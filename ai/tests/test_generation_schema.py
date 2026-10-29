"""The generation schema derived from schemas/step.schema.json (#37)."""

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from ayna_ai.generate import SchemaDerivationError, generation_schema
from ayna_ai.validate import load_step_schema

EXAMPLES = Path(__file__).resolve().parents[2] / "schemas" / "examples" / "step"
STEP_SCHEMA = load_step_schema()
ORIGINAL = Draft202012Validator(STEP_SCHEMA)
OBJECTS = [
    "login.usernameInput",
    "login.loginButton",
    "main.searchInput",
    "customer.cityCombo",
]
KEYWORDS = STEP_SCHEMA["$defs"]["step"]["properties"]["keyword"]["enum"]


def is_name(value) -> bool:
    return Draft202012Validator(STEP_SCHEMA["$defs"]["logicalName"]).is_valid(value)


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def derive(objects=OBJECTS, **kwargs) -> dict:
    return generation_schema(STEP_SCHEMA, objects, **kwargs)


def branches(schema: dict) -> dict[str, dict]:
    """Step branches by keyword."""
    return {
        b["properties"]["keyword"]["const"]: b
        for b in schema["properties"]["steps"]["items"]["anyOf"]
    }


def as_document(case: dict) -> dict:
    return (
        case["document"]
        if "document" in case
        else {"version": "0.1", "steps": [case["step"]]}
    )


def without_ids(document: dict) -> dict:
    """A valid document as the generator would produce it: no server ids."""
    document = copy.deepcopy(document)
    for step in document["steps"]:
        step.pop("id", None)
    return document


def test_derived_schema_is_valid_json_schema():
    Draft202012Validator.check_schema(derive())


def test_one_branch_per_schema_keyword():
    assert list(branches(derive())) == KEYWORDS


def test_target_is_an_enum_of_the_objects_in_every_branch():
    schema = derive(OBJECTS + [OBJECTS[0]])  # duplicates are dropped, order kept
    for branch in branches(schema).values():
        assert branch["properties"]["target"] == {"type": "string", "enum": OBJECTS}


def test_fields_follow_the_per_keyword_rules():
    b = branches(derive())
    fields = {k: set(branch["properties"]) for k, branch in b.items()}
    assert fields == {
        "Click": {"keyword", "target", "timeoutMs"},
        "Type": {"keyword", "target", "value", "timeoutMs"},
        "Select": {"keyword", "target", "value", "timeoutMs"},
        "Verify": {"keyword", "target", "checkpoint", "timeoutMs"},
        "Wait": {"keyword", "target", "timeoutMs"},
    }
    assert "value" in b["Type"]["required"]
    assert "value" in b["Select"]["required"]
    assert b["Select"]["properties"]["value"]["minLength"] == 1
    assert "checkpoint" in b["Verify"]["required"]
    for branch in b.values():
        assert branch["additionalProperties"] is False


def test_checkpoint_is_split_by_property_kind():
    checkpoint = branches(derive())["Verify"]["properties"]["checkpoint"]
    text, boolean = checkpoint["anyOf"]
    assert text["properties"]["property"] == {"enum": ["name", "value"]}
    assert text["properties"]["expected"]["type"] == "string"
    assert boolean["properties"]["property"] == {
        "enum": ["enabled", "visible", "checked", "selected"]
    }
    assert boolean["properties"]["operator"] == {"const": "equals"}
    assert boolean["properties"]["expected"] == {"type": "boolean"}


def test_free_strings_are_bounded():
    b = branches(derive(max_text=50))
    assert b["Type"]["properties"]["value"]["maxLength"] == 50
    assert b["Select"]["properties"]["value"]["maxLength"] == 50
    text = b["Verify"]["properties"]["checkpoint"]["anyOf"][0]
    assert text["properties"]["expected"]["maxLength"] == 50
    # Never looser than the step schema itself (1000).
    assert (
        branches(derive(max_text=5000))["Type"]["properties"]["value"]["maxLength"]
        == 1000
    )


def test_step_list_is_bounded_and_not_empty():
    steps = derive(max_steps=7)["properties"]["steps"]
    assert (steps["minItems"], steps["maxItems"]) == (1, 7)


def test_version_and_root_constraints_are_kept():
    schema = derive()
    assert schema["properties"]["version"] == {
        "const": STEP_SCHEMA["properties"]["version"]["const"]
    }
    assert schema["required"] == STEP_SCHEMA["required"]
    assert schema["additionalProperties"] is False


