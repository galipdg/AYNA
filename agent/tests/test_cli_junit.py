"""#66's JUnit XML: does it validate, and does it say the right thing?

The first half is the acceptance criterion taken literally — **every document this module can
produce is validated against the real schema** (`tests/data/junit-10.xsd`, the Apache Ant /
JUnitReport schema, Apache-2.0). That is not ceremony: writing the validation first changed the
design four times, because the format everyone writes by hand is not the format the schema
allows. `xmlschema` is a dev-only dependency and the product never imports it.

The second half is about meaning rather than shape, and one case carries most of it: a run whose
tests all passed but whose results never reached the server exits 2 (FR-23). The testcases must
stay green — no test failed — while `system-err` says why the job did not.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from ayna_cli.junit import junit_bytes, summary_of, write_junit
from ayna_cli.run import SuiteOutcome, TestOutcome

xmlschema = pytest.importorskip("xmlschema", reason="dev-only; install with .[dev]")

SCHEMA_PATH = Path(__file__).resolve().parent / "data" / "junit-10.xsd"


@pytest.fixture(scope="module")
def schema():
    return xmlschema.XMLSchema(str(SCHEMA_PATH))


def validate(schema, document: bytes) -> None:
    """Raise with the schema's own words when a document does not validate."""
    schema.validate(ET.fromstring(document))


# --- the outcomes a run can have ------------------------------------------------------------


def results(*statuses: str, message: str | None = None, category: str | None = None):
    out = []
    for index, status in enumerate(statuses):
        step = {"stepIndex": index, "status": status, "durationMs": 40}
        if status != "passed":
            if message:
                step["message"] = message
            if category:
                step["category"] = category
        out.append(step)
    return out


def passed(name="Login succeeds", scenario="SC-14"):
    return TestOutcome(name, scenario, "passed", results("passed", "passed"))


def failed(name="Detail form refuses an empty name", scenario="SC-34"):
    return TestOutcome(
        name,
        scenario,
        "failed",
        results(
            "passed",
            "failed",
            message='detail.statusLabel: name should be "Ad alanı zorunlu"',
            category="assertionFailed",
        ),
    )


def errored(name="Wizard", scenario=None):
    return TestOutcome(
        name,
        scenario,
        "failed",
        [],
        error="no window with className 'WizardWindow' within 60 s",
    )


def undelivered(name="Login succeeds"):
    test = passed(name)
    test.delivery_error = (
        "PUT /api/runs/r1/results/0: 409 the step already has a result"
    )
    return test


def outcome_of(*tests, error: str | None = None) -> SuiteOutcome:
    return SuiteOutcome(tests=list(tests), error=error)


# --- criterion 1: it validates --------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "outcome"),
    [
        ("all passed", outcome_of(passed(), passed("Second", "SC-15"))),
        ("one failed", outcome_of(passed(), failed())),
        ("one errored", outcome_of(passed(), errored())),
        ("every kind", outcome_of(passed(), failed(), errored(), undelivered("Third"))),
        ("undelivered only", outcome_of(undelivered())),
        ("run-level error", outcome_of(passed(), error="the agent stopped")),
        ("no tests at all", outcome_of()),
        (
            "no scenario ids",
            outcome_of(TestOutcome("Bare", None, "passed", results("passed"))),
        ),
    ],
)
def test_every_document_this_module_writes_validates(schema, name, outcome):
    validate(schema, junit_bytes("smoke", outcome))


def test_turkish_text_validates_and_survives(schema):
    """Test names and application messages are Turkish; UTF-8 all the way out."""
    test = TestOutcome(
        "Giriş Denemesi",
        "SC-14",
        "failed",
        results("failed", message="Kullanıcı adı veya şifre hatalı"),
    )
    document = junit_bytes("Örnek Paket", outcome_of(test))
    validate(schema, document)
    text = document.decode("utf-8")
    assert "Giriş Denemesi" in text
    assert "Kullanıcı adı veya şifre hatalı" in text


def test_a_message_with_xml_in_it_is_escaped_not_injected(schema):
    """A step message is application text and can contain anything."""
    test = TestOutcome(
        "Odd",
        "SC-99",
        "failed",
        results("failed", message='</failure><evil a="1">& <![CDATA['),
    )
    document = junit_bytes("smoke", outcome_of(test))
    validate(schema, document)
    assert b"<evil" not in document
    parsed = ET.fromstring(document)
    assert "evil" in parsed.find("testcase/failure").get("message")


def test_the_timestamp_has_no_timezone_because_the_schema_forbids_one(schema):
    """The one place this project departs from "always carry an offset"."""
    moment = datetime(2026, 11, 15, 21, 4, 5, tzinfo=timezone(timedelta(hours=3)))
    document = junit_bytes("smoke", outcome_of(passed()), started_at=moment)
    validate(schema, document)

    root = ET.fromstring(document)
    assert root.get("timestamp") == "2026-11-15T21:04:05"
    assert "+" not in root.get("timestamp")
    # Nothing is lost: the offset-carrying stamp is kept as a property.
    started = [
        p for p in root.findall("properties/property") if p.get("name") == "startedAt"
    ]
    assert started[0].get("value") == "2026-11-15T21:04:05+03:00"


