"""Playing a step document against one window: in order, with a deadline (#26).

What a run does, per step:

1. **Resolve** the target from the repository object's property sets, re-reading the window
   until it resolves to exactly one element or the step's time runs out. No fixed sleep
   (`agent/AGENTS.md`): the wait ends the moment the element is there, and a step that needs no
   waiting costs one read.
2. **Act** -- through UI Automation patterns only, never coordinates: Click and Type on the
   element itself (`playback.actions`), Select on one of its items (`playback.items`),
   SelectRow on one of its rows (`playback.rows`), Verify on a property of it
   (`playback.checkpoint`) or of a row of it, and Wait on nothing at all, because the wait in
   step 1 is the whole keyword.
3. **Record** one result, with how long the step took.

**A failed step stops the run** and every step after it is `notRun` (TBD-6, which I closed as
"the test stops after a failure"). Carrying on after a failed step would act on a screen the
test did not reach, and the results after it would describe an application state nobody asked
for.

**"Ready" is the pre-step wait, and it is more than "resolves"** (#40): a step waits until its
target resolves to exactly one element *and* that element is neither disabled nor off screen,
which is what the issue asks for ("exists, is visible and enabled") and what the schema calls
ready. A `Verify` is the exception -- a checkpoint may be *about* a disabled element -- so it
waits only for resolution and the checkpoint re-reads on its own.

A keyword outside `IMPLEMENTED` fails with a message naming what this agent does perform,
rather than being quietly skipped as passed.

Everything here is pure: the window is read through an injected callable and time through
injected `now`/`sleep`, so the ordering, the waiting and the stop-on-failure rules are tested
with fakes on any OS. Only `playback.actions.uia_patterns` and the real `read_tree` need
Windows.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any

from ayna_agent.playback import items, rows, triage
from ayna_agent.playback.actions import (
    ActionFailed,
    Patterns,
    click,
    type_text,
    uia_patterns,
)
from ayna_agent.playback.checkpoint import (
    CheckpointError,
    Unreadable,
    describe,
    holds,
)
from ayna_agent.playback.checkpoint import read as read_property
from ayna_agent.playback.checkpoint import validate as checkpoint_rules
from ayna_agent.playback.decisions import DecisionLog, decision_from
from ayna_agent.playback.items import SelectFailed
from ayna_agent.playback.resolve import (
    Ambiguous,
    NotFound,
    NotReady,
    Resolution,
    Unsupported,
    resolve,
)
from ayna_agent.playback.rows import RowError, RowFailed, RowsUnavailable
from ayna_agent.playback.screenshot import StepCapture
from ayna_agent.playback.tree import Tree
from ayna_agent.playback.tree import of as tree_of

#: Step-document versions this runner reads. A *consumer* lists what it understands instead of
#: deriving one version from the schema file, which it does not ship: v0.2 only *adds*
#: SelectRow, `row` and the three row checkpoints, so every 0.1 document means the same thing
#: in both and refusing one of them would break playback for no reason. A keyword this runner
#: does not implement is refused per step, by name, which is the honest place for that.
SUPPORTED_STEP_VERSIONS: tuple[str, ...] = ("0.1", "0.2")

#: Keywords this runner performs -- every keyword of step schema v0.2 (#40). One outside it
#: fails per step, by name, which is the honest place for "not implemented" to appear: a
#: document from a newer schema than this agent reads can always name one.
IMPLEMENTED: frozenset[str] = frozenset(
    {"Click", "Type", "Wait", "Verify", "Select", "SelectRow"}
)

#: Which keyword may carry which optional field, from the step schema's own words: `value` is
#: "text for Type and Select, not allowed for the other keywords", `row` is "the row SelectRow
#: selects" and `checkpoint` is "the check of a Verify step". A field on a keyword that forbids
#: it is refused rather than ignored: ignoring it would play a mis-built document as if it said
#: something else and report `passed`, which is the one outcome a tester cannot debug.
ALLOWED_FIELDS: dict[str, frozenset[str]] = {
    "value": frozenset({"Type", "Select"}),
    "row": frozenset({"SelectRow"}),
    "checkpoint": frozenset({"Verify"}),
}

#: A step without `timeoutMs` waits this long (RS NFR-05, team-confirmed in #143). Per run it
#: is configurable; `timeoutMs: 0` on a step means check once and never means "use this".
DEFAULT_TIMEOUT_MS = 10_000

#: How often the window is re-read while waiting for a target. The same 250 ms the step schema
#: v0.2 ADR records for row checks, so there is one number in the product rather than two.
POLL_INTERVAL_S = 0.25

#: `() -> (nodes, live elements)` for the window under test, as
#: `recognition.uia.UiaDesktop.read_tree` returns them.
ReadTree = Callable[[], tuple[Sequence[Mapping[str, Any]], Sequence[Any]]]

log = logging.getLogger(__name__)

PASSED = "passed"
FAILED = "failed"
NOT_RUN = "notRun"


class StepDocumentError(Exception):
    """The document is not a step document this runner can read."""


def not_ready(descriptor: Any) -> list[str]:
    """What stops `descriptor` from being acted on, in the words the message uses.

    `None` counts as **ready**: a provider that did not report `IsEnabled` or `IsOffscreen` is
    common, and refusing to act then would make playback depend on properties `NEVER_MATCH`
    already calls unreliable. Only an explicit `False`/`True` holds a step back.
    """
    missing = []
    if descriptor.enabled is False:
        missing.append("enabled")
    if descriptor.offscreen is True:
        missing.append("on screen")
    return missing


@dataclass(frozen=True, slots=True)
class StepResult:
    """One step's outcome, shaped like the `run.stepResult` params of `docs/agent-rpc.md`."""

    step_index: int
    status: str
    duration_ms: int
    step_id: str | None = None
    message: str | None = None
    #: Which property set resolved the target: `"primary"`, `"fallback"` or None when the step
    #: never got that far. A fallback match is what #73 heals and #63 logs, so it is recorded
    #: even on a step that passed.
    matched: str | None = None
    #: The pattern that performed the action (`"Invoke"`, `"SetValue"`, …), for the decision
    #: log (#63) and because "it clicked, through LegacyIAccessible" is a different fact from
    #: "it clicked".
    performed_with: str | None = None
    #: Absolute path to this step's PNG on the agent's machine, and when it was taken (#54).
    #: Absent when there is no image: a `notRun` step is never photographed, and a capture that
    #: failed does not fail the step (`playback.screenshot.step_capture`). So a reader -- #59's
    #: report, the client's step list -- treats "no screenshot" as normal.
    screenshot_path: str | None = None
    screenshot_at: str | None = None
    #: Which of FR-35's five a failed step belongs to (#63, ADR `2026-11-15-failure-category`).
    #: **Only with `status: failed`, and absent when the failure is not about the application**
    #: -- a keyword this agent has not implemented, a step document it refuses, a provider that
    #: refused an action. `playback.triage` is the one place that decides, and its docstring
    #: says why those stay out of the five rather than being squeezed into one.
    category: str | None = None

    def to_json(self) -> dict[str, Any]:
        """camelCase, absent values left out, so it can be sent as it is."""
        out: dict[str, Any] = {
            "stepIndex": self.step_index,
            "status": self.status,
            "durationMs": self.duration_ms,
        }
        if self.step_id is not None:
            out["stepId"] = self.step_id
        for key, value in (
            ("message", self.message),
            ("matched", self.matched),
            ("performedWith", self.performed_with),
            ("screenshotPath", self.screenshot_path),
            ("screenshotAt", self.screenshot_at),
            ("category", self.category),
        ):
            if value is not None:
                out[key] = value
        return out


