"""Tests for running a step document against a window (#26).

Three rules are the point of this module and each is tested on its own:

- **order and stop-on-failure** -- a failed step ends the run and every later step is
  `notRun` (TBD-6);
- **waiting, not sleeping** -- the window is re-read until the target resolves, and
  `timeoutMs: 0` reads exactly once (RS NFR-05);
- **a step's own mistakes are results, not exceptions** -- an unknown keyword, a target the
  request forgot, a bad timeout all become that step's `failed` result with a message.

Time and the window are injected, so the waiting is tested without waiting: `now` is a counter
the fake `sleep` advances. The window content is the real trial-app tree from #11.
"""

from __future__ import annotations

import json
from pathlib import Path

import grids
import pytest

from ayna_agent.playback import runner
from ayna_agent.playback.actions import INVOKE_GAP_S, InvokeSpacing
from ayna_agent.playback.runner import (
    DEFAULT_TIMEOUT_MS,
    POLL_INTERVAL_S,
    SUPPORTED_STEP_VERSIONS,
    StepDocumentError,
    run_steps,
)
from ayna_agent.playback.screenshot import StepImage

TRIAL_TREE = Path(__file__).resolve().parent / "data" / "trial-app-tree.json"

USERNAME = "QApplication.loginWindow.usernameInput"
PASSWORD = "QApplication.loginWindow.passwordInput"
LOGIN = "QApplication.loginWindow.loginButton"

TARGETS = {
    "login.userNameInput": {"properties": {"automationId": USERNAME}},
    "login.passwordInput": {"properties": {"automationId": PASSWORD}},
    "login.loginButton": {"properties": {"automationId": LOGIN}},
}

#: The three-step login of #26's acceptance criteria.
LOGIN_STEPS = {
    "version": "0.1",
    "steps": [
        {"keyword": "Type", "target": "login.userNameInput", "value": "admin"},
        {"keyword": "Type", "target": "login.passwordInput", "value": "admin"},
        {"keyword": "Click", "target": "login.loginButton"},
    ],
}


def nodes() -> list[dict]:
    return json.loads(TRIAL_TREE.read_text(encoding="utf-8"))


class Window:
    """A window that can be read, counting the reads. `content` may change between them."""

    def __init__(self, content: list[dict] | None = None) -> None:
        self.content = nodes() if content is None else content
        self.reads = 0

    def read_tree(self) -> tuple[list[dict], list[str]]:
        self.reads += 1
        return self.content, [f"element-{i}" for i in range(len(self.content))]


class Clock:
    """A clock that only moves when something sleeps, so a wait costs no real time."""

    def __init__(self) -> None:
        self.at = 0.0
        self.slept: list[float] = []

    def now(self) -> float:
        return self.at

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.at += seconds


class Patterns:
    """Every element supports Invoke and Value; records what was done to which element."""

    def __init__(self) -> None:
        self.done: list[tuple[str, str, str | None]] = []

    def __call__(self, element: str, name: str) -> object | None:
        if name not in ("Invoke", "Value"):
            return None
        recorder = self

        class Fake:
            CurrentIsReadOnly = False

            def Invoke(self) -> None:
                recorder.done.append(("Click", element, None))

            def SetValue(self, value: str) -> None:
                recorder.done.append(("Type", element, value))

        return Fake()


def run(document, targets=None, *, window=None, clock=None, patterns=None, **kwargs):
    window = window or Window()
    clock = clock or Clock()
    patterns = patterns or Patterns()
    results = run_steps(
        document,
        TARGETS if targets is None else targets,
        window.read_tree,
        patterns=patterns,
        now=clock.now,
        sleep=clock.sleep,
        **kwargs,
    )
    return results, window, clock, patterns


# --- the happy path ------------------------------------------------------------------------


def test_the_three_step_login_passes_and_acts_on_the_right_elements():
    results, window, _clock, patterns = run(LOGIN_STEPS)
    assert [r.status for r in results] == ["passed", "passed", "passed"]
    assert [r.step_index for r in results] == [0, 1, 2]
    assert patterns.done == [
        ("Type", "element-8", "admin"),
        ("Type", "element-10", "admin"),
        ("Click", "element-12", None),
    ]
    assert window.reads == 3, "a target that is already there costs one read"
    assert all(r.matched == "primary" for r in results)
    assert [r.performed_with for r in results] == ["SetValue", "SetValue", "Invoke"]


def test_a_result_is_shaped_like_the_run_step_result_params():
    results, *_ = run(LOGIN_STEPS)
    body = results[0].to_json()
    assert body["stepIndex"] == 0
    assert body["status"] == "passed"
    # durationMs, not duration: the name settled in the #193 review.
    assert isinstance(body["durationMs"], int)
    assert body["performedWith"] == "SetValue"
    assert "message" not in body, "absent values are left out"
    assert "stepId" not in body


def test_a_step_id_is_carried_into_its_result():
    document = {
        "version": "0.1",
        "steps": [
            {
                "id": "4a8e2f10-6c3b-4d9e-a157-3e0b9c6d2f81",
                "keyword": "Click",
                "target": "login.loginButton",
            }
        ],
    }
    results, *_ = run(document)
    assert results[0].step_id == "4a8e2f10-6c3b-4d9e-a157-3e0b9c6d2f81"
    assert results[0].to_json()["stepId"] == "4a8e2f10-6c3b-4d9e-a157-3e0b9c6d2f81"


def test_an_empty_document_runs_nothing():
    results, window, *_ = run({"version": "0.1", "steps": []})
    assert results == []
    assert window.reads == 0


# --- stopping at the first failure ---------------------------------------------------------


def test_a_failed_step_stops_the_run_and_the_rest_is_not_run():
    document = {
        "version": "0.1",
        "steps": [
            {"keyword": "Click", "target": "login.loginButton"},
            {"keyword": "Click", "target": "login.gone"},
            {"keyword": "Click", "target": "login.loginButton"},
            {"keyword": "Type", "target": "login.userNameInput", "value": "x"},
        ],
    }
    results, _window, _clock, patterns = run(document)
    assert [r.status for r in results] == ["passed", "failed", "notRun", "notRun"]
    assert "not run" in results[2].message
    assert results[3].duration_ms == 0
    assert len(patterns.done) == 1, "nothing is performed after the failure"


def test_every_step_gets_a_result_even_when_the_first_one_fails():
    document = {
        "version": "0.1",
        "steps": [{"keyword": "Click", "target": "login.gone"}] * 3,
    }
    results, *_ = run(document)
    assert len(results) == 3
    assert [r.status for r in results] == ["failed", "notRun", "notRun"]


# --- what a single step can get wrong ------------------------------------------------------


@pytest.mark.parametrize("keyword", ["Open", "Nonsense"])
def test_a_keyword_this_release_does_not_perform_fails_by_name(keyword):
    """A keyword playback does not do must not be silently reported as passed.

    The step editor offers every keyword of the schema, so a document can always name one the
    agent has not got to yet, and the honest place to say so is the step's own result.
    """
    document = {
        "version": "0.1",
        "steps": [{"keyword": keyword, "target": "login.loginButton"}],
    }
    results, *_ = run(document)
    assert results[0].status == "failed"
    assert keyword in results[0].message
    assert "not implemented yet" in results[0].message
    for performed in sorted(runner.IMPLEMENTED):
        assert performed in results[0].message, "the message names what it can do"


def test_a_target_the_request_forgot_fails_with_a_message_a_tester_can_act_on():
    document = {
        "version": "0.1",
        "steps": [{"keyword": "Click", "target": "login.loginButton"}],
    }
    results, *_ = run(document, {})
    assert results[0].status == "failed"
    assert "login.loginButton" in results[0].message
    assert "renamed or removed" in results[0].message


