"""#63's triage: which of FR-35's five a failed step gets, and which get none.

Two halves, and the second is the one that would catch a real regression:

- the **mapping** on its own, one case per exception type;
- the **runner**, driven to each failure for real with #26's fakes, so that a `category` that
  stops being filled — or starts being filled with the wrong value — fails here rather than
  quietly changing what RQ2 and RQ5 measure.

The rule this module defends is that a failure the **agent** caused never wears one of the five.
A `timeout` that was really "this agent has no `SelectRow` yet" would be AYNA measuring its own
unfinished state and calling it the application's flakiness.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ayna_agent.errors import SnapshotTimeout
from ayna_agent.playback import triage
from ayna_agent.playback.actions import ActionFailed
from ayna_agent.playback.checkpoint import CheckpointError, Unreadable
from ayna_agent.playback.items import ITEM_NOT_FOUND, ITEM_REFUSED, SelectFailed
from ayna_agent.playback.resolve import Ambiguous, NotFound, NotReady, Unsupported
from ayna_agent.playback.rows import (
    ROW_NOT_FOUND,
    ROW_REFUSED,
    RowError,
    RowFailed,
    RowsUnavailable,
)
from ayna_agent.playback.runner import run_steps

TRIAL_TREE = Path(__file__).resolve().parent / "data" / "trial-app-tree.json"

USERNAME = "QApplication.loginWindow.usernameInput"
LOGIN = "QApplication.loginWindow.loginButton"

TARGETS = {
    "login.userNameInput": {"properties": {"automationId": USERNAME}},
    "login.loginButton": {"properties": {"automationId": LOGIN}},
    "login.gone": {"properties": {"automationId": "no-such-element"}},
    "login.ambiguous": {"properties": {"controlType": "Edit"}},
    "login.unmatchable": {"properties": {"patternSalad": "nope"}},
}


# --- the mapping on its own -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (NotFound("login.gone", [{"automationId": "x"}]), triage.ELEMENT_NOT_FOUND),
        (
            Ambiguous("login.x", {"controlType": "Edit"}, 3, "primary"),
            triage.ELEMENT_NOT_FOUND,
        ),
        (RowFailed("row 4 was not found", ROW_NOT_FOUND), triage.ELEMENT_NOT_FOUND),
        (SelectFailed("no such item", ITEM_NOT_FOUND), triage.ELEMENT_NOT_FOUND),
        (NotReady("login.loginButton", ["enabled"]), triage.TIMEOUT),
        (SnapshotTimeout("window still not read"), triage.SEARCH_INCOMPLETE),
    ],
    ids=["notFound", "ambiguous", "rowMissing", "itemMissing", "notReady", "budget"],
)
def test_a_failure_about_the_application_gets_one_of_the_five(error, expected):
    assert triage.category_for(error) == expected
    assert expected in triage.CATEGORIES


@pytest.mark.parametrize(
    "error",
    [
        Unsupported(["patternSalad"]),
        ActionFailed("Click", "the provider refused Invoke"),
        SelectFailed("the application refused to select it", ITEM_REFUSED),
        RowFailed("the application refused to select it", ROW_REFUSED),
        CheckpointError("a checkpoint needs an operator"),
        RowError("the step names no row"),
        RowsUnavailable("not a grid"),
        Unreadable("login.statusLabel", "no Name"),
    ],
    ids=[
        "unsupported-properties",
        "action-refused",
        "item-refused",
        "row-refused",
        "malformed-checkpoint",
        "malformed-row",
        "not-a-grid",
        "unreadable",
    ],
)
def test_a_failure_the_agent_caused_gets_no_category(error):
    """None of these is evidence about the application, so none wears one of the five."""
    assert triage.category_for(error) is None


def test_every_failure_still_gets_a_reason_for_the_log():
    """Criterion 1 in the place where labelling happens, even where the contract says nothing."""
    for error in (
        Unsupported(["x"]),
        ActionFailed("Click", "no"),
        CheckpointError("bad"),
        RowError("bad"),
        RowsUnavailable("not a grid"),
        Unreadable("a", "no Name"),
        NotFound("a", [{"automationId": "x"}]),
        RuntimeError("something nobody foresaw"),
    ):
        reason = triage.reason_for(error)
        assert isinstance(reason, str) and reason, error


def test_a_malformed_checkpoint_is_not_an_assertion_failure():
    """The trap this module exists for.

    `CheckpointError` is "the checkpoint itself is wrong, whatever the application is doing" —
    its own docstring. Calling it `assertionFailed` would file a broken *test* under the
    application's failures, which is precisely the mixing #63 must not do.
    """
    assert (
        triage.category_for(CheckpointError("a checkpoint needs an operator")) is None
    )
    assert triage.reason_for(CheckpointError("bad")) == triage.REFUSED_STEP


def test_the_two_halves_of_a_row_failure_are_not_merged():
    """A row that is missing is recognition evidence; one the app refused is not."""
    assert (
        triage.category_for(RowFailed("gone", ROW_NOT_FOUND))
        == triage.ELEMENT_NOT_FOUND
    )
    assert triage.category_for(RowFailed("refused", ROW_REFUSED)) is None
    assert triage.reason_for(RowFailed("refused", ROW_REFUSED)) == triage.ACTION_REFUSED


def test_an_unknown_exception_is_not_guessed_at():
    assert triage.category_for(RuntimeError("?")) is None
    assert triage.reason_for(RuntimeError("?")) == triage.REFUSED_STEP


def test_the_five_are_exactly_the_contracts_five():
    """If the schema grows a sixth value, this fails until the module knows about it."""
    schema = json.loads(
        (
            Path(__file__).resolve().parents[2] / "schemas" / "agent-rpc.schema.json"
        ).read_text("utf-8")
    )
    assert set(schema["$defs"]["failureCategory"]["enum"]) == set(triage.CATEGORIES)


# --- the runner, driven to each failure for real ----------------------------------------------


class Window:
    """The same fake #26's tests use: the real trial-app tree from #11."""

    def __init__(self) -> None:
        self.content = json.loads(TRIAL_TREE.read_text(encoding="utf-8"))
        self.reads = 0

    def read_tree(self):
        self.reads += 1
        return self.content, [f"element-{i}" for i in range(len(self.content))]


