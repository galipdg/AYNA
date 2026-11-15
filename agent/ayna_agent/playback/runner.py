"""Playing a step document against one window: in order, with a deadline (#26).

What a run does, per step:

1. **Resolve** the target from the repository object's property sets, re-reading the window
   until it resolves to exactly one element or the step's time runs out. No fixed sleep
   (`agent/AGENTS.md`): the wait ends the moment the element is there, and a step that needs no
   waiting costs one read.
2. **Act** -- Click or Type, through UI Automation patterns only (`playback.actions`).
3. **Record** one result, with how long the step took.

**A failed step stops the run** and every step after it is `notRun` (TBD-6, which I closed as
"the test stops after a failure"). Carrying on after a failed step would act on a screen the
test did not reach, and the results after it would describe an application state nobody asked
for.

`#26 implements Click and Type` -- the issue says so, and `Select`, `Verify`, `Wait` and
`SelectRow` fail with a message naming #40, rather than being quietly skipped as passed.

Everything here is pure: the window is read through an injected callable and time through
injected `now`/`sleep`, so the ordering, the waiting and the stop-on-failure rules are tested
with fakes on any OS. Only `playback.actions.uia_patterns` and the real `read_tree` need
Windows.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any

from ayna_agent.model import describe_tree
from ayna_agent.playback.actions import (
    ActionFailed,
    Patterns,
    click,
    type_text,
    uia_patterns,
)
from ayna_agent.playback.resolve import (
    Ambiguous,
    NotFound,
    Resolution,
    Unsupported,
    resolve,
)
from ayna_agent.playback.screenshot import StepCapture

#: Step-document versions this runner reads. A *consumer* lists what it understands instead of
#: deriving one version from the schema file, which it does not ship: Click and Type are
#: identical in 0.1 and 0.2, so refusing 0.2 would break playback the day the v0.2 schema
#: merges (#147) for no reason. A keyword this runner does not implement is refused per step,
#: by name, which is the honest place for that to happen.
SUPPORTED_STEP_VERSIONS: tuple[str, ...] = ("0.1", "0.2")

#: Keywords #26 performs. The rest are #40's.
IMPLEMENTED: frozenset[str] = frozenset({"Click", "Type"})

#: A step without `timeoutMs` waits this long (RS NFR-05, team-confirmed in #143). Per run it
#: is configurable; `timeoutMs: 0` on a step means check once and never means "use this".
DEFAULT_TIMEOUT_MS = 10_000

#: How often the window is re-read while waiting for a target. The same 250 ms the step schema
#: v0.2 ADR records for row checks, so there is one number in the product rather than two.
POLL_INTERVAL_S = 0.25

#: `() -> (nodes, live elements)` for the window under test, as
#: `recognition.uia.UiaDesktop.read_tree` returns them.
ReadTree = Callable[[], tuple[Sequence[Mapping[str, Any]], Sequence[Any]]]

PASSED = "passed"
FAILED = "failed"
NOT_RUN = "notRun"


class StepDocumentError(Exception):
    """The document is not a step document this runner can read."""


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
) -> list[StepResult]:
    """Play `document`'s steps and return one result per step, in order.

    `targets` maps a logical name to `{"properties": {...}, "fallback": {...}}` -- the
    repository object's primary and fallback sets (#25). Extra members (`serverElementId`,
    `featureVersion`, which healing needs) are ignored here.

    `capture` is #54's screenshot, built by `playback.screenshot.step_capture` and bound to the
    window under test; it is called after each step that ran, never for a `notRun` one. Injected
    rather than taken as a window handle so this module stays testable with no desktop, and
    because the handle belongs to the caller that opened the window, not to the runner.

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
        result = _run_one(
            index,
            step,
            targets,
            read_tree,
            default_timeout_ms=default_timeout_ms,
            patterns=patterns,
            now=now,
            sleep=sleep,
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
    return results


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
) -> StepResult:
    started = now()
    step_id = _step_id(step)

    def done(status: str, message: str | None = None, **extra: Any) -> StepResult:
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
        known = " and ".join(sorted(IMPLEMENTED))
        return done(
            FAILED,
            f"keyword {keyword!r} is not implemented yet: #26 performs {known}, "
            f"the rest comes with #40",
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
    value = step.get("value")
    if keyword == "Type" and not isinstance(value, str):
        return done(FAILED, "a Type step needs a text value")

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

    try:
        found = _resolve_waiting(
            read_tree,
            name,
            target,
            timeout_ms=timeout_ms,
            now=now,
            sleep=sleep,
        )
    except Unsupported as exc:
        return done(FAILED, f"{name}: {exc}")
    except Ambiguous as exc:
        # FR-35 "element not found": no *unique* element matched. Deliberately not a sixth
        # category and deliberately not a guess -- see `playback.resolve`.
        return done(FAILED, str(exc))
    except NotFound as exc:
        return done(FAILED, f"{exc} within {timeout_ms} ms")

    try:
        if keyword == "Click":
            performed_with = click(found.element, patterns)
        else:
            performed_with = type_text(found.element, str(value), patterns)
    except ActionFailed as exc:
        return done(FAILED, str(exc), matched=found.which)

    return done(PASSED, matched=found.which, performed_with=performed_with)


def _resolve_waiting(
    read_tree: ReadTree,
    name: str,
    target: Mapping[str, Any],
    *,
    timeout_ms: int,
    now: Callable[[], float],
    sleep: Callable[[float], None],
) -> Resolution:
    """Re-read the window until `name` resolves to one element, or the time runs out.

    `timeoutMs: 0` checks once (RS NFR-05). The last failure is the one raised, so the message
    describes the state the window actually ended in rather than the first thing that went
    wrong.
    """
    primary = target.get("properties") or {}
    fallback = target.get("fallback") or None
    deadline = now() + timeout_ms / 1000
    while True:
        nodes, infos = read_tree()
        descriptors = describe_tree(nodes)
        try:
            return resolve(descriptors, infos, name, primary, fallback)
        except Unsupported:
            # A property set playback cannot match on is a client bug: waiting cannot fix it.
            raise
        except (NotFound, Ambiguous) as exc:
            last: Exception = exc
        remaining = deadline - now()
        if timeout_ms == 0 or remaining <= 0:
            raise last
        sleep(min(POLL_INTERVAL_S, remaining))
