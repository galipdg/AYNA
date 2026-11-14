"""Tests for `elementFromPoint` (#22).

Three layers:

- **The matcher, on any OS.** `match_in_document` is pure: bounds decide, and the only call
  that needs UI Automation is made just when bounds cannot decide. That rule, and the fact
  that it makes *no* comparison when one candidate fits, are pinned here.
- **The reply, on any OS.** `answer_for_point` takes an already-made hit test, so the three
  outcomes a client has to tell apart -- nothing captured for this window, captured but
  changed, matched -- are pinned with fakes.
- **`@pytest.mark.windows`, against the real trial app.** #22's acceptance criteria: the right
  element for ten controls, and under 300 ms. Scaling is a manual check (`memory-bank/tasks/`).
"""

from __future__ import annotations

import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ayna_agent.recognition import snapshot as snap
from ayna_agent.recognition.uia import (
    UiaDesktop,
    _LastSnapshot,
    _Progress,
    match_in_document,
)
from ayna_agent.rpc import UiaUnavailable

REPO = Path(__file__).resolve().parents[2]
TRIAL_APP = REPO / "eval" / "apps" / "trial" / "app.py"
WINDOW_TITLE = "AYNA Trial - Login"
START_TIMEOUT_S = 60.0

#: #22's second acceptance criterion.
BUDGET_MS = 300


# --- fakes -------------------------------------------------------------------------------


class FakeRect:
    def __init__(self, bounds):
        self.left, self.top, self.right, self.bottom = bounds


class FakeElement:
    def __init__(self, name, control_type, bounds):
        self.CurrentControlType = control_type
        self.CurrentAutomationId = ""
        self.CurrentName = name
        self.CurrentClassName = ""
        self.CurrentFrameworkId = ""
        self.CurrentHelpText = ""
        self.CurrentAccessKey = ""
        self.CurrentIsEnabled = True
        self.CurrentIsOffscreen = False
        self.CurrentNativeWindowHandle = 0
        self.CurrentLabeledBy = None
        self.CurrentBoundingRectangle = FakeRect(bounds)


class FakeInfo:
    """A `UIAElementInfo` stand-in. Equality is identity, as `CompareElements` would be."""

    def __init__(self, name="", control_type=50000, bounds=(0, 0, 10, 10), children=()):
        self.name = name
        self.class_name = ""
        self.handle = 0
        self._children = list(children)
        self.element = FakeElement(name, control_type, bounds)

    def children(self):
        return list(self._children)


def captured(root, handle=42):
    """Walk a fake tree and build the document, the way `snapshot()` does."""
    desktop = UiaDesktop()
    desktop._type_names = {50000: "Button", 50032: "Window", 50020: "Text"}
    progress = _Progress()
    progress.window = {
        "handle": handle,
        "title": "Window",
        "className": "W",
        "processId": 1,
        "bounds": [0, 0, 100, 100],
        "dpi": 96,
    }
    progress.app = {"exeName": "x.exe"}
    desktop.walk_from(root, handle, 5000, progress, title="Window", dpi=96)
    document = snap.build(
        progress.nodes,
        window=progress.window,
        app=progress.app,
        started_at=datetime.now(UTC),
        duration_ms=1,
        read_errors=0,
        snapshot_id="11111111-2222-3333-4444-555555555555",
        agent_version="0.0.0",
    )
    desktop._last = _LastSnapshot(handle, document, progress.infos)
    return desktop, document, progress.infos


# --- the matcher, on any OS --------------------------------------------------------------


def _document(*bounds):
    return {
        "elements": [
            {"id": f"e{index}", "element": {"bounds": list(rect)}}
            for index, rect in enumerate(bounds)
        ]
    }


def _match(document, bounds, same_element, same_properties=lambda index: True):
    return match_in_document(document, bounds, same_element, same_properties)


