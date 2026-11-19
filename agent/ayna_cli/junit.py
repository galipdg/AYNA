"""A run as JUnit XML, so a CI server can show it as tests (#66, FR-24).

    ayna run --from-file suite.json --junit out.xml

**Written against the schema, not against what other tools happen to accept.** The criterion is
that the file validates, and the Apache Ant / JUnitReport schema (vendored at
`agent/tests/data/junit-10.xsd`, Apache-2.0) is stricter than the format most people write by
hand. Checking against it changed four things, every one of which the project was getting wrong
in the stand-in this command replaces (#249's `run_suite.py`):

- the root is a single **`<testsuite>`**. A `<testsuite>` nested in `<testsuites>` additionally
  requires `package` and `id`, which carry nothing here;
- **`<properties>` is required**, first in the sequence, even when it holds nothing;
- **`<system-out>` and `<system-err>` belong to the suite and are both required** — not to a
  `<testcase>`, which is where it is tempting to put a step log;
- `timestamp` and `hostname` are required on the suite, and `timestamp` **may not carry a
  timezone** (the schema's own words), which is the one place this project departs from its
  "always an offset" rule. The offset-carrying stamp is kept as a property instead, so nothing
  is lost.

A `<testcase>` holds **at most one** of `skipped`, `error` or `failure`, so the distinction has
to be made rather than hedged: a test whose steps ran and did not pass is a **failure**, and a
test that could not be played at all — no window, a suite the agent refused — is an **error**.
That is the same line `TestOutcome` already draws between `status` and `error`.
"""

from __future__ import annotations

import socket
import xml.etree.ElementTree as ET
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from ayna_cli.run import SuiteOutcome, TestOutcome

#: What the schema's `ISO8601_DATETIME_PATTERN` allows: no fraction, no offset.
SCHEMA_TIMESTAMP = "%Y-%m-%dT%H:%M:%S"


def junit_bytes(
    suite_name: str,
    outcome: SuiteOutcome,
    *,
    started_at: datetime | None = None,
    duration_s: float = 0.0,
    hostname: str | None = None,
) -> bytes:
    """The whole run as one `<testsuite>` document, ready to write."""
    started = started_at or datetime.now().astimezone()
    suite = ET.Element(
        "testsuite",
        name=suite_name,
        timestamp=started.strftime(SCHEMA_TIMESTAMP),
        hostname=hostname or _hostname(),
        tests=str(len(outcome.tests)),
        failures=str(sum(1 for t in outcome.tests if _is_failure(t))),
        errors=str(sum(1 for t in outcome.tests if _is_error(t))),
        skipped="0",
        time=f"{max(0.0, duration_s):.3f}",
    )

    _properties(suite, suite_name, started, outcome)
    for test in outcome.tests:
        _testcase(suite, suite_name, test)
    # Both required, and both last: a reader that wants the run's own words looks here, and a
    # job that failed for a reason that is not a test failure explains itself in system-err.
    ET.SubElement(suite, "system-out").text = _system_out(outcome)
    ET.SubElement(suite, "system-err").text = _system_err(outcome)

    ET.indent(suite)
    return ET.tostring(suite, encoding="utf-8", xml_declaration=True) + b"\n"


def _properties(
    suite: ET.Element, suite_name: str, started: datetime, outcome: SuiteOutcome
) -> None:
    """The element the schema requires, carrying what the attributes cannot."""
    properties = ET.SubElement(suite, "properties")
    for name, value in (
        # The stamp this project would normally use. `timestamp` above cannot carry the offset.
        ("startedAt", started.isoformat(timespec="seconds")),
        ("suite", suite_name),
        ("exitCode", str(outcome.code)),
        ("undelivered", str(len(outcome.undelivered))),
    ):
        if value:
            ET.SubElement(properties, "property", name=name, value=value)