def run_steps(
    document: Mapping[str, Any],
    targets: Mapping[str, Mapping[str, Any]],
    read_tree: ReadTree,
    *,
    default_timeout_ms: int = DEFAULT_TIMEOUT_MS,
    patterns: Patterns = uia_patterns,
    now: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    capture: StepCapture | None = None,
    decisions: DecisionLog | None = None,
    context: Mapping[str, Any] | None = None,
) -> list[StepResult]:
    """Play `document`'s steps and return one result per step, in order.

    `targets` maps a logical name to `{"properties": {...}, "fallback": {...}}` -- the
    repository object's primary and fallback sets (#25). Extra members (`serverElementId`,
    `featureVersion`, which healing needs) are ignored here.

    `capture` is #54's screenshot, built by `playback.screenshot.step_capture` and bound to the
    window under test; it is called after each step that ran, never for a `notRun` one. Injected
    rather than taken as a window handle so this module stays testable with no desktop, and
    because the handle belongs to the caller that opened the window, not to the runner.

    `decisions` is #63's log: one JSONL line per **failed** step, with the finer `reason` the
    contract's `category` cannot carry and the property sets that were tried, so the failure
    can be labelled later (RQ5, #64, #86). `context` adds what this module cannot know --
    `run_id`, `test_name`, `window_title`, `app_version`. Writing the log never affects the
    run: a log that cannot be written is logged and the steps carry on, because losing a run
    to a full disk in the measurement harness would be the wrong trade.

    Raises `StepDocumentError` only for a document that cannot be read at all; everything a
    single step can get wrong becomes that step's `failed` result, because a run that returns
    results is far more useful than one that raises.
    """
    steps = _steps_of(document)
    results: list[StepResult] = []
    for index, step in enumerate(steps):
        if results and results[-1].status != PASSED:
            results.append(
                StepResult(
                    step_index=index,
                    status=NOT_RUN,
                    duration_ms=0,
                    step_id=_step_id(step),
                    message="not run: an earlier step failed",
                )
            )
            continue
        triaged: dict[str, str] = {}
        result = _run_one(
            index,
            step,
            targets,
            read_tree,
            default_timeout_ms=default_timeout_ms,
            patterns=patterns,
            now=now,
            sleep=sleep,
            triaged=triaged,
        )
        # After the step, not before: FR-19's image is the evidence of what the step did, and
        # for a failed step it is the evidence of what the screen looked like when it failed.
        if capture is not None:
            image = capture(index)
            if image is not None:
                result = replace(
                    result,
                    screenshot_path=image.path,
                    screenshot_at=image.taken_at,
                )
        results.append(result)
        if decisions is not None and result.status == FAILED:
            _record(decisions, result, step, targets, triaged, context)
    return results