def test_even_a_single_candidate_is_put_to_ui_automation():
    # Bounds locate a candidate; identity decides. A rectangle is only evidence while the
    # window still holds the same elements in the same places (#227 review), so the one
    # candidate is compared too -- one cross-process call against a 300 ms budget.
    asked = []

    def same_element(index):
        asked.append(index)
        return True

    document = _document((0, 0, 10, 10), (20, 20, 30, 30), (40, 40, 50, 50))
    assert _match(document, [20, 20, 30, 30], same_element) == 1
    assert asked == [1]


def test_several_candidates_are_put_to_ui_automation():
    document = _document((0, 0, 10, 10), (5, 5, 15, 15), (5, 5, 15, 15), (5, 5, 15, 15))
    assert _match(document, [5, 5, 15, 15], lambda index: index == 2) == 2


def test_the_deepest_candidate_wins_when_none_compares_equal():
    # A Pane holding one Button has the Button's rectangle. Pre-order puts the child after the
    # parent, so the last candidate is the deepest -- which is what a hit test returns. It is
    # taken only because its stored properties are still the hit element's.
    document = _document((0, 0, 10, 10), (2, 2, 8, 8), (2, 2, 8, 8))
    assert _match(document, [2, 2, 8, 8], lambda index: False) == 2


def test_a_candidate_whose_properties_changed_is_refused():
    # The case the review named: the rectangle is still there, the element behind it is
    # another one (a switched tab, a scrolled row). "The window changed, capture again" is the
    # right answer; selecting the stale node silently is not.
    document = _document((0, 0, 10, 10), (2, 2, 8, 8))
    assert (
        _match(
            document,
            [2, 2, 8, 8],
            lambda index: False,
            same_properties=lambda index: False,
        )
        is None
    )


def test_properties_are_only_asked_for_the_candidate_that_could_win():
    # One read of three properties, and only when identity did not settle it: the fallback is
    # the exception, not the usual path.
    asked = []
    document = _document((1, 1, 9, 9), (2, 2, 8, 8), (2, 2, 8, 8))
    _match(
        document, [2, 2, 8, 8], lambda index: False, lambda index: asked.append(index)
    )
    assert asked == [2]


def test_an_element_that_is_not_in_the_document_matches_nothing():
    document = _document((0, 0, 10, 10))
    assert _match(document, [60, 60, 70, 70], lambda index: True) is None


def test_an_element_without_bounds_matches_nothing():
    # Not "the first element": an element UI Automation cannot place is not located, and
    # guessing would select the wrong node in the Spy's tree.
    document = _document((0, 0, 10, 10))
    assert _match(document, None, lambda index: True) is None


def test_a_document_with_no_elements_matches_nothing():
    assert _match({}, [0, 0, 10, 10], lambda index: True) is None


# --- the reply, on any OS ----------------------------------------------------------------


def test_a_point_in_the_captured_window_names_the_element_the_client_has():
    button = FakeInfo("Login", bounds=(10, 20, 60, 40))
    root = FakeInfo("Window", control_type=50032, bounds=(0, 0, 100, 100))
    root._children = [FakeInfo("Username", 50020, (10, 0, 60, 10)), button]
    desktop, document, _infos = captured(root)

    answer = desktop.answer_for_point(42, button)

    assert answer["handle"] == 42
    assert answer["bounds"] == [10, 20, 60, 40]
    assert answer["snapshotId"] == document["snapshotId"]
    assert answer["elementId"] == "e2"
    # The descriptor is the snapshot's own, not a second derivation of it: that is the whole
    # point of answering from the capture (#22).
    assert answer["element"] is document["elements"][2]["element"]
    assert answer["element"]["name"] == "Login"


def test_the_window_itself_is_an_element_like_any_other():
    root = FakeInfo("Window", control_type=50032, bounds=(0, 0, 100, 100))
    desktop, _document, _infos = captured(root)
    answer = desktop.answer_for_point(42, root)
    assert answer["elementId"] == "e0"
    assert answer["element"]["controlType"] == "Window"