def _testcase(suite: ET.Element, suite_name: str, test: TestOutcome) -> None:
    case = ET.SubElement(
        suite,
        "testcase",
        name=test.name,
        # A scenario id is the most useful classname a reader could get: it groups the run by
        # what the test is *for* (SC-14, SC-34) rather than by a Python module nobody has.
        classname=f"{suite_name}.{test.scenario or 'test'}",
        time=f"{_seconds(test):.3f}",
    )
    if _is_error(test):
        # Could not be played at all: no window, a target the suite never defined. Nothing was
        # learned about the application, which is exactly what `error` means here.
        ET.SubElement(
            case,
            "error",
            message=test.error or "the test could not be played",
            type="runError",
        ).text = _steps_text(test)
    elif _is_failure(test):
        step = test.failing_step or {}
        message = str(step.get("message") or "a step did not pass, and gave no message")
        ET.SubElement(
            case,
            "failure",
            message=message,
            type=str(step.get("category") or "stepFailed"),
        ).text = _steps_text(test)


def _is_error(test: TestOutcome) -> bool:
    return bool(test.error)


def _is_failure(test: TestOutcome) -> bool:
    return not test.passed and not test.error


def _seconds(test: TestOutcome) -> float:
    """A test's time, from its steps. The CLI does not clock a test as a whole."""
    total = sum(
        result.get("durationMs", 0)
        for result in test.results
        if isinstance(result.get("durationMs"), int)
    )
    return total / 1000


def _steps_text(test: TestOutcome) -> str:
    """One line per step, which is what a person reads first when a test goes red."""
    lines = []
    for result in test.results:
        line = f"step {result.get('stepIndex')}: {result.get('status')}"
        for key in ("category", "message"):
            if result.get(key):
                line += f" -- {result[key]}"
        lines.append(line)
    if test.error:
        lines.append(f"could not be played: {test.error}")
    return "\n".join(lines)


def _system_out(outcome: SuiteOutcome) -> str:
    passed = sum(1 for test in outcome.tests if test.passed)
    lines = [f"{passed} of {len(outcome.tests)} tests passed."]
    for test in outcome.tests:
        mark = "pass" if test.passed else "FAIL"
        lines.append(
            f"{mark}  {test.name}" + (f" ({test.scenario})" if test.scenario else "")
        )
    return "\n".join(lines)


def _system_err(outcome: SuiteOutcome) -> str:
    """Why the job failed when no test did.

    A run whose tests all passed but whose results never reached the server exits 2 (FR-23),
    and a report showing all green next to a red job is the confusing outcome. The test results
    stay honest; the reason goes where a reader looks for one.
    """
    lines: list[str] = []
    if outcome.error:
        lines.append(f"the run could not be completed: {outcome.error}")
    for test in outcome.undelivered:
        lines.append(
            f"{test.name}: results were not stored on the server: {test.delivery_error}"
        )
    if lines:
        lines.append(
            f"exit code {outcome.code}: a run whose results were not stored is not in the record."
        )
    return "\n".join(lines)


def _hostname() -> str:
    try:
        return socket.gethostname() or "unknown"
    except (
        OSError
    ):  # pragma: no cover - a host with no name is not a case worth failing on
        return "unknown"


def write_junit(
    path: Any,
    suite_name: str,
    outcome: SuiteOutcome,
    *,
    started_at: datetime | None = None,
    duration_s: float = 0.0,
) -> None:
    """Write the document, making the parent directory if CI named one that does not exist."""
    from pathlib import Path

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(
        junit_bytes(suite_name, outcome, started_at=started_at, duration_s=duration_s)
    )


def summary_of(document: bytes) -> Mapping[str, Any]:
    """`{tests, failures, errors, cases}` read back out of a document. For tests and for #67."""
    root = ET.fromstring(document)
    cases: Sequence[Mapping[str, Any]] = [
        {
            "name": case.get("name"),
            "classname": case.get("classname"),
            "outcome": next(
                (
                    child.tag
                    for child in case
                    if child.tag in ("failure", "error", "skipped")
                ),
                "passed",
            ),
        }
        for case in root.findall("testcase")
    ]
    return {
        "tests": int(root.get("tests", "0")),
        "failures": int(root.get("failures", "0")),
        "errors": int(root.get("errors", "0")),
        "cases": cases,
    }
