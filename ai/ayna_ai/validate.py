"""Checks a step document against the step schema and the object repository.

The generator constrains decoding with a schema derived from
`schemas/step.schema.json`; this module validates the result against the
original file, so a gap in the derivation or a server that ignores the
constraint cannot let an invalid step through.
"""

from __future__ import annotations

import json
from collections.abc import Collection
from pathlib import Path

from jsonschema import Draft202012Validator

# ai/ayna_ai/validate.py -> repository root -> schemas/
STEP_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "step.schema.json"


def load_step_schema(path: Path | None = None) -> dict:
    """Read the step schema (by default the repository's frozen contract)."""
    return json.loads((path or STEP_SCHEMA_PATH).read_text(encoding="utf-8"))


class StepValidator:
    def __init__(self, schema: dict | None = None) -> None:
        self.schema = schema if schema is not None else load_step_schema()
        Draft202012Validator.check_schema(self.schema)
        self._validator = Draft202012Validator(self.schema)

    def schema_errors(self, document: object) -> list[str]:
        """Messages for every schema violation, as `<json path>: <message>`."""
        errors = sorted(
            self._validator.iter_errors(document), key=lambda e: e.json_path
        )
        return [f"{error.json_path}: {error.message}" for error in errors]

    @staticmethod
    def unknown_targets(document: dict, objects: Collection[str]) -> list[str]:
        """Steps whose target is not one of `objects`. Call on a schema-valid document."""
        return [
            f"$.steps[{i}].target: {step['target']!r} is not in the object repository"
            for i, step in enumerate(document["steps"])
            if step["target"] not in objects
        ]