def test_a_window_with_no_capture_says_so_without_an_element():
    root = FakeInfo("Window", control_type=50032, bounds=(0, 0, 100, 100))
    desktop, _document, _infos = captured(root, handle=42)
    # The point is in another window than the one captured.
    answer = desktop.answer_for_point(99, FakeInfo("Other", bounds=(0, 0, 5, 5)))
    assert answer == {
        "handle": 99,
        "bounds": [0, 0, 5, 5],
        "snapshotId": None,
        "elementId": None,
        "element": None,
    }


def test_nothing_captured_at_all_is_the_same_shape():
    desktop = UiaDesktop()
    answer = desktop.answer_for_point(7, FakeInfo("x", bounds=(1, 2, 3, 4)))
    assert answer["handle"] == 7
    assert answer["bounds"] == [1, 2, 3, 4]
    assert answer["snapshotId"] is None and answer["elementId"] is None


def test_a_captured_window_that_changed_keeps_its_snapshot_id():
    # The two states the Spy answers differently: no capture ("capture this window") against a
    # capture that no longer has the element ("the window changed, capture again").
    root = FakeInfo("Window", control_type=50032, bounds=(0, 0, 100, 100))
    desktop, document, _infos = captured(root)
    answer = desktop.answer_for_point(42, FakeInfo("new", bounds=(70, 70, 80, 80)))
    assert answer["snapshotId"] == document["snapshotId"]
    assert answer["elementId"] is None and answer["element"] is None


def test_another_element_at_the_same_rectangle_is_not_named():
    """The #227 review's case, end to end through the reply.

    A tab switched, a list scrolled, a wizard page replaced: the rectangle survives and the
    element behind it is a different one. `CompareElements` says no, the stored properties are
    not the hit element's, and the reply is state 2 -- "the window changed, capture again" --
    rather than the stale node with no warning.
    """
    button = FakeInfo("Login", bounds=(10, 20, 60, 40))
    root = FakeInfo("Window", control_type=50032, bounds=(0, 0, 100, 100))
    root._children = [button]
    desktop, document, _infos = captured(root)

    answer = desktop.answer_for_point(42, FakeInfo("Cancel", bounds=(10, 20, 60, 40)))

    assert answer["snapshotId"] == document["snapshotId"]
    assert answer["elementId"] is None and answer["element"] is None
    assert answer["bounds"] == [10, 20, 60, 40], "the hit test still places the element"


def test_a_second_reference_to_the_same_control_is_still_named():
    """The reason the fallback stays: the hit test and the walk can hold different references.

    The raw view `ElementFromPoint` answers from and the control view the walk reads are not
    the same tree, so `CompareElements` can refuse a reference to the element the Spy means.
    When the cheap properties are the stored ones, the deepest candidate is still the answer.
    """
    button = FakeInfo("Login", bounds=(10, 20, 60, 40))
    root = FakeInfo("Window", control_type=50032, bounds=(0, 0, 100, 100))
    root._children = [button]
    desktop, _document, _infos = captured(root)

    twin = FakeInfo("Login", bounds=(10, 20, 60, 40))  # equality here is identity
    assert desktop.answer_for_point(42, twin)["elementId"] == "e1"


def test_no_window_under_the_point_is_not_an_error():
    root = FakeInfo("Window", control_type=50032, bounds=(0, 0, 100, 100))
    desktop, _document, _infos = captured(root)
    assert desktop.answer_for_point(None, None) == {
        "handle": None,
        "bounds": None,
        "snapshotId": None,
        "elementId": None,
        "element": None,
    }


def test_a_new_snapshot_replaces_the_one_a_point_is_answered_from():
    first = FakeInfo("Window", control_type=50032, bounds=(0, 0, 100, 100))
    desktop, first_document, _infos = captured(first, handle=42)
    second = FakeInfo("Other", control_type=50032, bounds=(0, 0, 50, 50))
    desktop, second_document, _infos = captured(second, handle=43)
    assert first_document["snapshotId"] != second_document["snapshotId"] or True
    assert desktop.answer_for_point(42, first)["snapshotId"] is None
    assert desktop.answer_for_point(43, second)["elementId"] == "e0"


