"""Checks schemas/step.schema.json against its examples (#13, v0.2: #147).

The schema is shared by every component; these tests live in ai/ because the
AI service is its first Python consumer and CI already runs this module.
"""

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

SCHEMAS = Path(__file__).resolve().parents[2] / "schemas"
EXAMPLES = SCHEMAS / "examples" / "step"
KEYWORDS = {"Click", "Type", "Select", "SelectRow", "Verify", "Wait"}
PROPERTIES = {
    "name",
    "value",
    "enabled",
    "visible",
    "checked",
    "selected",
    "cell",
    "rowExists",
    "rowCount",
}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


SCHEMA = load(SCHEMAS / "step.schema.json")
VERSION = SCHEMA["properties"]["version"]["const"]
VALIDATOR = Draft202012Validator(SCHEMA)


def step_validator(schema: dict) -> Draft202012Validator:
    """How a consumer validates a single step: by reference to the step definition."""
    return Draft202012Validator(
        {"$ref": f"{schema['$id']}#/$defs/step"},
        registry=Registry().with_resource(
            schema["$id"], Resource.from_contents(schema)
        ),
    )


STEP_VALIDATOR = step_validator(SCHEMA)
CASES = load(EXAMPLES / "cases.json")
EXAMPLE_FILES = ["login-and-customer.json", "customer-search-grid.json"]
# Written for version 0.1; only their version changed in 0.2.
V0_1_EXAMPLE = "login-and-customer.json"


def as_document(case: dict) -> dict:
    if "document" in case:
        return case["document"]
    return {"version": VERSION, "steps": [case["step"]]}


def leaf_errors(document, validator=VALIDATOR) -> list:
    """Every failing keyword, with errors under anyOf/oneOf flattened."""
    pending, leaves = list(validator.iter_errors(document)), []
    while pending:
        error = pending.pop()
        if error.context:
            pending.extend(error.context)
        else:
            leaves.append(error)
    return leaves


def test_schema_is_valid_json_schema():
    Draft202012Validator.check_schema(SCHEMA)


def test_keywords_and_checkpoint_properties():
    defs = SCHEMA["$defs"]
    assert set(defs["step"]["properties"]["keyword"]["enum"]) == KEYWORDS
    assert set(defs["checkpoint"]["properties"]["property"]["enum"]) == PROPERTIES


@pytest.mark.parametrize("name", EXAMPLE_FILES)
def test_example_test_validates(name):
    document = load(EXAMPLES / name)
    VALIDATOR.validate(document)
    assert document["version"] == VERSION
    for step in document["steps"]:
        STEP_VALIDATOR.validate(step)


def test_examples_cover_every_keyword_and_checkpoint_property():
    steps = [step for name in EXAMPLE_FILES for step in load(EXAMPLES / name)["steps"]]
    assert len(load(EXAMPLES / V0_1_EXAMPLE)["steps"]) >= 10
    assert {step["keyword"] for step in steps} == KEYWORDS
    checked = {step["checkpoint"]["property"] for step in steps if "checkpoint" in step}
    assert checked >= {"name", "value", "enabled", "visible", "checked"}
    assert checked >= {"cell", "rowExists", "rowCount"}


def test_grid_example_uses_both_row_forms():
    rows = []
    for step in load(EXAMPLES / "customer-search-grid.json")["steps"]:
        rows += [step.get("row"), step.get("checkpoint", {}).get("row")]
    rows = [row for row in rows if row]
    assert any("index" in row for row in rows)
    assert any("value" in row and "column" in row for row in rows)
    assert any("value" in row and "column" not in row for row in rows)


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
    assert len([case for case in CASES["invalid"] if "since" in case]) >= 10


# --- Compatibility with version 0.1 (ADR 2026-10-28-step-schema-v0-2-rows) ----


def v0_1_documents() -> list[dict]:
    """The 0.1 example test and the 0.1 valid cases, labelled 0.1 again."""
    documents = [load(EXAMPLES / V0_1_EXAMPLE)]
    documents += [as_document(case) for case in CASES["valid"] if "since" not in case]
    return [{**document, "version": "0.1"} for document in documents]


def test_every_v0_1_step_is_a_valid_step_unchanged():
    steps = [step for document in v0_1_documents() for step in document["steps"]]
    assert len(steps) >= 20
    for step in steps:
        STEP_VALIDATOR.validate(step)


def test_a_v0_1_document_differs_only_in_its_version():
    """Migration: change "0.1" to "0.2" and nothing else."""
    for document in v0_1_documents():
        errors = list(VALIDATOR.iter_errors(document))
        assert [(list(e.path), e.validator) for e in errors] == [(["version"], "const")]
        VALIDATOR.validate({**document, "version": VERSION})


def test_v0_1_cases_are_still_there():
    """The 0.1 cases stay in cases.json, so every 0.1 rule is still tested."""
    old = [case for kind in ("valid", "invalid") for case in CASES[kind]]
    old = [case for case in old if "since" not in case]
    assert len(old) == 7 + 29