def test_a_type_step_without_a_value_fails():
    document = {
        "version": "0.1",
        "steps": [{"keyword": "Type", "target": "login.userNameInput"}],
    }
    results, *_ = run(document)
    assert results[0].status == "failed"
    assert "needs a text value" in results[0].message


def test_a_step_with_no_target_fails():
    results, *_ = run({"version": "0.1", "steps": [{"keyword": "Click"}]})
    assert results[0].status == "failed"
    assert "names no target" in results[0].message


@pytest.mark.parametrize("timeout", [-1, "10", 1.5, True])
def test_a_timeout_that_is_not_whole_milliseconds_fails(timeout):
    document = {
        "version": "0.1",
        "steps": [
            {"keyword": "Click", "target": "login.loginButton", "timeoutMs": timeout}
        ],
    }
    results, *_ = run(document)
    assert results[0].status == "failed"
    assert "timeoutMs" in results[0].message


def test_an_ambiguous_target_fails_and_nothing_is_clicked():
    """The #187 rule: more than one match is a failure, never the first match."""
    document = {
        "version": "0.1",
        "steps": [{"keyword": "Click", "target": "login.userNameInput"}],
    }
    targets = {"login.userNameInput": {"properties": {"name": "Username"}}}
    results, _window, _clock, patterns = run(document, targets)
    assert results[0].status == "failed"
    assert "2 elements match" in results[0].message
    assert patterns.done == []


def test_a_property_set_playback_cannot_match_on_fails_at_once_without_waiting():
    document = {
        "version": "0.1",
        "steps": [
            {
                "keyword": "Click",
                "target": "login.loginButton",
                "timeoutMs": 10_000,
            }
        ],
    }
    targets = {"login.loginButton": {"properties": {"bounds": [0, 0, 10, 10]}}}
    results, window, clock, _patterns = run(document, targets)
    assert results[0].status == "failed"
    assert "cannot match on bounds" in results[0].message
    assert window.reads == 1, "waiting cannot fix a client bug"
    assert clock.slept == []


def test_an_action_that_cannot_be_performed_fails_and_records_the_match():
    document = {
        "version": "0.1",
        "steps": [{"keyword": "Click", "target": "login.loginButton"}],
    }
    results, *_ = run(document, patterns=lambda element, name: None)
    assert results[0].status == "failed"
    assert "without coordinates" in results[0].message
    assert results[0].matched == "primary", (
        "the element was found; the click is what failed"
    )


# --- the fallback set ----------------------------------------------------------------------


def test_a_fallback_match_passes_and_is_recorded_as_such():
    """What #73 heals and #63 logs: the Find-by properties have stopped matching."""
    document = {
        "version": "0.1",
        "steps": [{"keyword": "Click", "target": "login.loginButton"}],
    }
    targets = {
        "login.loginButton": {
            "properties": {"automationId": "QApplication.loginWindow.signInButton"},
            "fallback": {"name": "Login", "controlType": "Button"},
        }
    }
    results, *_ = run(document, targets)
    assert results[0].status == "passed"
    assert results[0].matched == "fallback"


# --- waiting, not sleeping -----------------------------------------------------------------


def test_the_window_is_re_read_until_the_target_appears():
    window = Window(content=[])
    tree = nodes()

    original = window.read_tree

    def appearing() -> tuple[list[dict], list[str]]:
        if window.reads >= 2:
            window.content = tree
        return original()

    window.read_tree = appearing  # type: ignore[method-assign]
    clock = Clock()
    results, _window, _clock, _patterns = run(
        {
            "version": "0.1",
            "steps": [{"keyword": "Click", "target": "login.loginButton"}],
        },
        window=window,
        clock=clock,
    )
    assert results[0].status == "passed"
    assert window.reads == 3
    assert clock.slept == [POLL_INTERVAL_S, POLL_INTERVAL_S]


def test_a_timeout_of_zero_reads_once_and_does_not_wait():
    """RS NFR-05: 0 means check once, and never means "use the default"."""
    document = {
        "version": "0.1",
        "steps": [{"keyword": "Click", "target": "login.loginButton", "timeoutMs": 0}],
    }
    window = Window(content=[])
    clock = Clock()
    results, _window, _clock, _patterns = run(document, window=window, clock=clock)
    assert results[0].status == "failed"
    assert window.reads == 1
    assert clock.slept == []


def test_waiting_stops_at_the_deadline_and_reports_the_last_failure():
    document = {
        "version": "0.1",
        "steps": [
            {"keyword": "Click", "target": "login.loginButton", "timeoutMs": 600}
        ],
    }
    window = Window(content=[])
    clock = Clock()
    results, _window, _clock, _patterns = run(document, window=window, clock=clock)
    assert results[0].status == "failed"
    assert "no element matches login.loginButton" in results[0].message
    assert "within 600 ms" in results[0].message
    # 0 ms, 250, 500, then the remaining 100 ms is the last sleep: four reads.
    assert clock.slept == [0.25, 0.25, pytest.approx(0.1)]
    assert window.reads == 4


def test_the_last_sleep_never_overshoots_the_deadline():
    document = {
        "version": "0.1",
        "steps": [
            {"keyword": "Click", "target": "login.loginButton", "timeoutMs": 100}
        ],
    }
    window = Window(content=[])
    clock = Clock()
    run(document, window=window, clock=clock)
    assert clock.slept == [pytest.approx(0.1)]
    assert clock.at == pytest.approx(0.1), "a 100 ms step must not take 250 ms"


def test_a_step_without_a_timeout_uses_the_run_default():
    document = {
        "version": "0.1",
        "steps": [{"keyword": "Click", "target": "login.loginButton"}],
    }
    window = Window(content=[])
    clock = Clock()
    run(document, window=window, clock=clock, default_timeout_ms=500)
    assert clock.at == pytest.approx(0.5)


def test_the_default_timeout_is_the_one_nfr_05_names():
    assert DEFAULT_TIMEOUT_MS == 10_000


# --- the document itself -------------------------------------------------------------------


def test_both_step_schema_versions_are_read():
    """Click and Type are identical in 0.1 and 0.2, so refusing 0.2 would break on #147."""
    assert SUPPORTED_STEP_VERSIONS == ("0.1", "0.2")
    for version in SUPPORTED_STEP_VERSIONS:
        results, *_ = run({**LOGIN_STEPS, "version": version})
        assert [r.status for r in results] == ["passed"] * 3


@pytest.mark.parametrize(
    "document",
    [
        {"steps": []},
        {"version": "0.0", "steps": []},
        {"version": 1, "steps": []},
        {"version": "0.1"},
        {"version": "0.1", "steps": "not a list"},
        {"version": "0.1", "steps": [["not", "an", "object"]]},
        [],
    ],
)
def test_a_document_that_cannot_be_read_raises(document):
    with pytest.raises(StepDocumentError):
        run(document)


# --- #54's screenshot per step -------------------------------------------------------------


class Camera:
    """A fake `capture`: records which steps were photographed, with no desktop involved."""

    def __init__(self, fails_on: set[int] | None = None) -> None:
        self.asked: list[int] = []
        self.fails_on = fails_on or set()

    def __call__(self, step_index: int) -> StepImage | None:
        self.asked.append(step_index)
        if step_index in self.fails_on:
            # What `step_capture` returns when the capture failed: no image, no exception.
            return None
        return StepImage(
            path=f"C:/runs/7/step-{step_index:04d}.png",
            taken_at="2026-11-15T14:03:11.250+03:00",
            width=800,
            height=600,
            captured_with="printWindow",
        )


