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

import pytest

from ayna_agent.playback import runner
from ayna_agent.playback.runner import (
    DEFAULT_TIMEOUT_MS,
    POLL_INTERVAL_S,
    SUPPORTED_STEP_VERSIONS,
    StepDocumentError,
    run_steps,
)

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


@pytest.mark.parametrize("keyword", ["Select", "Verify", "SelectRow", "Nonsense"])
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