def test_no_constructs_that_grammar_converters_ignore():
    text = json.dumps(derive())
    for keyword in ("$ref", "$defs", "allOf", "oneOf", '"if"', '"then"', '"not"'):
        assert keyword not in text, keyword
    # No boolean subschemas: the only `false` left is additionalProperties.
    assert text.count("false") == text.count('"additionalProperties": false')


def test_derivation_leaves_the_step_schema_unchanged():
    before = copy.deepcopy(STEP_SCHEMA)
    derive()
    assert STEP_SCHEMA == before


def test_valid_examples_fit_the_derived_schema():
    """Not narrower than needed: real steps (without server ids) still fit."""
    documents = [load(EXAMPLES / "login-and-customer.json")]
    documents += [as_document(case) for case in load(EXAMPLES / "cases.json")["valid"]]
    checked = 0
    for document in map(without_ids, documents):
        if not document["steps"]:
            continue  # generation asks for at least one step
        targets = [step["target"] for step in document["steps"]]
        derived = derive(targets, max_steps=len(targets))
        assert not list(Draft202012Validator(derived).iter_errors(document))
        checked += 1
    assert checked >= 7


@pytest.mark.parametrize(
    "case", load(EXAMPLES / "cases.json")["invalid"], ids=lambda case: case["name"]
)
def test_invalid_examples_are_rejected_by_the_derived_schema(case):
    document = as_document(case)
    steps = document.get("steps") if isinstance(document.get("steps"), list) else []
    targets = [
        step.get("target")
        for step in steps
        if isinstance(step, dict) and is_name(step.get("target"))
    ]
    derived = Draft202012Validator(derive(targets or OBJECTS))
    assert not derived.is_valid(document)


def samples(schema: dict):
    """Instances the derived (sub)schema accepts, covering every branch and bound."""
    if "anyOf" in schema:
        for branch in schema["anyOf"]:
            yield from samples(branch)
    elif "const" in schema:
        yield schema["const"]
    elif "enum" in schema:
        yield from schema["enum"]
    elif schema["type"] == "string":
        yield "a" * schema.get("minLength", 0)
        yield "ş" * schema["maxLength"]
    elif schema["type"] == "integer":
        yield from (schema["minimum"], schema["maximum"])
    elif schema["type"] == "boolean":
        yield from (True, False)
    elif schema["type"] == "array":
        for item in samples(schema["items"]):
            yield [item] * schema["minItems"]
            yield [item] * schema["maxItems"]
    elif schema["type"] == "object":
        props = schema["properties"]
        first = {name: next(samples(sub)) for name, sub in props.items()}
        yield {name: first[name] for name in schema["required"]}
        yield first
        for name, sub in props.items():
            for value in samples(sub):
                yield {name: value} | {k: v for k, v in first.items() if k != name}


def test_everything_the_derived_schema_accepts_is_a_valid_step_document():
    """Never wider than the step schema: generated text cannot break the contract."""
    derived = derive()
    validator = Draft202012Validator(derived)
    documents = list(samples(derived))
    assert len(documents) > 40
    for document in documents:
        assert validator.is_valid(document), document
        assert ORIGINAL.is_valid(document), list(ORIGINAL.iter_errors(document))


def test_objects_must_be_valid_logical_names():
    with pytest.raises(ValueError, match="Login Button"):
        derive(["login.loginButton", "Login Button"])
    with pytest.raises(ValueError, match="at least one"):
        derive([])


@pytest.mark.parametrize(
    "mutate",
    [
        lambda s: s["$defs"]["step"].update(oneOf=[{"required": ["value"]}]),
        lambda s: s["$defs"]["step"]["allOf"].append(
            {"if": {"properties": {"target": {"const": "a.b"}}}, "then": {}}
        ),
        lambda s: s["$defs"]["step"]["allOf"][0]["then"].update(
            {"not": {"required": ["timeoutMs"]}}
        ),
        lambda s: s["$defs"]["step"]["properties"]["id"].update(
            {"$ref": "https://example.com/x"}
        ),
        lambda s: s["$defs"]["step"]["required"].append("id"),
    ],
    ids=[
        "oneOf on step",
        "rule on another field",
        "then with extra keywords",
        "remote ref",
        "id required",
    ],
)
def test_unknown_constructs_fail_loudly(mutate):
    """A future schema change must break the derivation, not silently loosen it."""
    schema = copy.deepcopy(STEP_SCHEMA)
    mutate(schema)
    with pytest.raises(SchemaDerivationError):
        generation_schema(schema, OBJECTS)