def _record(
    decisions: DecisionLog,
    result: StepResult,
    step: Mapping[str, Any],
    targets: Mapping[str, Mapping[str, Any]],
    triaged: Mapping[str, str],
    context: Mapping[str, Any] | None,
) -> None:
    """Append one failed step to the decision log, and never let that fail the run."""
    target = targets.get(step.get("target", "")) if isinstance(step, Mapping) else None
    tried = [
        dict(properties)
        for properties in (
            (target or {}).get("properties"),
            (target or {}).get("fallback"),
        )
        if isinstance(properties, Mapping)
    ]
    try:
        decisions.append(
            decision_from(
                result,
                step,
                reason=triaged.get("reason", triage.REFUSED_STEP),
                tried=tried,
                **dict(context or {}),
            )
        )
    except Exception:
        log.warning("could not log step %d's failure", result.step_index, exc_info=True)


def _steps_of(document: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    if not isinstance(document, Mapping):
        raise StepDocumentError(
            f"a step document is an object, not {type(document).__name__}"
        )
    version = document.get("version")
    if version not in SUPPORTED_STEP_VERSIONS:
        supported = " or ".join(SUPPORTED_STEP_VERSIONS)
        raise StepDocumentError(
            f"step document version {version!r}; this agent reads {supported}"
        )
    steps = document.get("steps")
    if not isinstance(steps, Sequence) or isinstance(steps, str | bytes):
        raise StepDocumentError("the document's 'steps' is not a list")
    for position, step in enumerate(steps):
        if not isinstance(step, Mapping):
            raise StepDocumentError(f"step {position} is not an object")
    return list(steps)


def _step_id(step: Mapping[str, Any]) -> str | None:
    value = step.get("id")
    return str(value) if isinstance(value, str) and value else None


def _run_one(
    index: int,
    step: Mapping[str, Any],
    targets: Mapping[str, Mapping[str, Any]],
    read_tree: ReadTree,
    *,
    default_timeout_ms: int,
    patterns: Patterns,
    now: Callable[[], float],
    sleep: Callable[[float], None],
    triaged: dict[str, str] | None = None,
) -> StepResult:
    started = now()
    step_id = _step_id(step)
    # Where `done` leaves what `triage.reason_for` made of a failure, for the decision log
    # (#63). A dict the caller owns rather than a second return value: `done` is called from
    # two dozen places and every one of them would otherwise have to pass it back by hand.
    # The reason is finer than the contract's `category` and belongs to the measurement, not
    # to the message the client reads, which is why it does not live on `StepResult`.
    triaged = {} if triaged is None else triaged

    def done(
        status: str,
        message: str | None = None,
        *,
        error: BaseException | None = None,
        reason: str | None = None,
        **extra: Any,
    ) -> StepResult:
        """One result. Give it the `error` and it triages itself (#63).

        Passing the exception rather than a category at each site keeps the rule in
        `playback.triage` and out of twenty `except` branches; the two failures with no
        exception to pass (a step the agent refuses, a checkpoint that simply did not hold)
        name their `reason` instead.
        """
        if error is not None:
            extra.setdefault("category", triage.category_for(error))
            triaged["reason"] = triage.reason_for(error)
        elif status == FAILED:
            triaged["reason"] = reason or triage.REFUSED_STEP
        return StepResult(
            step_index=index,
            status=status,
            duration_ms=max(0, round((now() - started) * 1000)),
            step_id=step_id,
            message=message,
            **extra,
        )

    keyword = step.get("keyword")
    if keyword not in IMPLEMENTED:
        known = ", ".join(sorted(IMPLEMENTED))
        return done(
            FAILED,
            f"keyword {keyword!r} is not implemented yet; this agent performs {known}",
        )

    name = step.get("target")
    if not isinstance(name, str) or not name:
        return done(FAILED, "the step names no target")
    target = targets.get(name)
    if target is None:
        return done(
            FAILED,
            f"the run request carries no properties for {name}; the object may have been "
            f"renamed or removed from the repository",
        )
    for field, keywords in ALLOWED_FIELDS.items():
        if field in step and keyword not in keywords:
            allowed = " and ".join(sorted(keywords))
            return done(
                FAILED,
                f"a {keyword} step carries {field!r}, which only {allowed} takes",
            )

    value = step.get("value")
    if keyword == "Type" and not isinstance(value, str):
        return done(FAILED, "a Type step needs a text value")
    if keyword == "Select" and not (isinstance(value, str) and value):
        # The schema requires `minLength: 1` here: "choose the item whose text is" nothing is
        # not a choice, and an empty value would match an item with no text.
        return done(FAILED, "a Select step needs the text of the item to choose")

    timeout_ms = step.get("timeoutMs")
    if timeout_ms is None:
        timeout_ms = default_timeout_ms
    if (
        not isinstance(timeout_ms, int)
        or isinstance(timeout_ms, bool)
        or timeout_ms < 0
    ):
        return done(
            FAILED,
            f"timeoutMs must be a whole number of milliseconds, not {timeout_ms!r}",
        )

    #: The checkpoint and the row, read before the wait: a step whose own shape is wrong is a
    #: client bug, and spending the timeout on it before saying so helps nobody.
    check: tuple[str, str, Any] | None = None
    want_row: rows.Address | None = None
    checkpoint = step.get("checkpoint")
    try:
        if keyword == "Verify":
            check = checkpoint_rules(checkpoint)
            if check[0] in rows.ROW_PROPERTIES and check[0] != "rowCount":
                want_row = rows.address((checkpoint or {}).get("row"))
        elif keyword == "SelectRow":
            want_row = rows.address(step.get("row"))
    except (CheckpointError, RowError) as exc:
        return done(FAILED, f"{name}: {exc}", error=exc)

    try:
        found, tree = _resolve_waiting(
            read_tree,
            name,
            target,
            timeout_ms=timeout_ms,
            now=now,
            sleep=sleep,
            # A checkpoint may be *about* a disabled or offscreen element, so a Verify waits
            # only for resolution and the checkpoint does its own re-reading.
            require_ready=keyword != "Verify",
        )
    except Unsupported as exc:
        return done(FAILED, f"{name}: {exc}", error=exc)
    except Ambiguous as exc:
        # FR-35 "element not found": no *unique* element matched. Deliberately not a sixth
        # category and deliberately not a guess -- see `playback.resolve`.
        return done(FAILED, str(exc), error=exc)
    except NotFound as exc:
        return done(FAILED, f"{exc} within {timeout_ms} ms", error=exc)
    except NotReady as exc:
        # `after N ms`, not `within`: this one waited for a *state* to change rather than for
        # an element to appear. The wording is the one promised in the PR #231 review.
        return done(FAILED, f"{exc} after {timeout_ms} ms", error=exc)

    if keyword == "Wait":
        # "only wait until the target is ready; never a fixed sleep" (the schema). The wait
        # already happened above, so there is nothing left to do and nothing performed it.
        return done(PASSED, matched=found.which)

    if keyword == "Verify":
        try:
            message = _verify_waiting(
                read_tree,
                name,
                target,
                checkpoint,
                check,
                want_row,
                found,
                tree,
                timeout_ms=timeout_ms,
                patterns=patterns,
                now=now,
                sleep=sleep,
            )
        except (CheckpointError, RowError, RowsUnavailable) as exc:
            return done(
                FAILED,
                f"{name}: {exc}",
                matched=found.which,
                error=exc,
            )
        except Unreadable as exc:
            return done(
                FAILED,
                f"{name}: {exc}",
                matched=found.which,
                error=exc,
            )
        if message is None:
            return done(PASSED, matched=found.which)
        # The one failure with no exception to read: the checkpoint was well formed, the
        # property was read, and it did not hold. That is `assertionFailed` by definition.
        return done(
            FAILED,
            message,
            matched=found.which,
            category=triage.ASSERTION_FAILED,
            reason=triage.ASSERTION_FAILED,
        )

    if keyword == "SelectRow":
        try:
            performed_with, note = _select_row_waiting(
                read_tree,
                name,
                target,
                want_row,
                found,
                tree,
                timeout_ms=timeout_ms,
                patterns=patterns,
                now=now,
                sleep=sleep,
            )
        except (RowError, RowsUnavailable) as exc:
            return done(
                FAILED,
                f"{name}: {exc}",
                matched=found.which,
                error=exc,
            )
        except RowFailed as exc:
            return done(FAILED, str(exc), matched=found.which, error=exc)
        # `note` is a message on a *passing* step: the ADR asks playback to report what it
        # selected when the view selects cells rather than rows, and that is not a failure.
        return done(PASSED, note, matched=found.which, performed_with=performed_with)

    if keyword == "Select":
        try:
            performed_with = _select_waiting(
                read_tree,
                name,
                target,
                str(value),
                found,
                tree,
                timeout_ms=timeout_ms,
                patterns=patterns,
                now=now,
                sleep=sleep,
            )
        except SelectFailed as exc:
            return done(FAILED, str(exc), matched=found.which, error=exc)
        return done(PASSED, matched=found.which, performed_with=performed_with)

    try:
        if keyword == "Click":
            performed_with = click(found.element, patterns)
        else:
            performed_with = type_text(found.element, str(value), patterns)
    except ActionFailed as exc:
        return done(FAILED, str(exc), matched=found.which, error=exc)

    return done(PASSED, matched=found.which, performed_with=performed_with)


def _verify_waiting(
    read_tree: ReadTree,
    name: str,
    target: Mapping[str, Any],
    checkpoint: Any,
    check: tuple[str, str, Any] | None,
    want_row: rows.Address | None,
    found: Resolution,
    tree: Tree,
    *,
    timeout_ms: int,
    patterns: Patterns,
    now: Callable[[], float],
    sleep: Callable[[float], None],
) -> str | None:
    """None when the checkpoint holds, else the failure message.

    The checkpoint re-reads on the **same** deadline as the resolution that preceded it: the
    schema says `timeoutMs` is the longest wait for the target "and for SelectRow and row
    checks, its row or check" to become ready, so a property that is about to change is not a
    race. `timeoutMs: 0` checks once.

    The target is resolved again on every poll rather than kept: a re-read gives new live
    elements, and holding the old one would check a stale handle -- the same reason #22's
    `elementFromPoint` compares identity instead of trusting a remembered element.
    """
    prop, operator, expected = check if check else checkpoint_rules(checkpoint)
    if prop in rows.ROW_PROPERTIES:
        return _verify_rows_waiting(
            read_tree,
            name,
            target,
            (checkpoint or {}).get("column"),
            (prop, operator, expected),
            want_row,
            found,
            tree,
            timeout_ms=timeout_ms,
            patterns=patterns,
            now=now,
            sleep=sleep,
        )
    deadline = now() + timeout_ms / 1000
    while True:
        actual = read_property(prop, found.descriptor, found.element, patterns)
        if holds(operator, actual, expected):
            return None
        remaining = deadline - now()
        if timeout_ms == 0 or remaining <= 0:
            # `after N ms`, not `within`: this waited for a value to change, not for an
            # element to appear. One wording per kind of wait (the PR #231 review).
            suffix = f" after {timeout_ms} ms" if timeout_ms else ""
            return describe(name, prop, operator, expected, actual) + suffix
        sleep(min(POLL_INTERVAL_S, remaining))
        try:
            found, _tree = _read_and_resolve(read_tree, name, target)
        except (NotFound, Ambiguous, Unsupported) as exc:
            # It was there a moment ago and now it is not: that is the honest report, and it
            # is a different fact from "the property never took the expected value".
            return f"{exc} while checking {prop}"


def _verify_rows_waiting(
    read_tree: ReadTree,
    name: str,
    target: Mapping[str, Any],
    column: Any,
    check: tuple[str, str, Any],
    want: rows.Address | None,
    found: Resolution,
    tree: Tree,
    *,
    timeout_ms: int,
    patterns: Patterns,
    now: Callable[[], float],
    sleep: Callable[[float], None],
) -> str | None:
    """`cell`, `rowExists` and `rowCount`: None when the check holds, else the message.

    Re-reads the target on the same interval as every other wait, because **rows fill after
    the grid itself is ready** (SC-18) -- the target's smart wait cannot see that, which is the
    whole reason the ADR gives these three checks their own wait.

    The ` after N ms` suffix is appended at the end, exactly as it is for the element
    properties: the wording of these messages is what omer's run report (#59) is written
    against, and one rule for the suffix is worth more than a better-reading sentence.
    """
    prop, operator, expected = check
    deadline = now() + timeout_ms / 1000
    while True:
        grid = rows.of(tree, found.index, patterns)
        if want is None:
            # `rowCount`, the one row check with no row: the pattern's count, or the rows the
            # tree holds (`rows._count`), against the expected number.
            failure = (
                None
                if holds(operator, grid.count, expected)
                else describe(name, prop, operator, expected, grid.count)
            )
        else:
            failure = _row_check(
                name, prop, operator, expected, want, column, grid, tree, patterns
            )
        if failure is None:
            return None
        remaining = deadline - now()
        if timeout_ms == 0 or remaining <= 0:
            return failure + (f" after {timeout_ms} ms" if timeout_ms else "")
        sleep(min(POLL_INTERVAL_S, remaining))
        try:
            found, tree = _read_and_resolve(read_tree, name, target)
        except (NotFound, Ambiguous, Unsupported) as exc:
            # It was there a moment ago and now it is not: a different fact from "the check
            # never held", and a tester debugs the two differently.
            return f"{exc} while checking {prop}"


def _row_check(
    name: str,
    prop: str,
    operator: str,
    expected: Any,
    want: rows.Address,
    column: Any,
    grid: rows.Grid,
    tree: Tree,
    patterns: Patterns,
) -> str | None:
    """One pass of `cell` or `rowExists`: None when it holds, else the message, no time in it."""
    row = rows.find(tree, grid, want, patterns)
    if prop == "rowExists":
        if holds(operator, row is not None, expected):
            return None
        return rows.describe_exists(name, want, bool(expected), grid, row)

    cell = (
        rows.cell_of(row, rows.column_index(grid, column)) if row is not None else None
    )
    if cell is None:
        # No such row, or the row has no cell in that column: the check has no answer at all,
        # and "expected Yılmaz, got nothing" would blame the data instead of the address.
        return rows.unreadable_cell(name, want, column, grid)
    actual = rows.text_at(tree, cell, patterns)
    if holds(operator, actual, expected):
        return None
    return rows.describe_cell(name, want, column, operator, expected, actual)


def _select_row_waiting(
    read_tree: ReadTree,
    name: str,
    target: Mapping[str, Any],
    want: rows.Address | None,
    found: Resolution,
    tree: Tree,
    *,
    timeout_ms: int,
    patterns: Patterns,
    now: Callable[[], float],
    sleep: Callable[[float], None],
) -> tuple[str, str | None]:
    """Select the row `want` addresses: `(the pattern that did it, a note or None)`.

    The note is for the one case the ADR leaves open: on a view that selects cells rather than
    rows, selecting the row's first cell selects *that cell*, and playback "reports what it
    selected instead of claiming the row". A failure would be wrong -- the step did select
    something, and a pilot app's selection behaviour is not ours to change.

    Waits for the row within the step's `timeoutMs`, because a grid is ready before its rows
    are (SC-18).
    """
    if want is None:  # pragma: no cover - `_run_one` validates the row before the wait
        raise RowError("the step names no row")
    deadline = now() + timeout_ms / 1000
    while True:
        grid = rows.of(tree, found.index, patterns)
        row = rows.find(tree, grid, want, patterns)
        if row is not None:
            performed = rows.select(row, tree, patterns)
            if performed is None:
                raise RowFailed(rows.refused(name, want), rows.ROW_REFUSED)
            notes = []
            if rows.whole_row_selected(row, tree, patterns) is False:
                notes.append(rows.selected_a_cell(name, want))
            if not rows.make_current(row, found.index, tree, patterns):
                notes.append(rows.not_current(name, want))
            return performed, "; ".join(notes) or None
        remaining = deadline - now()
        if timeout_ms == 0 or remaining <= 0:
            raise RowFailed(
                rows.not_found(name, want, grid, timeout_ms), rows.ROW_NOT_FOUND
            )
        sleep(min(POLL_INTERVAL_S, remaining))
        try:
            found, tree = _read_and_resolve(read_tree, name, target)
        except (NotFound, Ambiguous, Unsupported) as exc:
            raise RowFailed(
                f"{exc} while selecting {want.describe()}", rows.ROW_NOT_FOUND
            ) from exc


def _select_waiting(
    read_tree: ReadTree,
    name: str,
    target: Mapping[str, Any],
    value: str,
    found: Resolution,
    tree: Tree,
    *,
    timeout_ms: int,
    patterns: Patterns,
    now: Callable[[], float],
    sleep: Callable[[float], None],
) -> str:
    """Choose the item whose text is `value`, and return the pattern that did it.

    The loop is here rather than in `playback.items` because it is the same loop every wait in
    this module runs: re-read the window, resolve the target again, look again. What is new is
    that the *items* are what it waits for -- a combo box fills its list when it opens, so
    expanding and then re-reading is the only way to see them (#33).

    The item wait gets the step's `timeoutMs` of its own, as a checkpoint's re-reading does:
    the schema names the target becoming ready and "its row or check" as two waits sharing one
    limit, not one clock split between them.

    Raises :class:`SelectFailed` with the message already worded, including the case where the
    target itself goes away mid-wait.
    """
    deadline = now() + timeout_ms / 1000
    opened = False
    # The *most* items the target was ever seen to hold, not the last count. A Qt popup
    # closes itself about a second after it is opened programmatically (measured in the #40
    # Windows check), so the count at the deadline is 0 while the list plainly had five --
    # and "the target shows no items at all" would tell the tester the opposite of the truth.
    most = 0

    def finish(performed: str) -> str:
        """Leave the screen as the test found it, then report what performed the choice.

        Only on success: a *failed* Select leaves an opened list open on purpose, because the
        run stops there and the open list with its items in it is the evidence a tester needs
        in the screenshot (#54). A refusal to close is not a failure -- the item is chosen.
        """
        if opened:
            items.collapse(found.element, patterns)
        return performed

    while True:
        position, count = items.find(tree, found.index, value, patterns)
        most = max(most, count)
        if position is not None:
            item = tree.infos[position]
            performed = items.choose(
                item,
                patterns,
                # Read back after every rung, so a provider that accepts the call and does
                # nothing falls through instead of reporting a choice it did not make.
                confirm=lambda item=item, box=found.element: _confirmed(
                    box,
                    item,
                    value,
                    patterns=patterns,
                    now=now,
                    sleep=sleep,
                    deadline=deadline,
                ),
            )
            if performed is not None:
                return finish(performed)
            # The item is there and the provider would not select it: the Qt case (#33). An
            # editable box may still take the text, and that is a different, honest outcome --
            # recorded as `SetValue` rather than as a choice.
            if items.write(found.element, value, patterns):
                return finish("SetValue")
            raise SelectFailed(
                items.refused(name, value, items.CHOOSE_PATTERNS), items.ITEM_REFUSED
            )

        if not count and items.can_expand(found.element, patterns):
            # The items of a closed combo box do not exist yet, so this is not "look harder":
            # it is the only way they can appear. The re-read below is what sees them.
            #
            # Every poll the box shows nothing, **not once**: Qt's popup closes itself about a
            # second after it was opened programmatically (#40 Windows check), so a list that
            # fills late -- the late control SC-18 is built around -- would appear in a box
            # playback had already given up reopening, and the item could never be found. The
            # guard is "shows no items", so this stops by itself as soon as they are there.
            opened = items.expand(found.element, patterns) or opened
        elif not count and not items.selectable(found.element, patterns):
            # Not a list or a combo box at all. Fail now rather than at the deadline: waiting
            # cannot turn a button into a list, and ten seconds of silence would suggest it
            # might.
            raise SelectFailed(items.not_a_list(name), items.ITEM_REFUSED)

        remaining = deadline - now()
        if timeout_ms == 0 or remaining <= 0:
            if items.write(found.element, value, patterns):
                # An editable combo box whose list playback cannot see (a Qt popup is a window
                # of its own) still has a usable text value. Last, and only after the full
                # wait, so it cannot hide a genuine "there is no such item".
                return finish("SetValue")
            raise SelectFailed(
                items.no_such_item(name, value, most, timeout_ms), items.ITEM_NOT_FOUND
            )
        sleep(min(POLL_INTERVAL_S, remaining))
        try:
            found, tree = _read_and_resolve(read_tree, name, target)
        except (NotFound, Ambiguous, Unsupported) as exc:
            raise SelectFailed(
                items.vanished(exc, value), items.ITEM_NOT_FOUND
            ) from exc


def _confirmed(
    target: Any,
    item: Any,
    value: str,
    *,
    patterns: Patterns,
    now: Callable[[], float],
    sleep: Callable[[float], None],
    deadline: float,
) -> bool:
    """Whether the rung just tried really changed the control, allowing for a slow provider.

    Qt applies a chosen item **asynchronously**: the sample app's combo box still reads its old
    value 11 ms after `LegacyIAccessible.DoDefaultAction()` and the new one at 32 ms (measured
    in the #40 Windows check). A single read straight after the call therefore judges the rung
    a no-op, falls through, and whichever rung comes next takes the credit for what this one
    did -- which is how `Select` first reported `SetValue` for a choice `LegacyIAccessible` had
    already made.

    So the confirmation is a short wait rather than a read: **one** `POLL_INTERVAL_S`, the same
    cadence as every other wait here, bounded by the step's own deadline so it can never
    outlive the timeout the tester set. One interval and no more -- a rung that genuinely did
    nothing has to reach the next rung inside that same timeout.
    """
    if items.took_effect(target, item, value, patterns):
        return True
    remaining = deadline - now()
    if remaining <= 0:
        return False
    sleep(min(POLL_INTERVAL_S, remaining))
    return items.took_effect(target, item, value, patterns)


def _resolve_waiting(
    read_tree: ReadTree,
    name: str,
    target: Mapping[str, Any],
    *,
    timeout_ms: int,
    now: Callable[[], float],
    sleep: Callable[[float], None],
    require_ready: bool = True,
) -> tuple[Resolution, Tree]:
    """Re-read the window until `name` is ready to act on, or the time runs out.

    Ready means: resolves to exactly one element, and that element is not disabled and not off
    screen (:func:`not_ready`). `require_ready=False` waits only for resolution, which is what
    a `Verify` needs -- a checkpoint on `enabled: false` would otherwise be unplayable.

    Returns the resolution **and the tree it was read from**: `Select` and the row keywords
    address a descendant of the target, so the shape of the window has to survive the wait
    that found it (`playback.tree`).

    `timeoutMs: 0` checks once (RS NFR-05). The last failure is the one raised, so the message
    describes the state the window actually ended in rather than the first thing that went
    wrong.
    """
    deadline = now() + timeout_ms / 1000
    while True:
        try:
            found, tree = _read_and_resolve(read_tree, name, target)
        except Unsupported:
            # A property set playback cannot match on is a client bug: waiting cannot fix it.
            raise
        except (NotFound, Ambiguous) as exc:
            last: Exception = exc
        else:
            missing = not_ready(found.descriptor) if require_ready else []
            if not missing:
                return found, tree
            last = NotReady(name, missing)
        remaining = deadline - now()
        if timeout_ms == 0 or remaining <= 0:
            raise last
        sleep(min(POLL_INTERVAL_S, remaining))


def _read_and_resolve(
    read_tree: ReadTree,
    name: str,
    target: Mapping[str, Any],
) -> tuple[Resolution, Tree]:
    """Read the window once and resolve `name` in it.

    One place, so every wait in this module resolves against the same derivation
    (`model.describe_tree`, as a snapshot does) and keeps the tree of the *same* read -- a
    descendant taken from an older read would be a stale handle.
    """
    nodes, infos = read_tree()
    tree = tree_of(nodes, infos)
    found = resolve(
        tree.descriptors,
        tree.infos,
        name,
        target.get("properties") or {},
        target.get("fallback") or None,
    )
    return found, tree