def test_every_step_that_ran_gets_a_screenshot_in_its_result():
    camera = Camera()
    results, *_ = run(LOGIN_STEPS, capture=camera)
    assert camera.asked == [0, 1, 2]
    assert [r.screenshot_path for r in results] == [
        "C:/runs/7/step-0000.png",
        "C:/runs/7/step-0001.png",
        "C:/runs/7/step-0002.png",
    ]
    assert all(r.screenshot_at == "2026-11-15T14:03:11.250+03:00" for r in results)


def test_the_screenshot_reaches_the_result_json_in_camel_case():
    camera = Camera()
    results, *_ = run(LOGIN_STEPS, capture=camera)
    body = results[0].to_json()
    assert body["screenshotPath"] == "C:/runs/7/step-0000.png"
    assert body["screenshotAt"] == "2026-11-15T14:03:11.250+03:00"


def test_a_run_without_a_capture_carries_no_screenshot_fields():
    """The parameter is optional, so #26's callers and the CLI keep working unchanged."""
    results, *_ = run(LOGIN_STEPS)
    assert all(r.screenshot_path is None for r in results)
    assert "screenshotPath" not in results[0].to_json()
    assert "screenshotAt" not in results[0].to_json()


def test_the_failed_step_is_photographed_and_the_not_run_ones_are_not():
    """The failing step's image is the one worth having; a step that never ran has no screen."""
    document = {
        "version": "0.1",
        "steps": [
            {"keyword": "Click", "target": "login.loginButton"},
            {"keyword": "Click", "target": "login.gone"},
            {"keyword": "Click", "target": "login.loginButton"},
        ],
    }
    camera = Camera()
    results, *_ = run(document, capture=camera)
    assert [r.status for r in results] == ["passed", "failed", "notRun"]
    assert camera.asked == [0, 1], "a notRun step is not photographed"
    assert results[1].screenshot_path == "C:/runs/7/step-0001.png"
    assert results[2].screenshot_path is None


def test_a_capture_that_could_not_take_the_image_leaves_the_step_passing():
    camera = Camera(fails_on={1})
    results, *_ = run(LOGIN_STEPS, capture=camera)
    assert [r.status for r in results] == ["passed", "passed", "passed"]
    assert results[1].screenshot_path is None
    assert results[0].screenshot_path and results[2].screenshot_path


def test_the_capture_runs_after_the_step_not_before():
    """FR-19's image is evidence of what the step did, so the order matters.

    The fake patterns record each action; the camera records each capture. Interleaving them on
    one list is the only way to assert the order rather than assume it.
    """
    order: list[str] = []

    class Recording(Camera):
        def __call__(self, step_index: int) -> StepImage | None:
            order.append(f"shot {step_index}")
            return super().__call__(step_index)

    patterns = Patterns()
    real_click = patterns.__call__

    class Watching(Patterns):
        def __call__(self, element, name):
            order.append(f"act {name}")
            return real_click(element, name)

    run(LOGIN_STEPS, patterns=Watching(), capture=Recording())
    # Each step acts (possibly trying more than one pattern) and only then is photographed.
    assert order[0].startswith("act")
    assert [entry for entry in order if entry.startswith("shot")] == [
        "shot 0",
        "shot 1",
        "shot 2",
    ]
    assert order.index("shot 0") < order.index("shot 1")
    for index in (0, 1, 2):
        acts_before = [
            position
            for position, entry in enumerate(order[: order.index(f"shot {index}")])
            if entry.startswith("act")
        ]
        assert acts_before, f"step {index} was photographed before it acted"


# --- ready: exists, visible and enabled (#40) -----------------------------------------------


def with_login_button(**changes) -> list[dict]:
    """The trial tree with the login button's state changed."""
    tree = nodes()
    for node in tree:
        if node.get("automation_id") == LOGIN:
            node.update(changes)
    return tree


def test_a_disabled_target_is_waited_for_rather_than_clicked():
    """#40: "before each step wait until the element exists, is visible and enabled".

    HandBrake gives the real case (#29): with no source loaded every tab reads
    `enabled: false`. Under #26's rule the step resolved at once and the click failed for an
    unstated reason; the tester needs to know the control never became usable.
    """
    window = Window(content=with_login_button(enabled=False))
    clock = Clock()
    results, _window, _clock, patterns = run(
        {
            "version": "0.2",
            "steps": [
                {"keyword": "Click", "target": "login.loginButton", "timeoutMs": 600}
            ],
        },
        window=window,
        clock=clock,
    )
    assert results[0].status == "failed"
    assert results[0].message == (
        "login.loginButton: did not become enabled after 600 ms"
    )
    assert patterns.done == [], "nothing was clicked"
    assert window.reads == 4, "it kept re-reading, as it does for a missing element"


def test_an_offscreen_target_is_waited_for_too():
    window = Window(content=with_login_button(offscreen=True))
    results, *_ = run(
        {
            "version": "0.2",
            "steps": [
                {"keyword": "Click", "target": "login.loginButton", "timeoutMs": 0}
            ],
        },
        window=window,
    )
    assert results[0].message == (
        "login.loginButton: did not become on screen after 0 ms"
    )


def test_an_element_that_is_both_disabled_and_offscreen_says_both():
    window = Window(content=with_login_button(enabled=False, offscreen=True))
    results, *_ = run(
        {
            "version": "0.2",
            "steps": [
                {"keyword": "Click", "target": "login.loginButton", "timeoutMs": 0}
            ],
        },
        window=window,
    )
    assert results[0].message == (
        "login.loginButton: did not become enabled or on screen after 0 ms"
    )


@pytest.mark.parametrize("state", [{"enabled": None}, {"offscreen": None}])
def test_a_state_the_provider_did_not_report_counts_as_ready(state):
    """`NEVER_MATCH` already calls these unreliable, so a provider that reports neither must
    not make every step of that application time out."""
    window = Window(content=with_login_button(**state))
    results, _window, _clock, patterns = run(
        {
            "version": "0.2",
            "steps": [{"keyword": "Click", "target": "login.loginButton"}],
        },
        window=window,
    )
    assert results[0].status == "passed"
    assert patterns.done == [("Click", "element-12", None)]


def test_a_control_that_becomes_enabled_after_three_seconds_needs_no_fixed_sleep():
    """#40's second acceptance criterion, on the state rather than on existence: the step
    ends the moment the control becomes usable, and the elapsed time is the wait itself."""
    window = Window(content=with_login_button(enabled=False))
    clock = Clock()
    original = window.read_tree

    def enabling() -> tuple[list[dict], list[str]]:
        if clock.at >= 3.0:
            window.content = nodes()
        return original()

    window.read_tree = enabling  # type: ignore[method-assign]
    results, _window, _clock, patterns = run(
        {
            "version": "0.2",
            "steps": [{"keyword": "Click", "target": "login.loginButton"}],
        },
        window=window,
        clock=clock,
    )
    assert results[0].status == "passed"
    assert patterns.done == [("Click", "element-12", None)]
    assert clock.at == pytest.approx(3.0), "it waited exactly as long as it had to"
    assert set(clock.slept) == {POLL_INTERVAL_S}, (
        "no fixed sleep, only the poll interval"
    )
    assert results[0].duration_ms == 3000


# --- Wait ----------------------------------------------------------------------------------


def test_wait_passes_as_soon_as_the_target_is_ready_and_acts_on_nothing():
    results, window, clock, patterns = run(
        {
            "version": "0.2",
            "steps": [{"keyword": "Wait", "target": "login.loginButton"}],
        }
    )
    assert results[0].status == "passed"
    assert results[0].matched == "primary"
    assert results[0].performed_with is None, "a Wait performs nothing"
    assert patterns.done == []
    assert window.reads == 1
    assert clock.slept == []


