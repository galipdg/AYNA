"""#63's decision log: one JSONL line per failed step, with enough to label it later.

The log is the half of #63 that the contract cannot carry: `reason` is finer than FR-35's five
and is never absent, and `tried` records the property sets, without which "no element matches
login.loginButton" cannot be judged by anyone reading it afterwards.

Two properties matter more than the field list and are tested hardest: **writing the log never
fails the run**, and **only failed steps are logged**.
"""

from __future__ import annotations

import json

import pytest
from playback_fakes import TARGETS, Clock, Window

from ayna_agent.playback import triage
from ayna_agent.playback.decisions import (
    FORMAT_VERSION,
    Decision,
    DecisionLog,
    export_jsonl,
    now_stamp,
)
from ayna_agent.playback.runner import run_steps


def a_decision(**over) -> Decision:
    base = {
        "at": "2026-11-15T14:03:11.250+03:00",
        "reason": triage.ELEMENT_NOT_FOUND,
        "category": triage.ELEMENT_NOT_FOUND,
        "step_index": 2,
        "keyword": "Click",
        "target": "login.loginButton",
        "message": "no element matches login.loginButton",
    }
    return Decision(**{**base, **over})


# --- the line itself --------------------------------------------------------------------


def test_a_line_carries_what_a_labeller_needs():
    written = a_decision(
        tried=[{"automationId": "loginButton"}, {"name": "Giriş"}],
        matched="fallback",
        duration_ms=10_000,
        test_name="Giriş Denemesi",
    ).to_json()

    assert written["v"] == FORMAT_VERSION
    assert written["reason"] == triage.ELEMENT_NOT_FOUND
    assert written["category"] == triage.ELEMENT_NOT_FOUND
    assert written["stepIndex"] == 2
    assert written["target"] == "login.loginButton"
    assert written["tried"] == [{"automationId": "loginButton"}, {"name": "Giriş"}]
    assert written["matched"] == "fallback"
    assert written["testName"] == "Giriş Denemesi"


def test_a_failure_with_no_contract_category_still_has_a_reason():
    """The whole point: absent in the contract, never absent here."""
    written = a_decision(reason=triage.REFUSED_STEP, category=None).to_json()
    assert written["reason"] == triage.REFUSED_STEP
    assert "category" not in written


def test_an_unlabelled_line_has_no_label_key():
    """So an unlabelled line and one a person labelled "unknown" are never confused (#64)."""
    assert "label" not in a_decision().to_json()
    assert a_decision(label="unknown").to_json()["label"] == "unknown"


def test_empty_tried_is_left_out_rather_than_written_as_an_empty_list():
    assert "tried" not in a_decision().to_json()


def test_the_stamp_has_an_offset_and_milliseconds():
    from datetime import datetime

    stamp = now_stamp()
    assert datetime.fromisoformat(stamp).tzinfo is not None
    assert "." in stamp


# --- the file ------------------------------------------------------------------------------


def test_lines_are_appended_not_rewritten(tmp_path):
    log = DecisionLog(tmp_path / "decisions.jsonl")
    log.append(a_decision(step_index=0))
    log.append(a_decision(step_index=1))

    lines = (tmp_path / "decisions.jsonl").read_text(encoding="utf-8").splitlines()
    assert [json.loads(line)["stepIndex"] for line in lines] == [0, 1]


def test_a_second_run_adds_to_the_same_file(tmp_path):
    """Two runs appending without a merge is the reason for JSONL over a JSON array."""
    path = tmp_path / "decisions.jsonl"
    DecisionLog(path).append(a_decision(step_index=0))
    DecisionLog(path).append(a_decision(step_index=1))
    assert len(list(DecisionLog(path).read())) == 2


def test_the_directory_is_made_on_the_first_line(tmp_path):
    log = DecisionLog(tmp_path / "deep" / "deeper" / "decisions.jsonl")
    log.append(a_decision())
    assert log.path.exists()


def test_turkish_is_written_as_turkish_not_as_escapes(tmp_path):
    """`ensure_ascii=False` and UTF-8: a Windows runner's default would be cp1252."""
    log = DecisionLog(tmp_path / "d.jsonl")
    log.append(a_decision(message="Kullanıcı adı veya şifre hatalı", test_name="Giriş"))
    raw = log.path.read_text(encoding="utf-8")
    assert "Kullanıcı adı veya şifre hatalı" in raw
    assert "\\u" not in raw


def test_a_half_written_last_line_does_not_lose_the_rest(tmp_path):
    """A cancelled CI job leaves one; the hundred before it are still the data."""
    path = tmp_path / "d.jsonl"
    DecisionLog(path).append(a_decision(step_index=0))
    with path.open("a", encoding="utf-8") as out:
        out.write('{"v": 1, "reason": "elementNot')
    assert [d["stepIndex"] for d in DecisionLog(path).read()] == [0]


def test_reading_a_log_that_is_not_there_yields_nothing(tmp_path):
    assert list(DecisionLog(tmp_path / "never.jsonl").read()) == []


