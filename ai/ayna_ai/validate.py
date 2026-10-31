"""Checks a step document against the step schema and the object repository.

The generator constrains decoding with a schema derived from
`schemas/step.schema.json`; this module validates the result against the
original file, so a gap in the derivation or a server that ignores the
constraint cannot let an invalid step through.

A document is checked in two parts (#71, FR-26): the envelope (`version`, the
`steps` list itself) as a whole, then every step on its own against the step
schema's `steps.items` (`#/$defs/step`) and the object list. A bad step is
dropped with its reason; the other steps stay.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Collection
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from jsonschema import Draft202012Validator

# ai/ayna_ai/validate.py -> repository root -> schemas/
STEP_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "step.schema.json"

# Reserved target: the model's way to say "no repository object fits this
# action" (SDD AI-3, forced choice). It fits the logical-name pattern, so the
# grammar can offer it; a step that uses it is always dropped, and no real
# object may have this name.
NO_MATCH = "none.noMatch"


def load_step_schema(path: Path | None = None) -> dict:
    """Read the step schema (by default the repository's frozen contract)."""
    return json.loads((path or STEP_SCHEMA_PATH).read_text(encoding="utf-8"))


class DropCode(StrEnum):
    """Why a generated step was dropped; the first that applies is the code."""

    UNKNOWN_KEYWORD = "unknown_keyword"  # keyword outside the step schema's enum
    UNKNOWN_TARGET = "unknown_target"  # target is not one of the given objects
    NO_MATCH = "no_match"  # the model chose the reserved target NO_MATCH
    INVALID_STEP = "invalid_step"  # any other step-schema violation, or no reason


@dataclass(frozen=True)
class DroppedStep:
    index: int  # position in the model's step list, 0-based
    step: object  # the step exactly as the model wrote it
    code: DropCode
    reason: str  # every problem found, for people

    @classmethod
    def of(
        cls, index: int, step: object, problems: list[tuple[DropCode, str]]
    ) -> DroppedStep:
        """The first problem gives the code; the reason lists them all."""
        reason = "; ".join(text for _, text in problems)
        return cls(index, step, problems[0][0], reason)

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "code": str(self.code),
            "reason": self.reason,
            "step": self.step,
        }


class StepValidator:
    def __init__(self, schema: dict | None = None) -> None:
        self.schema = schema if schema is not None else load_step_schema()
        Draft202012Validator.check_schema(self.schema)
        self._validator = Draft202012Validator(self.schema)
        # Envelope: the document with each step left unchecked. Step: what the
        # document applies to every element of `steps`. Together they accept
        # exactly what the whole schema accepts.
        envelope = copy.deepcopy(self.schema)
        items = envelope["properties"]["steps"].pop("items")
        self._envelope = Draft202012Validator(envelope)
        self._step = Draft202012Validator({"$defs": self.schema["$defs"], **items})

    def schema_errors(self, document: object) -> list[str]:
        """Messages for every schema violation, as `<json path>: <message>`."""
        return _messages(self._validator, document)

    def envelope_errors(self, document: object) -> list[str]:
        """Violations outside the individual steps: version, the list itself."""
        return _messages(self._envelope, document)

    def step_problems(
        self, step: object, objects: Collection[str]
    ) -> list[tuple[DropCode, str]]:
        """Why `step` cannot be suggested, most specific first; [] if it can."""
        errors = list(self._step.iter_errors(step))
        problems = []
        if any(list(e.absolute_path) == ["keyword"] for e in errors):
            problems.append(
                (DropCode.UNKNOWN_KEYWORD, f"unknown keyword {step['keyword']!r}")
            )
        target = step.get("target") if isinstance(step, dict) else None
        if target == NO_MATCH:
            problems.append((DropCode.NO_MATCH, "no repository object matches"))
        elif isinstance(target, str) and target not in objects:
            problems.append(
                (
                    DropCode.UNKNOWN_TARGET,
                    f"{target!r} is not in the object repository",
                )
            )
        covered = {"keyword"} | ({"target"} if isinstance(target, str) else set())
        rest = [
            _describe(e, step)
            for e in sorted(errors, key=lambda e: e.json_path)
            if not (e.absolute_path and e.absolute_path[0] in covered)
        ]
        if rest:
            problems.append((DropCode.INVALID_STEP, "; ".join(rest)))
        return problems


def _messages(validator: Draft202012Validator, instance: object) -> list[str]:
    errors = sorted(validator.iter_errors(instance), key=lambda e: e.json_path)
    return [f"{error.json_path}: {error.message}" for error in errors]


def _describe(error, step: object = None) -> str:
    """`<json path>: <message>`, naming the field a `false` subschema forbids.

    jsonschema reports such an error (e.g. `value` on a Click step) at the step
    itself, as "False schema does not allow 'x'", without the field's name;
    `error.instance` is the field's value object, so find it in `step`.
    """
    if error.validator is None and isinstance(step, dict):
        fields = [name for name, value in step.items() if value is error.instance]
        if fields:
            return f"{error.json_path}.{fields[0]}: not allowed for this keyword"
    return f"{error.json_path}: {error.message}"