def test_wait_waits_for_a_target_that_appears_late():
    window = Window(content=[])
    clock = Clock()
    original = window.read_tree

    def appearing() -> tuple[list[dict], list[str]]:
        if window.reads >= 2:
            window.content = nodes()
        return original()

    window.read_tree = appearing  # type: ignore[method-assign]
    results, *_ = run(
        {
            "version": "0.2",
            "steps": [{"keyword": "Wait", "target": "login.loginButton"}],
        },
        window=window,
        clock=clock,
    )
    assert results[0].status == "passed"
    assert window.reads == 3


def test_wait_fails_with_the_logical_name_when_the_target_never_arrives():
    """#40's third criterion: the message names the logical name and the time waited."""
    results, *_ = run(
        {
            "version": "0.2",
            "steps": [
                {"keyword": "Wait", "target": "login.loginButton", "timeoutMs": 500}
            ],
        },
        window=Window(content=[]),
    )
    assert results[0].status == "failed"
    assert "login.loginButton" in results[0].message
    assert "within 500 ms" in results[0].message


def test_wait_does_not_take_a_value():
    """The schema allows `value` for Type and Select only; a Wait carrying one is a client
    bug and must not be read as "wait for this text"."""
    results, *_ = run(
        {
            "version": "0.2",
            "steps": [
                {"keyword": "Wait", "target": "login.loginButton", "value": "admin"}
            ],
        }
    )
    assert results[0].status == "failed"
    assert "value" in results[0].message


@pytest.mark.parametrize(
    ("field", "extra", "allowed"),
    [
        ("value", "admin", "Select and Type"),
        ("row", {"index": 1}, "SelectRow"),
        ("checkpoint", {"property": "enabled", "expected": True}, "Verify"),
    ],
)
def test_a_field_on_a_keyword_that_forbids_it_is_refused_not_ignored(
    field, extra, allowed
):
    """Ignoring it would play a mis-built document as if it said something else and report
    `passed`, which is the one outcome a tester cannot debug."""
    results, _window, _clock, patterns = run(
        {
            "version": "0.2",
            "steps": [
                {"keyword": "Click", "target": "login.loginButton", field: extra}
            ],
        }
    )
    assert results[0].status == "failed"
    assert field in results[0].message
    assert allowed in results[0].message
    assert patterns.done == [], "nothing was clicked"


# --- Verify (#40) --------------------------------------------------------------------------


class Reading:
    """Patterns that answer property reads as well as performing actions."""

    def __init__(self, value=None, toggle=None, selected=None) -> None:
        self.value, self.toggle, self.selected = value, toggle, selected
        self.done: list[tuple[str, str, str | None]] = []

    def __call__(self, element: str, name: str) -> object | None:
        recorder = self
        if name == "Value" and self.value is not None:

            class V:
                CurrentIsReadOnly = False
                CurrentValue = recorder.value

                def SetValue(self, text: str) -> None:
                    recorder.done.append(("Type", element, text))

            return V()
        if name == "Toggle" and self.toggle is not None:

            class T:
                CurrentToggleState = recorder.toggle

            return T()
        if name == "SelectionItem" and self.selected is not None:

            class S:
                CurrentIsSelected = recorder.selected

            return S()
        if name == "Invoke":

            class I:
                def Invoke(self) -> None:
                    recorder.done.append(("Click", element, None))

            return I()
        return None


def verify(checkpoint, *, window=None, clock=None, patterns=None, **kwargs):
    document = {
        "version": "0.2",
        "steps": [
            {
                "keyword": "Verify",
                "target": "login.loginButton",
                "checkpoint": checkpoint,
                **kwargs,
            }
        ],
    }
    return run(document, window=window, clock=clock, patterns=patterns)


def test_a_checkpoint_that_holds_passes_without_waiting():
    results, window, clock, _patterns = verify(
        {"property": "name", "operator": "equals", "expected": "Login"}
    )
    assert results[0].status == "passed"
    assert results[0].matched == "primary"
    assert results[0].performed_with is None, "a Verify performs nothing"
    assert window.reads == 1
    assert clock.slept == []


def test_a_checkpoint_that_never_holds_fails_with_the_promised_wording():
    results, *_ = verify(
        {"property": "name", "operator": "contains", "expected": "Invalid"},
        timeoutMs=500,
    )
    assert results[0].status == "failed"
    assert results[0].message == (
        'login.loginButton: name should contain "Invalid", it is "Login" after 500 ms'
    )


def test_a_checkpoint_with_no_time_says_nothing_about_waiting():
    """`timeoutMs: 0` checks once, so there is no "after N ms" to report."""
    results, _window, clock, _patterns = verify(
        {"property": "name", "operator": "equals", "expected": "Hata"}, timeoutMs=0
    )
    assert results[0].message == (
        'login.loginButton: name should be "Hata", it is "Login"'
    )
    assert clock.slept == []


def test_a_verify_is_allowed_on_a_disabled_element():
    """The ready gate would make `enabled: false` unplayable, which is a check a tester
    writes all the time."""
    window = Window(content=with_login_button(enabled=False))
    results, _window, _clock, _patterns = verify(
        {"property": "enabled", "operator": "equals", "expected": False},
        window=window,
    )
    assert results[0].status == "passed"


def test_a_verify_on_an_offscreen_element_is_allowed_too():
    window = Window(content=with_login_button(offscreen=True))
    results, *_ = verify(
        {"property": "visible", "operator": "equals", "expected": False},
        window=window,
    )
    assert results[0].status == "passed"


def test_a_checkpoint_that_becomes_true_after_three_seconds_needs_no_fixed_sleep():
    """#40's second criterion again, on a property rather than on existence."""
    window = Window(content=with_login_button(name="Please wait"))
    clock = Clock()
    original = window.read_tree

    def settling() -> tuple[list[dict], list[str]]:
        if clock.at >= 3.0:
            window.content = nodes()
        return original()

    window.read_tree = settling  # type: ignore[method-assign]
    results, _window, _clock, _patterns = verify(
        {"property": "name", "operator": "equals", "expected": "Login"},
        window=window,
        clock=clock,
    )
    assert results[0].status == "passed"
    assert clock.at == pytest.approx(3.0)
    assert set(clock.slept) == {POLL_INTERVAL_S}
    assert results[0].duration_ms == 3000


def test_a_target_that_disappears_mid_check_says_so_rather_than_failing_the_property():
    """ "It was there and now it is not" is a different fact from "the property never took
    the expected value", and a tester debugs the two differently."""
    window = Window()
    clock = Clock()
    original = window.read_tree

    def vanishing() -> tuple[list[dict], list[str]]:
        if window.reads >= 1:
            window.content = []
        return original()

    window.read_tree = vanishing  # type: ignore[method-assign]
    results, *_ = verify(
        {"property": "name", "operator": "equals", "expected": "Hata"},
        window=window,
        clock=clock,
        timeoutMs=500,
    )
    assert results[0].status == "failed"
    assert "no element matches login.loginButton" in results[0].message
    assert "while checking name" in results[0].message


def test_a_property_that_cannot_be_read_fails_as_unreadable():
    results, *_ = verify(
        {"property": "checked", "operator": "equals", "expected": True}
    )
    assert results[0].status == "failed"
    assert "no TogglePattern" in results[0].message
    assert "login.loginButton" in results[0].message


def test_a_live_property_is_read_through_the_patterns():
    patterns = Reading(value="admin")
    results, *_ = verify(
        {"property": "value", "operator": "equals", "expected": "admin"},
        patterns=patterns,
    )
    assert results[0].status == "passed"
    assert patterns.done == [], "reading a property performs no action"


