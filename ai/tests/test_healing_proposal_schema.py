"""Checks schemas/healing-proposal.schema.json (version 0.2 proposed, #149) and its examples.

The agent produces the document, the client and the CLI runner forward it, the server
stores it. These checks live in ai/, like the step schema's, because CI's ai job is
where the jsonschema library is. Two kinds:

- JSON Schema validation, including that 0.2 only adds optional keys: a 0.1 document
  is valid once it is relabelled. Skipped when jsonschema is not installed.
- The arithmetic the schema cannot express, with the standard library only: every
  number is an exact fraction in lowest terms within [0, 1], each contribution equals
  weight * similarity / total weight, the contributions add up exactly to the score,
  and the candidates are ranked by score, then element id. This is what keeps
  "contributions sum to the score" true across Python, Java and TypeScript.
"""

import copy
import json
from fractions import Fraction
from pathlib import Path

import pytest

SCHEMAS = Path(__file__).resolve().parents[2] / "schemas"
EXAMPLES = SCHEMAS / "examples" / "healing-proposal"
EXAMPLE_FILES = sorted(p for p in EXAMPLES.glob("*.json") if p.name != "cases.json")


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


SCHEMA = load(SCHEMAS / "healing-proposal.schema.json")
CASES = load(EXAMPLES / "cases.json")
BASE = load(EXAMPLES / CASES["base"])


# --- arithmetic --------------------------------------------------------------------


def arithmetic_problems(proposal: dict) -> set[str]:
    """Names of the arithmetic rules the proposal breaks; empty when it is consistent."""
    problems: set[str] = set()

    def exact(text: str) -> Fraction:
        value = Fraction(text)
        if str(value) != text:
            problems.add("lowestTerms")
        return value

    weights = {k: exact(v) for k, v in proposal["scorer"]["weights"].items()}
    candidates = proposal["candidates"]
    if proposal["candidatesScored"] < len(candidates):
        problems.add("candidatesScored")
    if [c["rank"] for c in candidates] != list(range(1, len(candidates) + 1)):
        problems.add("ranks")
    if len({c["elementId"] for c in candidates}) != len(candidates):
        problems.add("uniqueElements")

    compared = None
    order = []
    for candidate in candidates:
        score = exact(candidate["score"])
        contributions = {k: exact(v) for k, v in candidate["contributions"].items()}
        similarities = {k: exact(v) for k, v in candidate["similarities"].items()}
        values = [score, *contributions.values(), *similarities.values()]
        if any(not 0 <= value <= 1 for value in values):
            problems.add("unitInterval")
        if set(contributions) != set(similarities):
            problems.add("sameKeys")
        if compared is None:
            compared = set(similarities)
        elif set(similarities) != compared:
            problems.add("sameProperties")
        if any(weights.get(name, 0) == 0 for name in similarities):
            problems.add("weight")
        total = sum(weights.get(name, Fraction(0)) for name in similarities)
        if total and any(
            contributions.get(name) != weights.get(name, 0) * similarity / total
            for name, similarity in similarities.items()
        ):
            problems.add("contribution")
        if sum(contributions.values(), Fraction(0)) != score:
            problems.add("sum")
        order.append((-score, candidate["elementId"]))
    if order != sorted(order):
        problems.add("order")
    return problems


# --- JSON Patch subset (add, remove, replace, copy, move) for the cases --------------


def _locate(document, pointer: str):
    parts = [p.replace("~1", "/").replace("~0", "~") for p in pointer.split("/")[1:]]
    parent = document
    for part in parts[:-1]:
        parent = parent[int(part)] if isinstance(parent, list) else parent[part]
    return parent, parts[-1]


def _get(document, pointer: str):
    parent, key = _locate(document, pointer)
    return parent[int(key)] if isinstance(parent, list) else parent[key]


def _remove(document, pointer: str):
    parent, key = _locate(document, pointer)
    if isinstance(parent, list):
        parent.pop(int(key))
    else:
        del parent[key]


def _add(document, pointer: str, value) -> None:
    parent, key = _locate(document, pointer)
    if isinstance(parent, list):
        if key == "-":
            parent.append(value)
        else:
            parent.insert(int(key), value)
    else:
        parent[key] = value


def patched(patch: list[dict]) -> dict:
    document = copy.deepcopy(BASE)
    for operation in patch:
        op = operation["op"]
        if op in ("copy", "move"):
            value = copy.deepcopy(_get(document, operation["from"]))
            if op == "move":
                _remove(document, operation["from"])
            _add(document, operation["path"], value)
        elif op == "remove":
            _remove(document, operation["path"])
        elif op == "add":
            _add(document, operation["path"], operation["value"])
        elif op == "replace":
            parent, key = _locate(document, operation["path"])
            parent[int(key) if isinstance(parent, list) else key] = operation["value"]
        else:
            raise ValueError(f"unsupported op {op!r}")
    return document