def test_the_required_sequence_is_in_the_order_the_schema_demands(schema):
    document = junit_bytes("smoke", outcome_of(passed(), failed()))
    validate(schema, document)
    tags = [child.tag for child in ET.fromstring(document)]
    assert tags == ["properties", "testcase", "testcase", "system-out", "system-err"]


def test_properties_is_written_even_when_there_is_nothing_to_say(schema):
    """Required and first in the sequence, which is easy to leave out and invalid to."""
    document = junit_bytes("smoke", outcome_of())
    validate(schema, document)
    assert ET.fromstring(document).find("properties") is not None


# --- what the document means -----------------------------------------------------------------


def test_a_failed_test_is_a_failure_and_an_unplayable_one_is_an_error():
    """The schema allows at most one of the two, so the line has to be drawn, not hedged."""
    document = junit_bytes("smoke", outcome_of(failed(), errored()))
    summary = summary_of(document)
    assert summary["failures"] == 1
    assert summary["errors"] == 1
    assert [case["outcome"] for case in summary["cases"]] == ["failure", "error"]


def test_a_passing_test_carries_neither():
    root = ET.fromstring(junit_bytes("smoke", outcome_of(passed())))
    case = root.find("testcase")
    assert list(case) == [], "a passing testcase is empty"


def test_the_counts_match_the_cases():
    document = junit_bytes("smoke", outcome_of(passed(), failed(), errored()))
    root = ET.fromstring(document)
    assert root.get("tests") == "3"
    assert root.get("failures") == "1"
    assert root.get("errors") == "1"
    assert len(root.findall("testcase")) == 3


def test_the_failure_message_is_the_step_s_and_the_type_is_its_category():
    """#63's category is the most useful `type` a reporter could group by."""
    failure = ET.fromstring(junit_bytes("smoke", outcome_of(failed()))).find(
        "testcase/failure"
    )
    assert "Ad alanı zorunlu" in failure.get("message")
    assert failure.get("type") == "assertionFailed"


def test_the_failure_text_lists_every_step_so_a_reader_sees_where_it_got_to():
    failure = ET.fromstring(junit_bytes("smoke", outcome_of(failed()))).find(
        "testcase/failure"
    )
    assert "step 0: passed" in failure.text
    assert "step 1: failed" in failure.text


def test_a_test_with_no_scenario_still_has_a_classname():
    root = ET.fromstring(
        junit_bytes("smoke", outcome_of(TestOutcome("Bare", None, "passed", [])))
    )
    assert root.find("testcase").get("classname") == "smoke.test"


def test_a_test_s_time_is_the_sum_of_its_steps():
    root = ET.fromstring(junit_bytes("smoke", outcome_of(passed())))
    assert root.find("testcase").get("time") == "0.080"


# --- the case the whole design turns on ------------------------------------------------------


def test_a_green_run_whose_results_were_not_stored_stays_green_and_says_why(schema):
    """FR-23's exit 2. The tests passed; the job still failed, and a reader must find out why.

    Marking the testcases red would be a lie about the application, and leaving the file silent
    would make a red job look like a reporting bug. So: green cases, and `system-err` carries
    the reason and the exit code.
    """
    outcome = outcome_of(undelivered(), undelivered("Second"))
    document = junit_bytes("smoke", outcome)
    validate(schema, document)

    summary = summary_of(document)
    assert summary["failures"] == 0 and summary["errors"] == 0
    assert all(case["outcome"] == "passed" for case in summary["cases"])

    root = ET.fromstring(document)
    system_err = root.find("system-err").text
    assert "were not stored on the server" in system_err
    assert "409" in system_err
    assert "exit code 2" in system_err


def test_a_run_that_could_not_be_completed_says_so_in_system_err(schema):
    document = junit_bytes("smoke", outcome_of(passed(), error="the agent stopped"))
    validate(schema, document)
    assert "the agent stopped" in ET.fromstring(document).find("system-err").text


def test_a_clean_run_leaves_system_err_empty_rather_than_inventing_something(schema):
    document = junit_bytes("smoke", outcome_of(passed()))
    validate(schema, document)
    assert not (ET.fromstring(document).find("system-err").text or "").strip()


def test_system_out_lists_every_test_either_way():
    text = (
        ET.fromstring(junit_bytes("smoke", outcome_of(passed(), failed())))
        .find("system-out")
        .text
    )
    assert "1 of 2 tests passed." in text
    assert "pass  Login succeeds (SC-14)" in text
    assert "FAIL  Detail form refuses an empty name (SC-34)" in text


# --- writing it ------------------------------------------------------------------------------


def test_the_file_is_written_and_validates_from_disk(schema, tmp_path):
    target = tmp_path / "deep" / "out.xml"
    write_junit(target, "smoke", outcome_of(passed(), failed()))
    assert target.exists(), "the parent directory was made"
    validate(schema, target.read_bytes())


def test_the_file_starts_with_an_xml_declaration(tmp_path):
    target = tmp_path / "out.xml"
    write_junit(target, "smoke", outcome_of(passed()))
    assert target.read_bytes().startswith(b"<?xml version='1.0' encoding='utf-8'?>")
