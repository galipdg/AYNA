"""Tests for the UI Automation backend (#12, #16).

Two layers, because only one of them can run everywhere:

- **With fakes, on any OS.** `UiaDesktop.walk_from` is duck-typed on what `UIAElementInfo`
  offers, so the pre-order, the deduplication by window handle, the per-element property
  reading and the deadline are all pinned here without a desktop (`agent/AGENTS.md`).
- **`@pytest.mark.windows`, against the real desktop.** Those are marked and skipped on macOS;
  they are the only ones that can say the backend reads anything at all.
"""

from __future__ import annotations

import sys
import time
from datetime import datetime

import pytest

from ayna_agent.recognition import snapshot as snap
from ayna_agent.recognition.uia import MAX_DEPTH, MAX_ELEMENTS, UiaDesktop, _Progress
from ayna_agent.rpc import UiaUnavailable

# --- fakes -------------------------------------------------------------------------------


class FakeElement:
    """The `element` of a `UIAElementInfo`: the raw `Current*` properties."""

    def __init__(self, **values):
        self.CurrentControlType = values.get("control_type", 50000)
        self.CurrentAutomationId = values.get("automation_id", "")
        self.CurrentName = values.get("name", "")
        self.CurrentClassName = values.get("class_name", "")
        self.CurrentFrameworkId = values.get("framework_id", "")
        self.CurrentHelpText = values.get("help_text", "")
        self.CurrentAccessKey = values.get("access_key", "")
        self.CurrentIsEnabled = values.get("enabled", True)
        self.CurrentIsOffscreen = values.get("offscreen", False)
        self.CurrentNativeWindowHandle = values.get("handle", 0)
        self.CurrentLabeledBy = values.get("labeled_by")
        self.CurrentBoundingRectangle = values.get("rect")


class FakeRect:
    def __init__(self, left, top, right, bottom):
        self.left, self.top, self.right, self.bottom = left, top, right, bottom


class FakeInfo:
    """A `UIAElementInfo` stand-in: a name, a class, a handle and some children."""

    def __init__(self, name="", class_name="", handle=0, children=(), **values):
        self.name = name
        self.class_name = class_name
        self.handle = handle
        self._children = list(children)
        self.element = FakeElement(
            name=name, class_name=class_name, handle=handle, **values
        )
        self.child_calls = 0

    def children(self):
        self.child_calls += 1
        return list(self._children)


class SlowInfo(FakeInfo):
    """A container whose child enumeration blocks, like a WinForms tab under a modal box."""

    def __init__(self, *args, blocks_for_s: float, **values):
        super().__init__(*args, **values)
        self.blocks_for_s = blocks_for_s

    def children(self):
        time.sleep(self.blocks_for_s)
        return super().children()


def walked(root, *, budget_ms=5000, handle=1, dpi=96, title="Window"):
    desktop = UiaDesktop()
    desktop._type_names = {50000: "Button", 50032: "Window", 50020: "Text"}
    progress = _Progress()
    desktop.walk_from(root, handle, budget_ms, progress, title=title, dpi=dpi)
    return progress


# --- order, ids and the tree -------------------------------------------------------------


def test_the_walk_is_pre_order_with_parents_before_children():
    tree = FakeInfo(
        "root",
        handle=1,
        children=[
            FakeInfo("a", children=[FakeInfo("a1"), FakeInfo("a2")]),
            FakeInfo("b", children=[FakeInfo("b1")]),
        ],
    )
    progress = walked(tree)
    assert [n["name"] for n in progress.nodes] == ["root", "a", "a1", "a2", "b", "b1"]
    assert [n["id"] for n in progress.nodes] == [0, 1, 2, 3, 4, 5]
    assert [n["parent"] for n in progress.nodes] == [None, 0, 1, 1, 0, 4]
    assert [n["sibling_index"] for n in progress.nodes] == [0, 0, 0, 1, 1, 0]


def test_the_nodes_feed_the_snapshot_builder_unchanged():
    # The two halves of #12 have to fit: the walk's node shape is the builder's input.
    tree = FakeInfo(
        "root", class_name="LoginWindow", handle=7, children=[FakeInfo("ok")]
    )
    progress = walked(tree, handle=7, dpi=120, title="root")
    document = snap.build(
        progress.nodes,
        window={"handle": 7, "title": "root"},
        app={},
        started_at=datetime.now().astimezone(),
        duration_ms=5,
    )
    assert [node["id"] for node in document["elements"]] == ["e0", "e1"]
    assert document["elements"][1]["parentId"] == "e0"
    assert document["elements"][0]["element"]["dpi"] == 120
    assert document["elements"][0]["element"]["windowTitle"] == "root"