# --- schema ------------------------------------------------------------------------


@pytest.fixture(scope="module")
def validator():
    jsonschema = pytest.importorskip("jsonschema")
    return jsonschema.Draft202012Validator(SCHEMA)


def leaf_errors(validator, document) -> list:
    """Every failing keyword, with errors under anyOf/oneOf flattened."""
    pending, leaves = list(validator.iter_errors(document)), []
    while pending:
        error = pending.pop()
        if error.context:
            pending.extend(error.context)
        else:
            leaves.append(error)
    return leaves


def test_schema_is_valid_json_schema(validator):
    type(validator).check_schema(SCHEMA)


@pytest.mark.parametrize("path", EXAMPLE_FILES, ids=lambda p: p.name)
def test_example_validates(validator, path):
    validator.validate(load(path))


@pytest.mark.parametrize("case", CASES["valid"], ids=lambda case: case["name"])
def test_valid_case(validator, case):
    validator.validate(patched(case["patch"]))


@pytest.mark.parametrize("case", CASES["invalid"], ids=lambda case: case["name"])
def test_invalid_case_is_rejected_by_its_rule(validator, case):
    errors = leaf_errors(validator, patched(case["patch"]))
    assert errors, "the schema accepted an invalid document"
    rules = {error.validator for error in errors}
    assert case["rule"] in rules, [error.message for error in errors]


@pytest.mark.parametrize("case", CASES["arithmetic"], ids=lambda case: case["name"])
def test_arithmetic_case_passes_the_schema(validator, case):
    # These are exactly the mistakes the schema cannot see.
    validator.validate(patched(case["patch"]))


def as_0_1(proposal: dict) -> dict:
    """The proposal without the keys 0.2 added, labelled 0.1, as a 0.1 producer wrote it."""
    document = copy.deepcopy(proposal)
    document["version"] = "0.1"
    document["scorer"].pop("featureVersion", None)
    document["target"].pop("featureVersion", None)
    elements = [
        document["target"]["properties"],
        *(c["element"] for c in document["candidates"]),
    ]
    for element in elements:
        element.pop("dpi", None)
    return document


@pytest.mark.parametrize("path", EXAMPLE_FILES, ids=lambda p: p.name)
def test_0_1_document_is_valid_once_relabelled(validator, path):
    # 0.2 adds only optional keys (dpi, the feature versions), so relabelling is the
    # whole migration. Each release still accepts only its own label.
    old = as_0_1(load(path))
    assert "dpi" not in json.dumps(old) and "featureVersion" not in json.dumps(old)
    assert not validator.is_valid(old)
    validator.validate({**old, "version": "0.2"})


@pytest.mark.parametrize("path", EXAMPLE_FILES, ids=lambda p: p.name)
def test_example_names_the_feature_version_of_its_candidates(path):
    # The agent always writes it (#73 compares its output with these examples), even
    # though the schema keeps it optional so that 0.2 stays a superset of 0.1.
    assert load(path)["scorer"]["featureVersion"]


# --- arithmetic --------------------------------------------------------------------


def test_examples_exist():
    assert {p.name for p in EXAMPLE_FILES} >= {
        "login-button-renamed.json",
        "cli-run-without-server.json",
    }


@pytest.mark.parametrize("path", EXAMPLE_FILES, ids=lambda p: p.name)
def test_example_arithmetic_is_exact(path):
    assert arithmetic_problems(load(path)) == set()


@pytest.mark.parametrize("case", CASES["valid"], ids=lambda case: case["name"])
def test_valid_case_arithmetic_is_exact(case):
    assert arithmetic_problems(patched(case["patch"])) == set()


@pytest.mark.parametrize("case", CASES["arithmetic"], ids=lambda case: case["name"])
def test_arithmetic_case_is_caught_by_its_rule(case):
    problems = arithmetic_problems(patched(case["patch"]))
    assert case["rule"] in problems, problems


def test_bars_drawn_as_floats_match_the_score():
    # Screens convert each exact value to a double only to draw it. The bars then add
    # up to the shown score within float rounding; the exact strings stay the reference,
    # and no consumer compares floats for equality.
    for candidate in BASE["candidates"]:
        score = Fraction(candidate["score"])
        bars = [float(Fraction(v)) for v in candidate["contributions"].values()]
        assert abs(sum(bars) - float(score)) < 1e-12
