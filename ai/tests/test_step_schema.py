"""Checks schemas/step.schema.json against its examples (#13).

The schema is shared by every component; these tests live in ai/ because the
AI service is its first Python consumer and CI already runs this module.
"""

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

SCHEMAS = Path(__file__).resolve().parents[2] / "schemas"
EXAMPLES = SCHEMAS / "examples" / "step"
KEYWORDS = {"Click", "Type", "Select", "Verify", "Wait"}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


SCHEMA = load(SCHEMAS / "step.schema.json")
VALIDATOR = Draft202012Validator(SCHEMA)
# How a consumer validates a single step: by reference to the step definition.
STEP_VALIDATOR = Draft202012Validator(
    {"$ref": f"{SCHEMA['$id']}#/$defs/step"},
    registry=Registry().with_resource(SCHEMA["$id"], Resource.from_contents(SCHEMA)),
)
CASES = load(EXAMPLES / "cases.json")


def as_document(case: dict) -> dict:
    if "document" in case:
        return case["document"]
    return {"version": "0.1", "steps": [case["step"]]}


def leaf_errors(document) -> list:
    """Every failing keyword, with errors under anyOf/oneOf flattened."""
    pending, leaves = list(VALIDATOR.iter_errors(document)), []
    while pending:
        error = pending.pop()
        if error.context:
            pending.extend(error.context)
        else:
            leaves.append(error)
    return leaves


def test_schema_is_valid_json_schema():
    Draft202012Validator.check_schema(SCHEMA)


def test_example_test_validates_and_covers_every_keyword():
    document = load(EXAMPLES / "login-and-customer.json")
    VALIDATOR.validate(document)
    assert len(document["steps"]) >= 10
    assert {step["keyword"] for step in document["steps"]} == KEYWORDS


def test_each_example_step_validates_on_its_own():
    for step in load(EXAMPLES / "login-and-customer.json")["steps"]:
        STEP_VALIDATOR.validate(step)


@pytest.mark.parametrize("case", CASES["valid"], ids=lambda case: case["name"])
def test_valid_case(case):
    VALIDATOR.validate(as_document(case))


@pytest.mark.parametrize("case", CASES["invalid"], ids=lambda case: case["name"])
def test_invalid_case_is_rejected_by_its_rule(case):
    errors = leaf_errors(as_document(case))
    assert errors, "the schema accepted an invalid document"
    # A boolean `false` subschema reports no keyword.
    rules = {error.validator or "false" for error in errors}
    assert case["rule"] in rules, [error.message for error in errors]


def test_there_are_enough_invalid_cases():
    assert len(CASES["invalid"]) >= 5


@pytest.mark.parametrize(
    "step",
    [
        {"keyword": "Type", "target": "login.usernameInput", "value": "x" * 1001},
        {"keyword": "Click", "target": "login." + "a" * 100},
        {
            "keyword": "Verify",
            "target": "login.statusLabel",
            "checkpoint": {
                "property": "name",
                "operator": "equals",
                "expected": "x" * 1001,
            },
        },
    ],
    ids=["value", "target", "expected"],
)
def test_long_strings_are_rejected(step):
    """Bounded strings stop a runaway model output early (#7 finding 1)."""
    rules = {error.validator for error in leaf_errors(as_document({"step": step}))}
    assert "maxLength" in rules