def test_every_element_carries_the_window_s_title_and_dpi():
    tree = FakeInfo("root", handle=1, children=[FakeInfo("child")])
    progress = walked(tree, dpi=144, title="Add Entry")
    assert {n["window_title"] for n in progress.nodes} == {"Add Entry"}
    assert {n["dpi"] for n in progress.nodes} == {144}


# --- deduplication by window handle ------------------------------------------------------


def test_a_dialog_that_is_also_a_child_of_its_owner_is_walked_once():
    # KeePass's `Add Entry` is a top-level window and a child of the main form's ToolBar
    # (#6), which made a first version of the #161 probe report 154 elements for 114.
    dialog = FakeInfo("Add Entry", handle=99, children=[FakeInfo("inside")])
    root = FakeInfo("main", handle=1, children=[FakeInfo("toolbar", children=[dialog])])
    progress = walked(root, handle=1)
    assert [n["name"] for n in progress.nodes] == [
        "main",
        "toolbar",
        "Add Entry",
        "inside",
    ]

    # Asked for the dialog itself, its subtree is not walked a second time through the owner.
    progress = walked(
        FakeInfo("main", handle=1, children=[FakeInfo("toolbar", children=[dialog])]),
        handle=99,
    )
    assert [n["name"] for n in progress.nodes] == ["main", "toolbar"]


def test_the_same_handle_twice_in_one_tree_is_read_once_subtree_included():
    twin = FakeInfo("twin", handle=42, children=[FakeInfo("under twin")])
    root = FakeInfo("root", handle=1, children=[twin, twin])
    progress = walked(root)
    assert [n["name"] for n in progress.nodes] == ["root", "twin", "under twin"]


def test_elements_without_a_handle_are_never_deduplicated():
    # Only about a third of WinForms elements have an HWND and none in WPF or Qt, so a
    # handle of 0 must not make every such element look like the same element.
    root = FakeInfo(
        "root", handle=1, children=[FakeInfo("a"), FakeInfo("b"), FakeInfo("c")]
    )
    progress = walked(root)
    assert [n["name"] for n in progress.nodes] == ["root", "a", "b", "c"]


# --- reading one element -----------------------------------------------------------------


def test_the_twelve_stored_properties_are_read_and_nothing_else():
    root = FakeInfo(
        "Giriş",
        class_name="QPushButton",
        handle=5,
        control_type=50000,
        automation_id="QApplication.loginWindow.loginButton",
        framework_id="Qt",
        help_text="Log in",
        access_key="Alt+G",
        enabled=True,
        offscreen=False,
        rect=FakeRect(10, 20, 110, 52),
    )
    node = walked(root).nodes[0]
    assert node["control_type"] == "Button"
    assert node["automation_id"] == "QApplication.loginWindow.loginButton"
    assert node["name"] == "Giriş"
    assert node["class_name"] == "QPushButton"
    assert node["framework_id"] == "Qt"
    assert node["help_text"] == "Log in"
    assert node["access_key"] == "Alt+G"
    assert node["enabled"] is True
    assert node["offscreen"] is False
    assert node["native_window_handle"] == 5
    assert node["bounds"] == [10, 20, 110, 52]
    assert node["labeled_by"] is None


def test_an_unknown_control_type_id_is_kept_as_the_id():
    root = FakeInfo("x", handle=1, control_type=99999)
    assert walked(root).nodes[0]["control_type"] == 99999


def test_a_labeled_by_relation_is_followed_to_the_label_s_name():
    label = FakeElement(name="Username")
    root = FakeInfo("", handle=1, labeled_by=label)
    assert walked(root).nodes[0]["labeled_by"] == "Username"


def test_a_native_window_handle_of_zero_becomes_absent():
    # The schema's nativeWindowHandle has minimum 1, and 0 means "this element has none".
    assert walked(FakeInfo("x")).nodes[0]["native_window_handle"] is None


class BrokenElement(FakeElement):
    """An element whose Name read fails, as a provider does when the element has gone."""

    def __getattribute__(self, name):
        if name == "CurrentName":
            raise OSError("the element vanished mid-walk")
        return super().__getattribute__(name)