class Clock:
    def __init__(self) -> None:
        self.t = 0.0

    def now(self) -> float:
        return self.t

    def sleep(self, seconds: float) -> None:
        self.t += seconds


def run(steps, targets=None):
    clock = Clock()
    return run_steps(
        {"version": "0.2", "steps": steps},
        TARGETS if targets is None else targets,
        Window().read_tree,
        now=clock.now,
        sleep=clock.sleep,
        patterns=lambda element, name: None,
    )


def test_a_target_that_is_not_there_is_element_not_found():
    (result,) = run([{"keyword": "Click", "target": "login.gone", "timeoutMs": 0}])
    assert result.status == "failed"
    assert result.category == triage.ELEMENT_NOT_FOUND
    assert result.to_json()["category"] == triage.ELEMENT_NOT_FOUND


def test_more_than_one_match_is_also_element_not_found():
    (result,) = run([{"keyword": "Click", "target": "login.ambiguous", "timeoutMs": 0}])
    assert result.status == "failed"
    assert result.category == triage.ELEMENT_NOT_FOUND


def test_a_property_set_playback_cannot_match_on_has_no_category():
    (result,) = run(
        [{"keyword": "Click", "target": "login.unmatchable", "timeoutMs": 0}]
    )
    assert result.status == "failed"
    assert result.category is None
    assert "category" not in result.to_json(), "absent, not null"


def test_a_keyword_this_agent_refuses_has_no_category():
    (result,) = run([{"keyword": "Scroll", "target": "login.loginButton"}])
    assert result.status == "failed"
    assert result.category is None


def test_a_step_with_no_target_has_no_category():
    (result,) = run([{"keyword": "Click"}])
    assert result.status == "failed"
    assert result.category is None


def test_a_target_the_request_forgot_has_no_category():
    (result,) = run(
        [{"keyword": "Click", "target": "login.unknown", "timeoutMs": 0}], {}
    )
    assert result.status == "failed"
    assert result.category is None


def test_a_not_run_step_carries_no_category():
    """Only a failed step is categorised; the contract says so and the server enforces it."""
    results = run(
        [
            {"keyword": "Click", "target": "login.gone", "timeoutMs": 0},
            {"keyword": "Click", "target": "login.loginButton", "timeoutMs": 0},
        ]
    )
    assert [r.status for r in results] == ["failed", "notRun"]
    assert results[1].category is None
    assert "category" not in results[1].to_json()


def test_a_passing_step_carries_no_category():
    """Asserted on a step that really passes, not behind an `if` that could skip the check."""
    # `Wait` passes as soon as the target is ready, so it needs no property and no pattern.
    (result,) = run(
        [{"keyword": "Wait", "target": "login.loginButton", "timeoutMs": 0}]
    )
    assert result.status == "passed", result.message
    assert result.category is None
    assert "category" not in result.to_json()


def test_a_verify_that_does_not_hold_is_an_assertion_failure():
    (result,) = run(
        [
            {
                "keyword": "Verify",
                "target": "login.loginButton",
                "checkpoint": {
                    "property": "name",
                    "operator": "equals",
                    "expected": "this is not the button's name",
                },
                "timeoutMs": 0,
            }
        ]
    )
    assert result.status == "failed"
    assert result.category == triage.ASSERTION_FAILED


def test_a_malformed_checkpoint_fails_the_step_without_a_category():
    """The same step shape as above, but the checkpoint is wrong rather than unmet."""
    (result,) = run(
        [
            {
                "keyword": "Verify",
                "target": "login.loginButton",
                "checkpoint": {"property": "name", "operator": "isAubergine"},
                "timeoutMs": 0,
            }
        ]
    )
    assert result.status == "failed"
    assert result.category is None, (
        "a checkpoint that is wrong is the test's fault, not the application's"
    )