# --- Each new rule bites --------------------------------------------------------


def rule_index(schema: dict, definition: str, selector: str, test) -> int:
    """Index of the allOf rule of `definition` whose `if` tests `selector` == `test`."""
    for i, rule in enumerate(schema["$defs"][definition]["allOf"]):
        condition = rule["if"]["properties"][selector]
        if condition.get("const", condition.get("enum")) == test:
            return i
    raise LookupError(f"{definition}: no rule for {selector} {test}")


def drop_rule(definition: str, selector: str, test):
    def mutate(schema: dict) -> None:
        rules = schema["$defs"][definition]["allOf"]
        del rules[rule_index(schema, definition, selector, test)]

    return mutate


def drop_from_rule(definition: str, selector: str, test, value: str):
    def mutate(schema: dict) -> None:
        i = rule_index(schema, definition, selector, test)
        schema["$defs"][definition]["allOf"][i]["if"]["properties"][selector][
            "enum"
        ].remove(value)

    return mutate


def drop_key(path: list, key: str):
    def mutate(schema: dict) -> None:
        node = schema
        for part in path:
            node = node[part]
        del node[key]

    return mutate


V0_KEYWORDS = ["Click", "Type", "Select", "Verify", "Wait"]
TARGET_PROPERTIES = ["name", "value", "enabled", "visible", "checked", "selected"]
INDEX_ROW = ["$defs", "row", "anyOf", 0]
KEY_ROW = ["$defs", "row", "anyOf", 1]
MUTATIONS = [
    (drop_rule("step", "keyword", V0_KEYWORDS), "Click with a row"),
    (drop_rule("step", "keyword", "SelectRow"), "SelectRow without row"),
    (drop_rule("step", "keyword", "SelectRow"), "SelectRow with a checkpoint"),
    (
        drop_rule("checkpoint", "property", TARGET_PROPERTIES),
        "name check with a row",
    ),
    (drop_rule("checkpoint", "property", "cell"), "cell without column"),
    (drop_rule("checkpoint", "property", "rowExists"), "rowExists without row"),
    (drop_rule("checkpoint", "property", "rowCount"), "rowCount with a row"),
    (drop_rule("checkpoint", "property", "rowCount"), "rowCount as a string"),
    (
        drop_from_rule("checkpoint", "property", ["name", "value", "cell"], "cell"),
        "cell with a boolean expected value",
    ),
    (
        drop_from_rule(
            "checkpoint",
            "property",
            ["enabled", "visible", "checked", "selected", "rowExists"],
            "rowExists",
        ),
        "rowExists with contains",
    ),
    (drop_key(INDEX_ROW + ["properties", "index"], "minimum"), "row index 0"),
    (
        drop_key(INDEX_ROW + ["properties", "index"], "maximum"),
        "row index above 100000",
    ),
    (
        drop_key(INDEX_ROW, "additionalProperties"),
        "row with both an index and a value",
    ),
    (drop_key(KEY_ROW, "required"), "row with a column but no value"),
    (
        drop_key(KEY_ROW + ["properties", "value"], "minLength"),
        "row with an empty value",
    ),
    (drop_key(["$defs", "column"], "minLength"), "row with an empty column"),
]


@pytest.mark.parametrize(
    "mutate, case_name",
    MUTATIONS,
    ids=[f"{i}-{name}" for i, (_, name) in enumerate(MUTATIONS)],
)
def test_dropping_a_new_rule_lets_its_invalid_case_through(mutate, case_name):
    """Every 0.2 rule is needed: without it, a named invalid case validates."""
    (case,) = [case for case in CASES["invalid"] if case["name"] == case_name]
    schema = copy.deepcopy(SCHEMA)
    mutate(schema)
    assert not VALIDATOR.is_valid(as_document(case))
    assert Draft202012Validator(schema).is_valid(as_document(case))


# --- Bounded strings ------------------------------------------------------------


def grid_check(**checkpoint) -> dict:
    return {
        "keyword": "Verify",
        "target": "main.customerGrid",
        "checkpoint": checkpoint,
    }


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
        {
            "keyword": "SelectRow",
            "target": "main.customerGrid",
            "row": {"value": "x" * 1001},
        },
        grid_check(
            property="cell",
            row={"index": 1},
            column="x" * 101,
            operator="equals",
            expected="Ayşe",
        ),
        grid_check(
            property="cell",
            row={"index": 1},
            column="Ad",
            operator="equals",
            expected="x" * 1001,
        ),
    ],
    ids=["value", "target", "expected", "row value", "column", "cell expected"],
)
def test_long_strings_are_rejected(step):
    """Bounded strings stop a runaway model output early (#7 finding 1)."""
    rules = {error.validator for error in leaf_errors(as_document({"step": step}))}
    assert "maxLength" in rules