def test_a_property_that_cannot_be_read_costs_only_that_value_and_is_counted():
    root = FakeInfo("x", handle=1)
    root.element = BrokenElement(class_name="Button")
    progress = walked(root)
    assert progress.nodes[0]["name"] is None
    assert progress.nodes[0]["class_name"] == "Button"
    assert progress.read_errors == 1


class BrokenChildren(FakeInfo):
    def children(self):
        raise OSError("this provider cannot enumerate")


def test_a_subtree_that_cannot_be_enumerated_costs_that_subtree_only():
    root = FakeInfo(
        "root", handle=1, children=[BrokenChildren("bad"), FakeInfo("good")]
    )
    progress = walked(root)
    assert [n["name"] for n in progress.nodes] == ["root", "bad", "good"]
    assert progress.read_errors == 1
    assert progress.timed_out is False


# --- the deadline and the guards ---------------------------------------------------------


def test_the_clock_is_checked_between_elements():
    deep = FakeInfo("leaf")
    for _ in range(40):
        deep = SlowInfo("node", children=[deep], blocks_for_s=0.01)
    progress = walked(deep, budget_ms=50)
    assert progress.timed_out is True
    assert 0 < progress.reached < 41


def test_a_walk_inside_its_budget_does_not_report_a_timeout():
    progress = walked(
        FakeInfo("root", handle=1, children=[FakeInfo("a")]), budget_ms=5000
    )
    assert progress.timed_out is False
    assert progress.reached == 2


def test_the_element_a_walk_got_stuck_on_is_named_from_values_already_read():
    stuck = SlowInfo(
        "Add Entry",
        class_name="WindowsForms10.Window",
        blocks_for_s=0.3,
        automation_id="m_tabEntry",
    )
    progress = walked(FakeInfo("root", handle=1, children=[stuck]), budget_ms=100)
    assert "m_tabEntry" in progress.blocked_on
    assert "element 1" in progress.blocked_on


def test_a_tree_deeper_than_the_guard_gives_up_rather_than_truncating():
    deep = FakeInfo("bottom")
    for _ in range(MAX_DEPTH + 2):
        deep = FakeInfo("node", children=[deep])
    progress = walked(deep)
    assert progress.timed_out is True
    assert progress.reached == MAX_DEPTH + 1


def test_the_element_guard_is_a_number_a_real_window_cannot_reach():
    # 20 000 against the 114 of the largest pilot window measured in #161: the guard exists
    # for a provider that reports a cycle, not as a second budget.
    assert MAX_ELEMENTS >= 20_000


# --- the backend's own contract ----------------------------------------------------------


def test_a_backend_that_was_never_set_up_answers_unavailable():
    desktop = UiaDesktop()
    with pytest.raises(UiaUnavailable, match="not been set up"):
        desktop.list_windows()
    with pytest.raises(UiaUnavailable, match="not been set up"):
        desktop.snapshot(1, None)


def test_setup_records_a_reason_instead_of_refusing_to_start(monkeypatch):
    # docs/agent-rpc.md: a host without a backend answers -32001 per call. A server that
    # refused to start would stop the client and the Spy from running on macOS.
    monkeypatch.setattr(sys, "platform", "darwin")
    desktop = UiaDesktop()
    desktop.setup()
    with pytest.raises(UiaUnavailable, match="needs Windows, this is darwin"):
        desktop.list_windows()
    desktop.close()  # must not raise although nothing was initialised


def test_the_default_budget_is_the_one_the_snapshot_module_defines():
    assert UiaDesktop().default_budget_ms == snap.DEFAULT_BUDGET_MS == 5000


# --- the real desktop --------------------------------------------------------------------


@pytest.fixture(scope="module")
def desktop():
    backend = UiaDesktop()
    backend.setup()
    if not backend._ready:
        pytest.skip(f"no UI Automation here: {backend._unavailable}")
    yield backend
    backend.close()


@pytest.mark.windows
def test_the_desktop_has_visible_top_level_windows(desktop):
    windows = desktop.list_windows()
    assert windows, "a session with no visible window at all is not a session"
    for window in windows:
        assert window["handle"] > 0
        assert set(window) == {
            "handle",
            "title",
            "className",
            "processId",
            "processName",
            "bounds",
        }
        left, top, right, bottom = window["bounds"]
        assert right > left and bottom > top


@pytest.mark.windows
def test_a_handle_that_is_not_a_window_is_window_not_found(desktop):
    from ayna_agent.rpc import WindowNotFound

    with pytest.raises(WindowNotFound):
        desktop.snapshot(12, None)