def test_a_verify_without_a_checkpoint_fails_before_reading_anything():
    results, *_ = run(
        {
            "version": "0.2",
            "steps": [{"keyword": "Verify", "target": "login.loginButton"}],
        }
    )
    assert results[0].status == "failed"
    assert "needs a checkpoint object" in results[0].message


def test_a_failed_verify_stops_the_run_like_any_other_failure():
    results, *_ = run(
        {
            "version": "0.2",
            "steps": [
                {
                    "keyword": "Verify",
                    "target": "login.loginButton",
                    "checkpoint": {
                        "property": "name",
                        "operator": "equals",
                        "expected": "Hata",
                    },
                    "timeoutMs": 0,
                },
                {"keyword": "Click", "target": "login.loginButton"},
            ],
        }
    )
    assert [r.status for r in results] == ["failed", "notRun"]
    assert results[1].message == "not run: an earlier step failed"


# --- Select (#40) --------------------------------------------------------------------------

CITY_COMBO = "QApplication.listWindow.cityCombo"
CITIES = ("Adana", "Ankara", "İzmir")

SELECT_TARGETS = {"list.city": {"properties": {"automationId": CITY_COMBO}}}


def city_window(items: tuple[str, ...]) -> list[dict]:
    """A window with a combo box, whose items are in the tree only while it is open.

    The items hang under an inner `List`, as WPF's and Qt's do, so "the children of the combo
    box" would find none of them.
    """
    content = [
        {
            "id": 0,
            "parent": None,
            "control_type": "Window",
            "automation_id": "QApplication.listWindow",
            "name": "AYNA Trial - Liste",
            "class_name": "ListWindow",
            "framework_id": "Qt",
            "bounds": [0, 0, 400, 300],
            "enabled": True,
            "offscreen": False,
            "window_title": "AYNA Trial - Liste",
            "dpi": 120,
        },
        {
            "id": 1,
            "parent": 0,
            "control_type": "Text",
            "name": "Şehir",
            "bounds": [10, 10, 60, 30],
            "enabled": True,
            "offscreen": False,
        },
        {
            "id": 2,
            "parent": 0,
            "control_type": "ComboBox",
            "automation_id": CITY_COMBO,
            "name": "Adana",
            "bounds": [70, 10, 200, 30],
            "enabled": True,
            "offscreen": False,
        },
    ]
    if items:
        content.append(
            {
                "id": 3,
                "parent": 2,
                "control_type": "List",
                "name": "cityCombo list",
                "bounds": [70, 30, 200, 120],
                "enabled": True,
                "offscreen": False,
            }
        )
        for position, text in enumerate(items):
            content.append(
                {
                    "id": 10 + position,
                    "parent": 3,
                    "control_type": "ListItem",
                    "name": text,
                    "bounds": [70, 30 + 20 * position, 200, 50 + 20 * position],
                    "enabled": True,
                    "offscreen": False,
                }
            )
    content.append(
        {
            "id": 4,
            "parent": 0,
            "control_type": "Button",
            "automation_id": "QApplication.listWindow.okButton",
            "name": "Tamam",
            "bounds": [10, 150, 100, 180],
            "enabled": True,
            "offscreen": False,
        }
    )
    return content


class ComboWindow:
    """The window above, read as often as playback asks.

    Each live element names itself (`ComboBox:Adana`, `ListItem:Ankara`), so a test asserts on
    *what* was acted on rather than on an index that moves when the list opens.
    """

    def __init__(
        self,
        items: tuple[str, ...] = CITIES,
        *,
        opened: bool = False,
        self_closing: bool = False,
    ) -> None:
        self.items = items
        self.opened = opened
        #: Qt: a popup opened through `ExpandCollapse` closes itself again about a second
        #: later, taking its items out of the tree (measured in the #40 Windows check). Here
        #: it closes after the read that saw it, which is the same failure deterministically.
        self.self_closing = self_closing
        self.gone = False
        self.reads = 0

    def read_tree(self) -> tuple[list[dict], list[str]]:
        self.reads += 1
        if self.gone:
            return [], []
        content = city_window(self.items if self.opened else ())
        if self.self_closing and self.opened:
            self.opened = False
        return content, [f"{n['control_type']}:{n.get('name')}" for n in content]


class ComboPatterns:
    """Patterns for that window: the box expands, and its items answer `SelectionItem`."""

    def __init__(
        self,
        window: ComboWindow,
        *,
        refuses: bool = False,
        editable: bool = False,
        expands: bool = True,
    ) -> None:
        self.window = window
        self.refuses = refuses
        self.editable = editable
        self.expands = expands
        #: What was done to the box itself, in order.
        self.done: list[str] = []
        #: Which items were selected.
        self.chosen: list[str] = []
        self.text = "Adana"

    def __call__(self, element: str, name: str) -> object | None:
        recorder = self
        if element.startswith("ComboBox"):
            if name == "ExpandCollapse" and self.expands:

                class E:
                    def Expand(self) -> None:
                        recorder.done.append("Expand")
                        recorder.window.opened = True

                    def Collapse(self) -> None:
                        recorder.done.append("Collapse")
                        recorder.window.opened = False

                return E()
            if name == "Selection":
                return object()
            if name == "Value" and self.editable:

                class V:
                    CurrentIsReadOnly = False

                    @property
                    def CurrentValue(self) -> str:
                        return recorder.text

                    def SetValue(self, value: str) -> None:
                        recorder.done.append("SetValue")
                        recorder.text = value

                return V()
        if element.startswith("ListItem") and name == "SelectionItem":

            class S:
                def Select(self) -> None:
                    if recorder.refuses:
                        raise OSError("Qt leaves the box unchanged")
                    recorder.chosen.append(element)

            return S()
        return None


def select_steps(value: str = "Ankara", target: str = "list.city", **extra) -> dict:
    return {
        "version": "0.2",
        "steps": [{"keyword": "Select", "target": target, "value": value, **extra}],
    }


def test_select_expands_the_box_rereads_and_chooses_the_item():
    """The re-read is the point: a closed combo box has no items at all (#33), so they are new
    elements rather than ones a harder look would have found."""
    window = ComboWindow()
    patterns = ComboPatterns(window)
    results, _window, clock, _patterns = run(
        select_steps(), SELECT_TARGETS, window=window, patterns=patterns
    )
    assert results[0].status == "passed"
    assert results[0].performed_with == "SelectionItem"
    assert results[0].matched == "primary"
    assert patterns.chosen == ["ListItem:Ankara"]
    assert patterns.done == [
        "Expand",
        "Collapse",
    ], "the screen is left as the test found it"
    assert window.reads == 2, "one read to resolve, one after expanding"
    assert clock.slept == [POLL_INTERVAL_S]


def test_a_list_that_already_shows_its_items_is_not_expanded():
    window = ComboWindow(opened=True)
    patterns = ComboPatterns(window, expands=False)
    results, _window, clock, _patterns = run(
        select_steps(), SELECT_TARGETS, window=window, patterns=patterns
    )
    assert results[0].status == "passed"
    assert patterns.chosen == ["ListItem:Ankara"]
    assert patterns.done == []
    assert window.reads == 1
    assert clock.slept == []


def test_an_item_the_list_does_not_have_says_how_many_items_it_has():
    """0 items and 3 items send a tester in different directions, so the count is in the
    message: a list that never filled, against a value that is simply wrong."""
    window = ComboWindow(opened=True)
    patterns = ComboPatterns(window, expands=False)
    results, *_ = run(
        select_steps("Bursa", timeoutMs=500),
        SELECT_TARGETS,
        window=window,
        patterns=patterns,
    )
    assert results[0].status == "failed"
    assert results[0].message == (
        'list.city: no item has the text "Bursa" after 500 ms; the target offers 3 items'
    )
    assert patterns.chosen == []