def test_an_export_is_atomic_and_leaves_no_temporary(tmp_path):
    path = export_jsonl(
        [a_decision(step_index=0), a_decision(step_index=1)], tmp_path / "out.jsonl"
    )
    assert len(path.read_text(encoding="utf-8").splitlines()) == 2
    assert [p.name for p in tmp_path.iterdir()] == ["out.jsonl"], (
        "no temp file left behind"
    )


# --- what the runner logs --------------------------------------------------------------------


def run(steps, log=None, context=None):
    clock = Clock()
    return run_steps(
        {"version": "0.2", "steps": steps},
        TARGETS,
        Window().read_tree,
        now=clock.now,
        sleep=clock.sleep,
        patterns=lambda element, name: None,
        decisions=log,
        context=context,
    )


def test_a_failed_step_is_logged_with_its_reason_and_what_was_tried(tmp_path):
    log = DecisionLog(tmp_path / "d.jsonl")
    run([{"keyword": "Click", "target": "login.gone", "timeoutMs": 0}], log)

    (line,) = list(log.read())
    assert line["reason"] == triage.ELEMENT_NOT_FOUND
    assert line["category"] == triage.ELEMENT_NOT_FOUND
    assert line["keyword"] == "Click"
    assert line["target"] == "login.gone"
    assert line["tried"] == [{"automationId": "no-such-element"}]
    assert "no element matches" in line["message"]


def test_a_failure_the_agent_caused_is_logged_with_a_reason_and_no_category(tmp_path):
    log = DecisionLog(tmp_path / "d.jsonl")
    run([{"keyword": "Click", "target": "login.unmatchable", "timeoutMs": 0}], log)

    (line,) = list(log.read())
    assert line["reason"] == triage.REFUSED_PROPERTIES
    assert "category" not in line


def test_a_refused_keyword_is_logged_too(tmp_path):
    """Criterion 1 holds here even where the contract has nothing to say."""
    log = DecisionLog(tmp_path / "d.jsonl")
    run([{"keyword": "Scroll", "target": "login.loginButton"}], log)
    (line,) = list(log.read())
    assert line["reason"] == triage.REFUSED_STEP
    assert "category" not in line


def test_passed_and_not_run_steps_are_not_logged(tmp_path):
    log = DecisionLog(tmp_path / "d.jsonl")
    results = run(
        [
            {"keyword": "Wait", "target": "login.loginButton", "timeoutMs": 0},
            {"keyword": "Click", "target": "login.gone", "timeoutMs": 0},
            {"keyword": "Wait", "target": "login.loginButton", "timeoutMs": 0},
        ],
        log,
    )
    assert [r.status for r in results] == ["passed", "failed", "notRun"]
    assert [line["stepIndex"] for line in log.read()] == [1], "only the failure"


def test_the_context_a_run_knows_and_playback_does_not_is_carried(tmp_path):
    log = DecisionLog(tmp_path / "d.jsonl")
    run(
        [{"keyword": "Click", "target": "login.gone", "timeoutMs": 0}],
        log,
        context={
            "run_id": "r1",
            "test_name": "Giriş Denemesi",
            "window_title": "Giriş",
        },
    )
    (line,) = list(log.read())
    assert line["runId"] == "r1"
    assert line["testName"] == "Giriş Denemesi"
    assert line["windowTitle"] == "Giriş"


def test_no_log_means_no_log_and_no_complaint(tmp_path):
    results = run([{"keyword": "Click", "target": "login.gone", "timeoutMs": 0}])
    assert results[0].status == "failed"
    assert not list(tmp_path.iterdir())


def test_a_log_that_cannot_be_written_does_not_fail_the_run(tmp_path, caplog):
    """A full disk in the measurement harness must not cost the run it was measuring."""

    class Broken(DecisionLog):
        def append(self, decision):
            raise OSError("no space left on device")

    with caplog.at_level("WARNING"):
        results = run(
            [{"keyword": "Click", "target": "login.gone", "timeoutMs": 0}],
            Broken(tmp_path / "d.jsonl"),
        )

    assert results[0].status == "failed"
    assert results[0].category == triage.ELEMENT_NOT_FOUND, "the result is untouched"
    assert "could not log step 0" in caplog.text


@pytest.mark.parametrize(
    ("steps", "expected"),
    [
        (
            [{"keyword": "Click", "target": "login.ambiguous", "timeoutMs": 0}],
            triage.ELEMENT_NOT_FOUND,
        ),
        ([{"keyword": "Click"}], triage.REFUSED_STEP),
        (
            [
                {
                    "keyword": "Verify",
                    "target": "login.loginButton",
                    "checkpoint": {
                        "property": "name",
                        "operator": "equals",
                        "expected": "not the name",
                    },
                    "timeoutMs": 0,
                }
            ],
            triage.ASSERTION_FAILED,
        ),
    ],
    ids=["ambiguous", "no-target", "assertion"],
)
def test_every_kind_of_failure_reaches_the_log_with_a_reason(tmp_path, steps, expected):
    log = DecisionLog(tmp_path / "d.jsonl")
    run(steps, log)
    (line,) = list(log.read())
    assert line["reason"] == expected