@pytest.mark.windows
def test_a_snapshot_of_a_real_window_validates_and_round_trips(desktop):
    import json
    from pathlib import Path

    from jsonschema import Draft202012Validator

    windows = desktop.list_windows()
    document = desktop.snapshot(windows[0]["handle"], None)
    schema = json.loads(
        (
            Path(__file__).resolve().parents[2] / "schemas" / "snapshot.schema.json"
        ).read_text(encoding="utf-8")
    )
    Draft202012Validator(schema).validate(document)
    assert snap.loads(snap.dumps(document)) == document
    capture = document["capture"]
    assert capture["elementCount"] == len(document["elements"])
    assert capture["durationMs"] < capture["budgetMs"]


@pytest.mark.windows
def test_a_budget_too_small_for_any_window_is_a_snapshot_timeout(desktop):
    from ayna_agent.rpc import SnapshotTimeout

    windows = desktop.list_windows()
    with pytest.raises(SnapshotTimeout, match="walk stopped"):
        desktop.snapshot(windows[0]["handle"], 1)


# --- DPI awareness -----------------------------------------------------------------------


def test_the_awareness_names_cover_every_context():
    """One name per `DPI_AWARENESS_CONTEXT`, so a warning can say what the process got."""
    from ayna_agent.recognition.uia import _AWARENESS_CONTEXTS, _PER_MONITOR_AWARE_V2

    assert _AWARENESS_CONTEXTS["per-monitor-v2"] == _PER_MONITOR_AWARE_V2
    assert sorted(_AWARENESS_CONTEXTS.values()) == [-5, -4, -3, -2, -1]


@pytest.mark.windows
@pytest.mark.skipif(
    sys.platform != "win32", reason="DPI awareness exists only on Windows"
)
def test_setup_leaves_the_process_per_monitor_v2():
    """The bounds contract, as a test rather than as a comment.

    `docs/agent-rpc.md` and `schemas/snapshot.schema.json` promise bounds "as UI Automation
    reports them to a per-monitor-v2 DPI aware agent". Awareness can be set only once per
    process and pytest has long since imported pywinauto by the time this runs, so the check
    has to happen in a **fresh interpreter** -- which is also how the agent really starts.

    This failed before 2026-11-07: `DPI_AWARENESS_CONTEXT` is pointer-sized, ctypes truncated
    the negative constant, the call returned `ERROR_INVALID_PARAMETER`, the code treated that
    as "already set", and pywinauto's import then made the process per-monitor-**v1**.
    """
    import subprocess
    import sys

    probe = (
        "from ayna_agent.recognition.uia import UiaDesktop, dpi_awareness\n"
        "d = UiaDesktop()\n"
        "d.setup()\n"
        "print(dpi_awareness())\n"
        "d.close()\n"
    )
    done = subprocess.run(
        [sys.executable, "-c", probe],
        capture_output=True,
        text=True,
        timeout=120,
        check=True,
    )
    assert done.stdout.strip().splitlines()[-1] == "per-monitor-v2", done.stderr


@pytest.mark.windows
def test_window_bounds_exclude_the_invisible_resize_border(desktop):
    """`listWindows` reports the window as a person sees it, not as `GetWindowRect` does.

    Since Windows 10 a resizable window has an *invisible* resize border outside its visible
    frame, and `GetWindowRect` includes it -- which is why a maximised browser reports a
    negative origin. The Spy drew its red frame from this rectangle, so the frame landed
    outside the window (#184, found at 150 % scaling on 2026-11-07).

    The assertion is a relation rather than a number, because the border is DPI-scaled and
    differs per window: the reported rectangle must sit **inside** `GetWindowRect`, and for at
    least one window on a real desktop it must be strictly smaller -- otherwise the fix is not
    doing anything and the test would pass against the old code.
    """
    import win32gui

    windows = desktop.list_windows()
    assert windows, "a session with no visible window at all is not a session"
    smaller = 0
    for window in windows:
        left, top, right, bottom = window["bounds"]
        outer = win32gui.GetWindowRect(window["handle"])
        assert left >= outer[0] and top >= outer[1], window["title"]
        assert right <= outer[2] and bottom <= outer[3], window["title"]
        if (right - left) < (outer[2] - outer[0]):
            smaller += 1
    assert smaller, (
        "no window's frame bounds were narrower than GetWindowRect; either every window on "
        "this desktop is borderless or the DWM call is not being used"
    )