def test_a_select_on_something_that_is_not_a_list_fails_without_waiting():
    """Waiting cannot turn a button into a list, and ten seconds of silence would suggest it
    might."""
    results, _window, clock, _patterns = run(select_steps(target="login.loginButton"))
    assert results[0].status == "failed"
    assert "Select needs a list or a combo box" in results[0].message
    assert results[0].message.startswith("login.loginButton: ")
    assert clock.slept == [], "it did not wait"


def test_a_provider_that_refuses_to_select_blames_itself_not_the_test():
    """The Qt case from #33: `SelectionItem.Select` leaves the box unchanged. A tester must
    not read that as "your text is wrong"."""
    window = ComboWindow(opened=True)
    patterns = ComboPatterns(window, refuses=True, expands=False)
    results, *_ = run(
        select_steps("Ankara", timeoutMs=0),
        SELECT_TARGETS,
        window=window,
        patterns=patterns,
    )
    assert results[0].status == "failed"
    assert "refused to select it" in results[0].message
    assert '"Ankara"' in results[0].message


def test_an_editable_box_takes_the_text_when_playback_cannot_see_any_item():
    """A Qt combo box's popup is a window of its own, so its items are in no tree read here.
    Writing the text is the honest last resort, and `SetValue` in the result says the step
    typed rather than chose."""
    window = ComboWindow(items=())
    patterns = ComboPatterns(window, editable=True)
    results, *_ = run(
        select_steps("Ankara", timeoutMs=500),
        SELECT_TARGETS,
        window=window,
        patterns=patterns,
    )
    assert results[0].status == "passed"
    assert results[0].performed_with == "SetValue"
    assert patterns.text == "Ankara"
    assert patterns.done[-1] == "Collapse", "the box it opened is closed again"


def test_the_text_fallback_is_only_tried_after_the_whole_wait():
    """It writes text rather than choosing an item, so trying it early would hide a genuine
    "there is no such item" behind a pass."""
    window = ComboWindow(opened=True)
    patterns = ComboPatterns(window, editable=True, expands=False)
    results, _window, clock, _patterns = run(
        select_steps("Bursa", timeoutMs=500),
        SELECT_TARGETS,
        window=window,
        patterns=patterns,
    )
    assert results[0].status == "passed"
    assert results[0].performed_with == "SetValue"
    assert clock.at == pytest.approx(0.5), "it waited the whole timeout first"


def test_select_waits_for_a_list_that_fills_late_without_a_fixed_sleep():
    """#40's second criterion, on items rather than on existence."""
    window = ComboWindow(items=())
    clock = Clock()
    original = window.read_tree

    def filling() -> tuple[list[dict], list[str]]:
        if clock.at >= 3.0:
            window.items = CITIES
        return original()

    window.read_tree = filling  # type: ignore[method-assign]
    patterns = ComboPatterns(window)
    results, *_ = run(
        select_steps(), SELECT_TARGETS, window=window, clock=clock, patterns=patterns
    )
    assert results[0].status == "passed"
    assert patterns.chosen == ["ListItem:Ankara"]
    assert clock.at == pytest.approx(3.0)
    assert set(clock.slept) == {POLL_INTERVAL_S}
    assert results[0].duration_ms == 3000


def test_a_popup_that_closes_itself_is_opened_again_so_a_late_item_is_still_found():
    """Qt's popup shuts about a second after `Expand`, and the sample app's list fills later
    than that. Expanding only once left the item in a box playback had stopped reopening, so
    it could never be found -- the same late control SC-18 is built around (#40 Windows
    check). The guard is "the target shows no items", so this stops by itself once they are
    there."""
    window = ComboWindow(items=(), self_closing=True)
    clock = Clock()
    original = window.read_tree

    def filling() -> tuple[list[dict], list[str]]:
        if clock.at >= 3.0:
            window.items = CITIES
        return original()

    window.read_tree = filling  # type: ignore[method-assign]
    patterns = ComboPatterns(window)
    results, *_ = run(
        select_steps(), SELECT_TARGETS, window=window, clock=clock, patterns=patterns
    )
    assert results[0].status == "passed"
    assert patterns.chosen == ["ListItem:Ankara"]
    assert patterns.done.count("Expand") > 1, "it reopened the box that closed itself"
    assert clock.at == pytest.approx(3.0)
    assert set(clock.slept) == {POLL_INTERVAL_S}


def test_the_count_in_the_message_is_the_most_items_ever_seen_not_the_last():
    """A self-closing popup holds nothing at the deadline, so the last count is 0 and "the
    target shows no items at all" would tell the tester the opposite of the truth: the list
    plainly had three and the text is what is wrong."""
    window = ComboWindow(self_closing=True)
    patterns = ComboPatterns(window)
    results, *_ = run(
        select_steps("Bursa", timeoutMs=500),
        SELECT_TARGETS,
        window=window,
        patterns=patterns,
    )
    assert results[0].status == "failed"
    assert results[0].message == (
        'list.city: no item has the text "Bursa" after 500 ms; the target offers 3 items'
    )


def test_a_target_that_vanishes_mid_select_says_so():
    """ "It was there and now it is not" is a different fact from "it has no such item"."""
    window = ComboWindow(items=())
    original = window.read_tree

    def vanishing() -> tuple[list[dict], list[str]]:
        if window.reads >= 1:
            window.gone = True
        return original()

    window.read_tree = vanishing  # type: ignore[method-assign]
    results, *_ = run(
        select_steps("Ankara", timeoutMs=500),
        SELECT_TARGETS,
        window=window,
        patterns=ComboPatterns(window),
    )
    assert results[0].status == "failed"
    assert "no element matches list.city" in results[0].message
    assert 'while choosing "Ankara"' in results[0].message


@pytest.mark.parametrize("value", ["", None])
def test_a_select_without_the_item_text_is_refused(value):
    """The schema requires a non-empty value: "choose the item whose text is" nothing is not a
    choice, and an empty value would match an item with no text."""
    step = {"keyword": "Select", "target": "list.city"}
    if value is not None:
        step["value"] = value
    results, *_ = run({"version": "0.2", "steps": [step]}, SELECT_TARGETS)
    assert results[0].status == "failed"
    assert "needs the text of the item to choose" in results[0].message


def test_a_failed_select_leaves_the_list_open_for_the_screenshot():
    """The run stops at a failed step, and the open list with its items in it is the evidence
    a tester needs in the screenshot (#54)."""
    window = ComboWindow()
    patterns = ComboPatterns(window)
    results, *_ = run(
        select_steps("Bursa", timeoutMs=500),
        SELECT_TARGETS,
        window=window,
        patterns=patterns,
    )
    assert results[0].status == "failed"
    assert patterns.done == ["Expand"]
    assert window.opened is True


# --- SelectRow and the row checks (#40) ----------------------------------------------------

GRID_TARGETS = {
    "main.customerGrid": {"properties": {"automationId": grids.CUSTOMER_GRID}},
    "main.entryList": {"properties": {"automationId": grids.ENTRY_LIST}},
    "main.cityList": {"properties": {"automationId": grids.CITY_LIST}},
}


def select_row(row, target: str = "main.entryList", **extra) -> dict:
    return {
        "version": "0.2",
        "steps": [{"keyword": "SelectRow", "target": target, "row": row, **extra}],
    }


def verify_row(checkpoint, target: str = "main.customerGrid", **extra) -> dict:
    return {
        "version": "0.2",
        "steps": [
            {"keyword": "Verify", "target": target, "checkpoint": checkpoint, **extra}
        ],
    }


