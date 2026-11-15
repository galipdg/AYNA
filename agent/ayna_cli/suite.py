"""A suite: a list of tests, each a step document with the targets its steps name (#61).

Two sources, one shape in memory. `--from-file` reads the shape
`.github/suite/smoke.json` already uses (#67's stand-in, which this command replaces), and
`--server` builds the same thing from the run the server created and the application's
repository objects. Everything downstream — playback, the results, the exit code — sees only
:class:`SuiteTest` and never learns which source it came from.

A file suite carries its own `targets`, because without a server there is no repository to
resolve a logical name against. A server suite does not: its targets come from
`GET /api/apps/{appId}/repo-objects`, which is the point of having a repository.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class SuiteError(Exception):
    """The suite cannot be read or does not hold what a run needs: exit code 2."""


@dataclass(frozen=True)
class SuiteTest:
    """One test of a suite, ready to play."""

    name: str
    #: The step document, `{version, steps}` as `schemas/step.schema.json` defines it.
    document: Mapping[str, Any]
    #: Logical name -> `{"properties": ..., "fallback": ...}`, what `run_steps` expects.
    targets: Mapping[str, Mapping[str, Any]]
    #: The reference scenario this test stands for (SC-14, …), when it names one. Carried for
    #: the report (#66) and for the eval work, never used to decide anything here.
    scenario: str | None = None
    #: The server's id for the test, when the suite came from a server. `None` for a file, and
    #: that is what makes a file run unable to post results.
    test_id: str | None = None
    #: Which window to play against, by UIA Name. With a server this comes from the targets'
    #: `windowTitle`, which is #40's rule.
    window_title: str | None = None
    #: Or by UIA ClassName, which is what `.github/suite/smoke.json` names (#67's stand-in for
    #: this command). Kept because a Qt or WinForms class name is often the stabler of the two:
    #: a title carries the document name, the dirty marker and the language.
    window_class: str | None = None

    def __post_init__(self) -> None:
        if self.window_title and self.window_class:
            raise SuiteError(
                f"{self.name}: a window is named by 'title' or by 'className', not both"
            )


@dataclass(frozen=True)
class Suite:
    """What a run plays, in order."""

    name: str
    tests: list[SuiteTest] = field(default_factory=list)


def read_suite_file(path: Path | str) -> Suite:
    """Read `--from-file`'s suite.

    Every check here raises rather than skipping the test. A suite file with a typo in it is an
    operational failure (exit 2), not a test failure (exit 1): the difference between "the
    application is broken" and "the job is misconfigured" is the whole value of the two codes,
    and silently running four tests of five would blur it.
    """
    path = Path(path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SuiteError(f"{path}: {exc}") from exc
    except ValueError as exc:
        raise SuiteError(f"{path}: not JSON: {exc}") from exc
    if not isinstance(raw, dict):
        raise SuiteError(f"{path}: a suite is an object, not {type(raw).__name__}")

    tests = raw.get("tests")
    if not isinstance(tests, list) or not tests:
        raise SuiteError(f"{path}: a suite needs a non-empty 'tests' list")

    read: list[SuiteTest] = []
    seen: set[str] = set()
    for index, test in enumerate(tests):
        read.append(_read_test(path, index, test, seen))
    return Suite(name=str(raw.get("suite") or path.stem), tests=read)


def _read_test(path: Path, index: int, test: object, seen: set[str]) -> SuiteTest:
    where = f"{path}: test {index}"
    if not isinstance(test, dict):
        raise SuiteError(f"{where} is not an object")

    name = test.get("name")
    if not isinstance(name, str) or not name.strip():
        raise SuiteError(f"{where} has no 'name'")
    if name in seen:
        # Names are how a result is reported and how `--expect-failed` picks a test, so two
        # tests of one name would make both ambiguous.
        raise SuiteError(f"{path}: two tests are named {name!r}")
    seen.add(name)

    document = test.get("steps")
    if not isinstance(document, dict):
        raise SuiteError(f"{where} ({name}) has no 'steps' document")
    steps = document.get("steps")
    if not isinstance(steps, list):
        raise SuiteError(f"{where} ({name}): 'steps.steps' is not a list")

    targets = test.get("targets", {})
    if not isinstance(targets, dict) or not all(
        isinstance(value, dict) for value in targets.values()
    ):
        raise SuiteError(
            f"{where} ({name}): 'targets' maps a logical name to its property sets"
        )
    missing = sorted(_named_targets(steps) - set(targets))
    if missing:
        # Caught here rather than per step, because a file suite has no repository to fall back
        # on: every one of those steps would fail with the same message at run time, and the
        # suite is simply wrong.
        raise SuiteError(
            f"{where} ({name}): no target for {', '.join(repr(m) for m in missing)}"
        )

    window = test.get("window") if isinstance(test.get("window"), dict) else {}
    title = window.get("title")
    class_name = window.get("className")
    if title is not None and class_name is not None:
        raise SuiteError(
            f"{where} ({name}): a window is named by 'title' or by 'className', not both"
        )

    scenario = test.get("scenario")
    return SuiteTest(
        name=name,
        document=document,
        targets=targets,
        scenario=scenario if isinstance(scenario, str) else None,
        window_title=title if isinstance(title, str) else None,
        window_class=class_name if isinstance(class_name, str) else None,
    )


def _named_targets(steps: list[Any]) -> set[str]:
    return {
        step["target"]
        for step in steps
        if isinstance(step, dict) and isinstance(step.get("target"), str)
    }
