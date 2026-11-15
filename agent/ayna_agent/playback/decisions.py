"""The decision log: one JSONL line per failed step, with enough context to label it (#63).

**Why a log at all, when the result already carries a `category`.** The contract's five are
coarse on purpose — they cross three components and a translated report — and they are absent
for every failure the agent itself caused (`playback.triage` says why). Neither is enough to
answer the questions #63 exists for: RQ5 asks how often healing helps, #86 compares gated
against auto-applied, and #64 needs ≥50 labelled examples. Those need the *reason*, the
properties that were tried, the window, and the wording a person will read when labelling.

So: the result keeps the contract's view, the log keeps the measurement's view, and `reason` is
never absent — which is how "every failed step gets a category" (criterion 1) is true in the
place where labelling happens.

**JSONL, appended, never rewritten.** One line per failure means a run that dies halfway leaves
everything up to that point, two runs can append to one file without a merge, and `jq` and
pandas both read it without a parser of ours. A JSON array would need the file rewritten on
every line and would be unreadable if the process stopped mid-run.

Nothing here is Windows-only and nothing imports a backend, so a log can be written by the
client's agent, by the CLI runner (#61) or by a test.
"""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

#: The log's own version, so a reader can tell which fields to expect. Bumped when a field is
#: removed or changes meaning; adding one does not need it.
FORMAT_VERSION = 1


@dataclass(frozen=True)
class Decision:
    """One failed step, as the triage saw it."""

    #: When the step finished, ISO 8601 with a UTC offset.
    at: str
    #: `refusedStep`, `elementNotFound`, … — `triage.reason_for`, never empty.
    reason: str
    #: One of FR-35's five, or `None` when the failure is not about the application.
    category: str | None
    step_index: int
    keyword: str | None
    #: The repository object the step named, which is what a labeller looks up first.
    target: str | None
    message: str | None
    duration_ms: int | None = None
    #: `primary`, `fallback` or `None` — a fallback match is what #73 heals, so a labeller
    #: wants it even on a step that then failed for another reason.
    matched: str | None = None
    #: The property sets that were tried. The single most useful thing for labelling a
    #: recognition failure: without it, "no element matches login.loginButton" cannot be
    #: judged, because nobody can see what was asked for.
    tried: list[dict[str, Any]] = field(default_factory=list)
    run_id: str | None = None
    test_name: str | None = None
    window_title: str | None = None
    app_version: str | None = None
    #: Filled by a person later (#64's labelling): left out of the file entirely until then,
    #: so an unlabelled line and a line labelled "unknown" are never confused.
    label: str | None = None

    def to_json(self) -> dict[str, Any]:
        """Absent values are left out, as everywhere else in this project."""
        out: dict[str, Any] = {
            "v": FORMAT_VERSION,
            "at": self.at,
            "reason": self.reason,
            "stepIndex": self.step_index,
        }
        for key, value in (
            ("category", self.category),
            ("keyword", self.keyword),
            ("target", self.target),
            ("message", self.message),
            ("durationMs", self.duration_ms),
            ("matched", self.matched),
            ("runId", self.run_id),
            ("testName", self.test_name),
            ("windowTitle", self.window_title),
            ("appVersion", self.app_version),
            ("label", self.label),
        ):
            if value is not None:
                out[key] = value
        if self.tried:
            out["tried"] = self.tried
        return out


def now_stamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


class DecisionLog:
    """Appends decisions to a JSONL file.

    Opened per write rather than held open: a run can take minutes, a CI job can be cancelled,
    and a file handle held across that loses whatever the buffer still had. One line is small
    enough that the open costs nothing worth saving.
    """

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    def append(self, decision: Decision) -> None:
        line = json.dumps(decision.to_json(), ensure_ascii=False, sort_keys=False)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # `ensure_ascii=False` and an explicit UTF-8 encoding: these lines carry Turkish test
        # names and application messages, and the default on a Windows runner is cp1252.
        with self.path.open("a", encoding="utf-8", newline="\n") as out:
            out.write(line + "\n")

    def read(self) -> Iterator[dict[str, Any]]:
        """Every decision in the file, skipping a half-written last line.

        A half-written line is not corruption to report: a cancelled CI job leaves one, and
        the hundred before it are still the data.
        """
        if not self.path.exists():
            return
        with self.path.open(encoding="utf-8") as lines:
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except ValueError:
                    continue


def decision_from(
    result: Any,
    step: Mapping[str, Any],
    *,
    reason: str,
    tried: list[dict[str, Any]] | None = None,
    at: str | None = None,
    **context: Any,
) -> Decision:
    """A `Decision` from a failed `StepResult` and the step it came from."""
    return Decision(
        at=at or now_stamp(),
        reason=reason,
        category=getattr(result, "category", None),
        step_index=result.step_index,
        keyword=step.get("keyword") if isinstance(step, Mapping) else None,
        target=step.get("target") if isinstance(step, Mapping) else None,
        message=result.message,
        duration_ms=result.duration_ms,
        matched=getattr(result, "matched", None),
        tried=tried or [],
        **context,
    )


def export_jsonl(decisions: list[Decision], path: Path | str) -> Path:
    """Write a whole set of decisions as JSONL, atomically.

    Used for an export rather than for logging as a run goes: a temp file and a rename, so a
    reader never sees half a file. `eval/` reads what this writes.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=str(path.parent), suffix=".jsonl")
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as out:
            for decision in decisions:
                out.write(json.dumps(decision.to_json(), ensure_ascii=False) + "\n")
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
    return path