def test_select_row_by_position_selects_that_row():
    window = grids.Reader(grids.entry_list())
    patterns = grids.Patterns()
    results, *_ = run(
        select_row({"index": 2}), GRID_TARGETS, window=window, patterns=patterns
    )
    assert results[0].status == "passed"
    assert results[0].performed_with == "SelectionItem"
    assert results[0].message is None
    assert patterns.selected == ["row:1"], "index counts from 1, GridItem from 0"


def test_select_row_by_a_key_cell_selects_the_first_row_that_matches():
    window = grids.Reader(grids.customer_grid())
    patterns = grids.Patterns()
    results, *_ = run(
        select_row({"value": "Demir", "column": "Soyad"}, "main.customerGrid"),
        GRID_TARGETS,
        window=window,
        patterns=patterns,
    )
    assert results[0].status == "passed"
    assert patterns.selected == ["grid-cell:1,0"], (
        "a Qt table has no row element, so its first cell is what selects the row"
    )
    assert results[0].message is None


def test_a_view_that_selects_cells_passes_and_says_what_it_selected():
    """The ADR's open case: playback reports what it selected instead of claiming the row, and
    a failure would be wrong -- a pilot app's selection behaviour is not ours to change."""
    window = grids.Reader(grids.customer_grid())
    patterns = grids.Patterns(selects_rows=False)
    results, *_ = run(
        select_row({"index": 1}, "main.customerGrid"),
        GRID_TARGETS,
        window=window,
        patterns=patterns,
    )
    assert results[0].status == "passed"
    assert results[0].message == (
        "main.customerGrid: the target selects cells rather than rows, so the first cell of "
        "row 1 is selected"
    )


def test_a_row_that_is_not_there_says_how_many_rows_the_target_has():
    window = grids.Reader(grids.entry_list())
    results, *_ = run(
        select_row({"index": 5}, timeoutMs=500),
        GRID_TARGETS,
        window=window,
        patterns=grids.Patterns(),
    )
    assert results[0].status == "failed"
    assert results[0].message == (
        "main.entryList: row 5 was not found after 500 ms; the target has 2 rows"
    )


def test_select_row_waits_for_a_row_that_arrives_after_three_seconds():
    """A grid is ready before its rows are (SC-18), which the target's smart wait cannot see --
    the reason the ADR gives SelectRow a wait of its own."""
    window = grids.Reader(grids.entry_list(()))
    clock = Clock()
    original = window.read_tree

    def filling() -> tuple[list[dict], list[str]]:
        if clock.at >= 3.0:
            window.content = grids.entry_list()
        return original()

    window.read_tree = filling  # type: ignore[method-assign]
    patterns = grids.Patterns()
    results, *_ = run(
        select_row({"value": "GitHub"}),
        GRID_TARGETS,
        window=window,
        clock=clock,
        patterns=patterns,
    )
    assert results[0].status == "passed"
    assert patterns.selected == ["row:1"]
    assert clock.at == pytest.approx(3.0)
    assert set(clock.slept) == {POLL_INTERVAL_S}
    assert results[0].duration_ms == 3000


def test_a_row_the_application_refuses_to_select_is_its_own_failure():
    window = grids.Reader(grids.entry_list())
    results, *_ = run(
        select_row({"index": 1}, timeoutMs=0),
        GRID_TARGETS,
        window=window,
        patterns=grids.Patterns(refuses=True),
    )
    assert results[0].status == "failed"
    assert results[0].message == (
        "main.entryList: row 1 is there, but the application refused to select it "
        "(SelectionItem and LegacyIAccessible were tried)"
    )


def test_a_select_row_with_no_row_fails_before_reading_the_window():
    """A step whose own shape is wrong is a client bug, and spending the timeout on it before
    saying so helps nobody."""
    window = grids.Reader(grids.entry_list())
    results, _window, clock, _patterns = run(
        {
            "version": "0.2",
            "steps": [{"keyword": "SelectRow", "target": "main.entryList"}],
        },
        GRID_TARGETS,
        window=window,
    )
    assert results[0].status == "failed"
    assert results[0].message == "main.entryList: the step names no row"
    assert window.reads == 0
    assert clock.slept == []


def test_a_grid_whose_cells_do_not_report_their_row_says_so_rather_than_guessing():
    window = grids.Reader(grids.customer_grid())
    results, *_ = run(
        select_row({"index": 1}, "main.customerGrid", timeoutMs=0),
        GRID_TARGETS,
        window=window,
        patterns=Patterns(),
    )
    assert results[0].status == "failed"
    assert "cannot tell which cells make up a row" in results[0].message


def test_row_count_reads_the_grid_pattern_and_passes():
    window = grids.Reader(grids.customer_grid())
    results, *_ = run(
        verify_row({"property": "rowCount", "operator": "equals", "expected": 7}),
        GRID_TARGETS,
        window=window,
        patterns=grids.Patterns(row_count=7),
    )
    assert results[0].status == "passed"


def test_row_count_is_worded_exactly_as_promised_on_pr_231():
    window = grids.Reader(grids.customer_grid())
    results, *_ = run(
        verify_row(
            {"property": "rowCount", "operator": "equals", "expected": 3},
            timeoutMs=500,
        ),
        GRID_TARGETS,
        window=window,
        patterns=grids.Patterns(),
    )
    assert results[0].status == "failed"
    assert results[0].message == (
        "main.customerGrid: rowCount should be 3, it is 2 after 500 ms"
    )


def test_row_exists_passes_on_a_row_that_is_there():
    window = grids.Reader(grids.customer_grid())
    results, *_ = run(
        verify_row(
            {
                "property": "rowExists",
                "operator": "equals",
                "expected": True,
                "row": {"value": "Yılmaz", "column": "Soyad"},
            }
        ),
        GRID_TARGETS,
        window=window,
        patterns=grids.Patterns(),
    )
    assert results[0].status == "passed"


def test_row_exists_failing_is_worded_exactly_as_promised_on_pr_231():
    window = grids.Reader(grids.customer_grid((("Ayşe", "Demir", "Ankara"),)))
    results, *_ = run(
        verify_row(
            {
                "property": "rowExists",
                "operator": "equals",
                "expected": True,
                "row": {"value": "Yılmaz", "column": "Soyad"},
            },
            timeoutMs=500,
        ),
        GRID_TARGETS,
        window=window,
        patterns=grids.Patterns(),
    )
    assert results[0].status == "failed"
    assert results[0].message == (
        'main.customerGrid: a row with "Yılmaz" in "Soyad" should exist, none does '
        "after 500 ms"
    )


def test_a_cell_check_names_the_cell_and_both_values():
    window = grids.Reader(grids.customer_grid())
    results, *_ = run(
        verify_row(
            {
                "property": "cell",
                "operator": "equals",
                "expected": "Yılmaz",
                "row": {"index": 2},
                "column": "Soyad",
            },
            timeoutMs=0,
        ),
        GRID_TARGETS,
        window=window,
        patterns=grids.Patterns(),
    )
    assert results[0].status == "failed"
    assert results[0].message == (
        'main.customerGrid: the "Soyad" cell of row 2 should be "Yılmaz", it is "Demir"'
    )


def test_a_cell_check_passes_on_a_keepass_list_item_s_column_child():
    """KeePass 2's list has no Table pattern, so this is the shape a `cell` check meets in a
    pilot app -- read through the ListItem's Text children in header order."""
    window = grids.Reader(grids.entry_list())
    results, *_ = run(
        verify_row(
            {
                "property": "cell",
                "operator": "contains",
                "expected": "@example.com",
                "row": {"value": "Gmail"},
                "column": "User Name",
            },
            "main.entryList",
        ),
        GRID_TARGETS,
        window=window,
        patterns=grids.Patterns(),
    )
    assert results[0].status == "passed"