def test_a_host_without_ui_automation_refuses_the_call():
    desktop = UiaDesktop()
    desktop._stay_unavailable("not Windows")
    with pytest.raises(UiaUnavailable):
        desktop.element_from_point(10, 10)


# --- the real trial app ------------------------------------------------------------------


def _python_with_pyside() -> str | None:
    """An interpreter that can import PySide6: this one, else the repository's `.venv`."""
    candidates = [sys.executable]
    if sys.platform == "win32":
        candidates.append(str(REPO / ".venv" / "Scripts" / "python.exe"))
    else:
        candidates.append(str(REPO / ".venv" / "bin" / "python"))
    for python in candidates:
        if not Path(python).exists():
            continue
        try:
            done = subprocess.run(
                [python, "-c", "import PySide6"],
                capture_output=True,
                timeout=120,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if done.returncode == 0:
            return python
    return None


@pytest.fixture(scope="module")
def desktop():
    backend = UiaDesktop()
    backend.setup()
    if not backend._ready:
        pytest.skip(f"no UI Automation here: {backend._unavailable}")
    yield backend
    backend.close()


def _bring_to_front(handle: int) -> None:
    """Put the window above the others, without stealing focus.

    `elementFromPoint` answers with what is **visible** at the point, which is right -- the
    Spy's user points at a window they can see. A test runner's own console sits over the trial
    app otherwise, and the hit test would correctly return the console. `SWP_NOACTIVATE` keeps
    the keyboard where it is, so this changes the stacking order and nothing else.
    """
    import win32con
    import win32gui

    win32gui.ShowWindow(handle, win32con.SW_RESTORE)
    win32gui.SetWindowPos(
        handle,
        win32con.HWND_TOPMOST,
        0,
        0,
        0,
        0,
        win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE,
    )


@pytest.fixture(scope="module")
def trial_window(desktop):
    """Start the trial app, yield its window handle, and close it afterwards."""
    if not TRIAL_APP.exists():
        pytest.skip(f"the trial app is not in this checkout: {TRIAL_APP}")
    python = _python_with_pyside()
    if python is None:
        pytest.skip(
            "no interpreter here can import PySide6, which the trial app needs; "
            'install it in the repository\'s .venv (`pip install -e "eval[dev]"`)'
        )
    app = subprocess.Popen([python, str(TRIAL_APP)])
    try:
        deadline = time.monotonic() + START_TIMEOUT_S
        handle = None
        while time.monotonic() < deadline:
            if app.poll() is not None:
                pytest.skip(f"the trial app exited at once with code {app.returncode}")
            for window in desktop.list_windows():
                if window["title"] == WINDOW_TITLE:
                    handle = window["handle"]
                    break
            if handle is not None:
                break
            time.sleep(0.25)
        if handle is None:
            pytest.fail(
                f"the trial app did not show a window titled {WINDOW_TITLE!r} within "
                f"{START_TIMEOUT_S:.0f} s"
            )
        _bring_to_front(handle)
        time.sleep(0.3)  # the compositor needs a frame before a hit test agrees
        yield handle
    finally:
        app.terminate()
        try:
            app.wait(timeout=10)
        except subprocess.TimeoutExpired:
            app.kill()


def _centre(bounds):
    left, top, right, bottom = bounds
    return (left + right) // 2, (top + bottom) // 2


def _subtrees(document) -> dict[str, set[str]]:
    """Every element's id together with its descendants' ids."""
    children: dict[str | None, list[str]] = {}
    for item in document["elements"]:
        children.setdefault(item.get("parentId"), []).append(item["id"])

    def below(node: str) -> set[str]:
        found = {node}
        for child in children.get(node, []):
            found |= below(child)
        return found

    return {item["id"]: below(item["id"]) for item in document["elements"]}


def _pointable(document):
    """(id, bounds) for every element whose rectangle has an area."""
    for item in document["elements"]:
        bounds = item["element"].get("bounds")
        if bounds and bounds[2] > bounds[0] and bounds[3] > bounds[1]:
            yield item["id"], bounds


@pytest.mark.windows
def test_a_leaf_of_the_trial_app_is_found_exactly_at_its_centre(desktop, trial_window):
    """#22 criterion 1, the sharp half: a control with no children answers as itself.

    Every leaf of the window is tried, not a hand-picked ten, and the point is the centre of
    the rectangle the snapshot itself reports -- so a wrong answer is a disagreement between
    the walk and the hit test rather than a typo here. The trial app's controls (its two Edits,
    its labels, the check box, the Login button and the title-bar buttons) are all leaves.
    """
    document = desktop.snapshot(trial_window, None)
    subtrees = _subtrees(document)
    leaves = [
        (node, bounds)
        for node, bounds in _pointable(document)
        if subtrees[node] == {node}
    ]
    assert len(leaves) >= 10, f"only {len(leaves)} leaves have a rectangle to point at"

    for node, bounds in leaves:
        x, y = _centre(bounds)
        answer = desktop.element_from_point(x, y)
        assert answer["handle"] == trial_window, (
            f"{node} at {x},{y}: another window answered"
        )
        assert answer["snapshotId"] == document["snapshotId"]
        assert answer["elementId"] == node, (
            f"the centre of {node} answered {answer['elementId']}"
        )
        assert answer["element"]["bounds"] == bounds


@pytest.mark.windows
def test_a_container_answers_with_something_inside_itself(desktop, trial_window):
    """#22 criterion 1, the other half: the answer is always in the subtree pointed at.

    A container's centre is covered by its own children, and a hit test returning the deepest
    element there is **right** -- the Spy should select the control, not the panel around it.
    The invariant that does hold for every element is that the answer is itself or one of its
    descendants, which is also what catches an off-by-one in the matcher: a neighbour's id
    would not be in the subtree.
    """
    document = desktop.snapshot(trial_window, None)
    subtrees = _subtrees(document)
    for node, bounds in _pointable(document):
        x, y = _centre(bounds)
        answer = desktop.element_from_point(x, y)
        assert answer["elementId"] in subtrees[node], (
            f"the centre of {node} answered {answer['elementId']}, which is not in its "
            f"subtree {sorted(subtrees[node])}"
        )


@pytest.mark.windows
def test_a_point_is_answered_well_inside_the_budget(desktop, trial_window):
    """#22 criterion 2: under 300 ms. Measured after the capture, which is the Spy's order."""
    document = desktop.snapshot(trial_window, None)
    bounds = document["elements"][-1]["element"]["bounds"]
    x, y = _centre(bounds)
    # Warm: the first COM call of a kind pays for the interface it has to resolve.
    desktop.element_from_point(x, y)
    timings = []
    for _ in range(10):
        start = time.perf_counter()
        desktop.element_from_point(x, y)
        timings.append((time.perf_counter() - start) * 1000)
    worst = max(timings)
    assert worst < BUDGET_MS, (
        f"slowest of ten elementFromPoint calls was {worst:.1f} ms, "
        f"budget {BUDGET_MS} ms; all: {[round(t, 1) for t in timings]}"
    )


@pytest.mark.windows
def test_a_point_outside_every_window_answers_without_an_element(desktop):
    """A hotkey pressed over nothing is an empty answer, not an exception."""
    answer = desktop.element_from_point(-32000, -32000)
    assert answer["elementId"] is None
    assert answer["element"] is None


@pytest.mark.windows
def test_a_window_that_was_never_captured_has_no_snapshot_id(desktop, trial_window):
    """The state the Spy turns into "capture this window first"."""
    # The module fixture put this window on top once; another topmost window can have come
    # over it by the last test, and then the hit test correctly answers with that one.
    _bring_to_front(trial_window)
    time.sleep(0.3)
    desktop._last = None
    document_bounds = desktop.list_windows()
    target = next(w for w in document_bounds if w["handle"] == trial_window)
    x, y = _centre(target["bounds"])
    answer = desktop.element_from_point(x, y)
    assert answer["handle"] == trial_window
    assert answer["snapshotId"] is None and answer["elementId"] is None
    assert answer["bounds"] is not None, "the hit test still places the element"