def test_a_column_the_target_does_not_have_fails_without_waiting():
    window = grids.Reader(grids.customer_grid())
    results, _window, clock, _patterns = run(
        verify_row(
            {
                "property": "cell",
                "operator": "equals",
                "expected": "Yılmaz",
                "row": {"index": 1},
                "column": "Soyadı",
            }
        ),
        GRID_TARGETS,
        window=window,
        patterns=grids.Patterns(),
    )
    assert results[0].status == "failed"
    assert 'no column "Soyadı"' in results[0].message
    assert '"Ad", "Soyad", "Şehir"' in results[0].message
    assert clock.slept == [], "a column the grid cannot name will not appear by waiting"


def test_a_cell_of_a_row_that_is_not_there_cannot_be_read():
    """ "Expected Yılmaz, got nothing" would blame the data instead of the address."""
    window = grids.Reader(grids.customer_grid())
    results, *_ = run(
        verify_row(
            {
                "property": "cell",
                "operator": "equals",
                "expected": "Yılmaz",
                "row": {"index": 9},
                "column": "Soyad",
            },
            timeoutMs=0,
        ),
        GRID_TARGETS,
        window=window,
        patterns=grids.Patterns(),
    )
    assert results[0].status == "failed"
    assert results[0].message == (
        'main.customerGrid: the "Soyad" cell of row 9 cannot be read; '
        "the target has 2 rows"
    )


def test_a_row_check_waits_for_rows_that_fill_after_three_seconds():
    """#40's second criterion once more, on rows: the grid is ready long before them."""
    window = grids.Reader(grids.customer_grid(()))
    clock = Clock()
    original = window.read_tree

    def filling() -> tuple[list[dict], list[str]]:
        if clock.at >= 3.0:
            window.content = grids.customer_grid()
        return original()

    window.read_tree = filling  # type: ignore[method-assign]
    results, *_ = run(
        verify_row({"property": "rowCount", "operator": "equals", "expected": 2}),
        GRID_TARGETS,
        window=window,
        clock=clock,
        patterns=grids.Patterns(),
    )
    assert results[0].status == "passed"
    assert clock.at == pytest.approx(3.0)
    assert set(clock.slept) == {POLL_INTERVAL_S}


def test_a_target_that_vanishes_mid_row_check_says_so():
    window = grids.Reader(grids.customer_grid())
    original = window.read_tree

    def vanishing() -> tuple[list[dict], list[str]]:
        if window.reads >= 1:
            window.gone = True
        return original()

    window.read_tree = vanishing  # type: ignore[method-assign]
    results, *_ = run(
        verify_row(
            {"property": "rowCount", "operator": "equals", "expected": 9},
            timeoutMs=500,
        ),
        GRID_TARGETS,
        window=window,
        patterns=grids.Patterns(),
    )
    assert results[0].status == "failed"
    assert "no element matches main.customerGrid" in results[0].message
    assert "while checking rowCount" in results[0].message


@pytest.mark.parametrize(
    ("checkpoint", "expected"),
    [
        (
            {
                "property": "name",
                "operator": "equals",
                "expected": "x",
                "row": {"index": 1},
            },
            "a name check carries 'row'",
        ),
        (
            {
                "property": "rowCount",
                "operator": "equals",
                "expected": 1,
                "row": {"index": 1},
            },
            "a rowCount check carries 'row'",
        ),
        (
            {
                "property": "cell",
                "operator": "equals",
                "expected": "x",
                "row": {"index": 1},
            },
            "a cell check says no column",
        ),
        (
            {"property": "rowExists", "operator": "equals", "expected": True},
            "a rowExists check says no row",
        ),
        (
            {
                "property": "rowExists",
                "operator": "equals",
                "expected": True,
                "row": {"index": 1},
                "column": "Soyad",
            },
            "a rowExists check carries 'column'",
        ),
        (
            {"property": "rowCount", "operator": "equals", "expected": "3"},
            "rowCount is checked against a whole number of rows",
        ),
    ],
)
def test_a_checkpoint_the_schema_would_refuse_fails_before_reading_the_window(
    checkpoint, expected
):
    """The schema enforces every one of these with an `if`/`then`, so a request carrying one is
    a client bug; reading it as something else would report `passed` on a different check."""
    window = grids.Reader(grids.customer_grid())
    results, *_ = run(verify_row(checkpoint), GRID_TARGETS, window=window)
    assert results[0].status == "failed"
    assert expected in results[0].message
    assert window.reads == 0


# --- two Invokes on one target (#264) ------------------------------------------------------

TWO_CLICKS = {
    "version": "0.1",
    "steps": [
        {"keyword": "Click", "target": "login.loginButton"},
        {"keyword": "Click", "target": "login.loginButton"},
    ],
}


def test_a_second_invoke_on_the_same_target_waits_out_the_gap():
    results, _window, clock, patterns = run(TWO_CLICKS)
    assert [r.status for r in results] == ["passed", "passed"]
    assert [d[0] for d in patterns.done] == ["Click", "Click"]
    assert clock.slept == [pytest.approx(INVOKE_GAP_S)]


def test_invokes_on_different_targets_do_not_wait():
    document = {
        "version": "0.1",
        "steps": [
            {"keyword": "Click", "target": "login.loginButton"},
            {"keyword": "Click", "target": "login.passwordInput"},
        ],
    }
    _results, _window, clock, _patterns = run(document)
    assert clock.slept == []


def test_only_what_is_left_of_the_gap_is_waited():
    clock = Clock()
    spacing = InvokeSpacing()
    one = {"version": "0.1", "steps": TWO_CLICKS["steps"][:1]}
    run(one, clock=clock, spacing=spacing)
    clock.at += 0.15
    run(one, clock=clock, spacing=spacing)
    assert clock.slept == [pytest.approx(INVOKE_GAP_S - 0.15)]


def test_a_click_long_after_the_last_one_does_not_wait():
    clock = Clock()
    spacing = InvokeSpacing()
    one = {"version": "0.1", "steps": TWO_CLICKS["steps"][:1]}
    run(one, clock=clock, spacing=spacing)
    clock.at += INVOKE_GAP_S
    run(one, clock=clock, spacing=spacing)
    assert clock.slept == []


def test_the_gap_holds_across_two_runs_as_the_client_sends_them():
    """The client plays each step as its own run (#44); #264's two clicks were in two."""
    clock = Clock()
    one = {"version": "0.1", "steps": TWO_CLICKS["steps"][:1]}
    run(one, clock=clock)
    run(one, clock=clock)
    assert clock.slept == [pytest.approx(INVOKE_GAP_S)]


def test_a_click_that_did_not_invoke_leaves_no_mark():
    class ToggleOnly(Patterns):
        def __call__(self, element, name):
            if name != "Toggle":
                return None
            recorder = self

            class Fake:
                def Toggle(self) -> None:
                    recorder.done.append(("Toggle", element, None))

            return Fake()

    results, _window, clock, _patterns = run(TWO_CLICKS, patterns=ToggleOnly())
    assert [r.performed_with for r in results] == ["Toggle", "Toggle"]
    assert clock.slept == []


def test_a_mark_from_another_clock_never_makes_a_step_wait_longer_than_the_gap():
    spacing = InvokeSpacing()
    spacing.invoked("login.loginButton", 50.0)
    slept: list[float] = []
    assert spacing.wait("login.loginButton", lambda: 0.0, slept.append) == 0.0
    assert slept == []
