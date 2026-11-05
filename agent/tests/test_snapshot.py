"""Tests for the window snapshot document (#12).

Three kinds, and the last two are the ones that keep the contract honest:

- the schema and its named cases (`schemas/examples/snapshot/cases.json`), as the element
  and healing-proposal schemas are tested;
- **lockstep with `element.schema.json`**: the snapshot duplicates the element descriptor so
  that it validates on its own in Java, TypeScript and Python, so every property is compared
  here, constraints included. Only the descriptions may differ;
- **the example is what the code produces**: `schemas/examples/snapshot/trial-login.json` is
  rebuilt from the same captured trial-app tree the descriptor tests use, so the document
  other components design against cannot drift away from the agent that writes it.
"""

from __future__ import annotations

import copy
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from ayna_agent.recognition import snapshot

SCHEMAS = Path(__file__).resolve().parents[2] / "schemas"
SCHEMA = json.loads((SCHEMAS / "snapshot.schema.json").read_text(encoding="utf-8"))
ELEMENT_SCHEMA = json.loads(
    (SCHEMAS / "element.schema.json").read_text(encoding="utf-8")
)
EXAMPLES = SCHEMAS / "examples" / "snapshot"
EXAMPLE = EXAMPLES / "trial-login.json"
CASES = json.loads((EXAMPLES / "cases.json").read_text(encoding="utf-8"))
TRIAL_TREE = Path(__file__).resolve().parent / "data" / "trial-app-tree.json"


@pytest.fixture(scope="module")
def validator() -> Draft202012Validator:
    return Draft202012Validator(SCHEMA)


@pytest.fixture(scope="module")
def base() -> dict:
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


# --- the schema --------------------------------------------------------------------------


def test_the_schema_is_valid_json_schema():
    Draft202012Validator.check_schema(SCHEMA)


def test_the_schema_version_matches_the_module():
    assert SCHEMA["properties"]["version"]["const"] == snapshot.VERSION


def test_the_example_validates(validator, base):
    validator.validate(base)


def test_the_element_properties_are_exactly_the_element_descriptor_s():
    """The duplicated descriptor must not drift: same keys, same constraints.

    Descriptions are allowed to differ, because the snapshot keeps short pointers and
    `element.schema.json` stays the normative place for the reasons behind each property.
    """
    mine = SCHEMA["$defs"]["element"]["properties"]
    theirs = ELEMENT_SCHEMA["$defs"]["element"]["properties"]
    assert set(mine) == set(theirs)
    for name in theirs:
        without_description = (
            {k: v for k, v in mine[name].items() if k != "description"},
            {k: v for k, v in theirs[name].items() if k != "description"},
        )
        assert without_description[0] == without_description[1], name


def test_the_descriptor_module_and_the_schema_agree_on_the_property_names():
    from ayna_agent.model import JSON_NAMES

    assert set(JSON_NAMES.values()) == set(SCHEMA["$defs"]["element"]["properties"])


def test_the_feature_version_fits_the_shared_versioned_id_pattern():
    # The healing proposal names the same value, so one must not accept what the other
    # refuses (#149).
    proposal = json.loads(
        (SCHEMAS / "healing-proposal.schema.json").read_text(encoding="utf-8")
    )
    shared = proposal["$defs"]["versionedId"]
    mine = SCHEMA["$defs"]["versionedId"]
    assert {k: v for k, v in mine.items() if k != "description"} == {
        k: v for k, v in shared.items() if k != "description"
    }
    Draft202012Validator(shared).validate(snapshot.FEATURE_VERSION)


# --- the named cases ---------------------------------------------------------------------


def patched(base: dict, patch: list[dict]) -> dict:
    """`base` with an RFC 6902 patch applied; add, remove and replace are enough here."""
    document = copy.deepcopy(base)
    for operation in patch:
        parent, key = _locate(document, operation["path"])
        if isinstance(parent, list):
            index = len(parent) if key == "-" else int(key)
            if operation["op"] == "remove":
                parent.pop(index)
            elif operation["op"] == "add":
                parent.insert(index, operation["value"])
            else:
                parent[index] = operation["value"]
        elif operation["op"] == "remove":
            del parent[key]
        else:
            parent[key] = operation["value"]
    return document


def _locate(document, pointer: str):
    parts = [p.replace("~1", "/").replace("~0", "~") for p in pointer.split("/")[1:]]
    parent = document
    for part in parts[:-1]:
        parent = parent[int(part)] if isinstance(parent, list) else parent[part]
    return parent, parts[-1]


def broken_rules(validator, document) -> set[str]:
    """Every failing keyword, at any level: errors nested under oneOf count too."""
    pending, rules = list(validator.iter_errors(document)), set()
    while pending:
        error = pending.pop()
        rules.add(error.validator)
        pending.extend(error.context or ())
    return rules


@pytest.mark.parametrize("case", CASES["valid"], ids=lambda case: case["name"])
def test_a_named_valid_case_passes_the_schema(validator, base, case):
    validator.validate(patched(base, case["patch"]))


@pytest.mark.parametrize("case", CASES["invalid"], ids=lambda case: case["name"])
def test_a_named_invalid_case_is_refused_by_the_rule_it_names(validator, base, case):
    rules = broken_rules(validator, patched(base, case["patch"]))
    assert rules, "the schema accepted an invalid document"
    assert case["rule"] in rules, sorted(rules)


# --- building a document -----------------------------------------------------------------


def trial_nodes() -> list[dict]:
    return json.loads(TRIAL_TREE.read_text(encoding="utf-8"))


def built(**overrides) -> dict:
    """The example document, rebuilt from the captured trial-app tree (#9, #11)."""
    root = trial_nodes()[0]
    arguments = {
        "window": {
            "handle": root["native_window_handle"],
            "title": root["window_title"],
            "className": root["class_name"],
            "bounds": root["bounds"],
            "dpi": root["dpi"],
        },
        "app": {"exeName": "python.exe", "fileVersion": "3.13.150.1013"},
        "started_at": datetime.fromisoformat("2026-10-31T17:42:19+03:00"),
        "duration_ms": 29,
        "budget_ms": snapshot.DEFAULT_BUDGET_MS,
        "read_errors": 0,
        "snapshot_id": "5e8f0a1b-3c2d-4e6f-8a9b-1c0d2e3f4a5b",
        "agent_version": "0.0.0",
    }
    arguments.update(overrides)
    return snapshot.build(trial_nodes(), **arguments)


def test_the_committed_example_is_what_build_produces(base):
    # Not a round trip: the file other components design against is regenerated here from
    # the real tree, so a change in the agent cannot leave the example behind.
    assert built() == base


def test_the_example_file_is_the_canonical_text(base):
    # Read as bytes, not with `read_text(newline="")`: that keyword is Python 3.13 only and
    # the module supports 3.11, which CI runs. Bytes are also what "identical file" means.
    assert EXAMPLE.read_bytes().decode("utf-8") == snapshot.dumps(base)


def test_elements_are_in_pre_order_with_ids_by_position():
    document = built()
    assert [node["id"] for node in document["elements"]] == [f"e{i}" for i in range(14)]
    assert document["elements"][0]["parentId"] is None
    seen = set()
    for node in document["elements"]:
        assert node["parentId"] is None or node["parentId"] in seen
        seen.add(node["id"])


def test_the_root_element_is_the_window_itself():
    document = built()
    root = document["elements"][0]["element"]
    assert root["controlType"] == "Window"
    assert root["className"] == document["window"]["className"]
    assert root["bounds"] == document["window"]["bounds"]


def test_the_capture_block_records_what_the_walk_cost():
    capture = built()["capture"]
    assert capture["elementCount"] == 14
    assert capture["durationMs"] == 29
    assert capture["budgetMs"] == snapshot.DEFAULT_BUDGET_MS == 5000
    assert capture["featureVersion"] == snapshot.FEATURE_VERSION
    assert capture["startedAt"] == "2026-10-31T17:42:19+03:00"


def test_a_snapshot_id_is_generated_when_none_is_given():
    first, second = built(snapshot_id=None), built(snapshot_id=None)
    assert first["snapshotId"] != second["snapshotId"]


def test_blank_window_and_app_values_are_left_out():
    document = built(
        window={"handle": 657704, "title": "   ", "className": None},
        app={"exeName": "", "fileVersion": None},
    )
    assert document["window"] == {"handle": 657704}
    assert document["app"] == {}


def test_an_unknown_window_key_is_refused():
    with pytest.raises(ValueError, match="processName"):
        built(window={"handle": 1, "processName": "python.exe"})


def test_a_naive_timestamp_is_refused():
    # A screenshot taken just before the walk (#54) is compared with this moment, so an
    # offset is not optional.
    with pytest.raises(ValueError, match="time zone"):
        built(started_at=datetime(2026, 10, 31, 17, 42, 19))


def test_an_aware_timestamp_in_another_zone_keeps_its_offset():
    document = built(started_at=datetime(2026, 10, 31, 14, 42, 19, tzinfo=UTC))
    assert document["capture"]["startedAt"] == "2026-10-31T14:42:19+00:00"


@pytest.mark.parametrize(
    ("name", "nodes", "message"),
    [
        ("no nodes", [], "at least"),
        (
            "a second root",
            [{"id": 0, "parent": None}, {"id": 1, "parent": None}],
            "second root",
        ),
        (
            "a forward reference",
            [{"id": 0, "parent": None}, {"id": 1, "parent": 2}, {"id": 2, "parent": 0}],
            "earlier node",
        ),
        (
            "an id that is not the position",
            [{"id": 0, "parent": None}, {"id": 7, "parent": 0}],
            "expected its position",
        ),
        (
            "an element that is its own parent",
            [{"id": 0, "parent": None}, {"id": 1, "parent": 1}],
            "earlier node",
        ),
    ],
)
def test_a_tree_that_cannot_be_built_in_one_pass_is_refused(name, nodes, message):
    with pytest.raises(ValueError, match=message):
        snapshot.build(
            nodes,
            window={"handle": 1},
            app={},
            started_at=datetime.fromisoformat("2026-10-31T17:42:19+03:00"),
            duration_ms=1,
        )


# --- round trip and canonical form -------------------------------------------------------


def test_load_then_save_gives_the_same_file_back():
    # Acceptance criterion 3 of #12, on the real example rather than on a fixture.
    text = EXAMPLE.read_bytes().decode("utf-8")
    assert snapshot.dumps(snapshot.loads(text)) == text


def test_the_round_trip_survives_a_file_whose_keys_are_in_another_order(tmp_path):
    document = built()
    shuffled = {key: document[key] for key in reversed(list(document))}
    shuffled["capture"] = {
        key: document["capture"][key] for key in reversed(list(document["capture"]))
    }
    path = tmp_path / "snapshot.json"
    path.write_text(json.dumps(shuffled, ensure_ascii=False), encoding="utf-8")
    assert snapshot.read(path) == document


def test_write_uses_lf_even_on_windows(tmp_path):
    path = tmp_path / "snapshot.json"
    snapshot.write(built(), path)
    assert b"\r\n" not in path.read_bytes()
    assert path.read_bytes().endswith(b"\n")


def test_turkish_text_is_not_escaped(tmp_path):
    document = built()
    document["elements"][12]["element"]["name"] = "Giriş"
    path = tmp_path / "snapshot.json"
    snapshot.write(document, path)
    assert "Giriş" in path.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("name", "change", "message"),
    [
        ("another version", {"version": "0.2"}, "version"),
        ("a missing block", {"window": None}, "missing"),
    ],
)
def test_loads_refuses_a_document_it_does_not_speak(name, change, message):
    document = built()
    for key, value in change.items():
        if value is None:
            del document[key]
        else:
            document[key] = value
    with pytest.raises(ValueError, match=message):
        snapshot.loads(json.dumps(document))


def test_loads_refuses_an_element_count_that_disagrees_with_the_list():
    document = built()
    document["capture"]["elementCount"] = 13
    with pytest.raises(ValueError, match="elementCount"):
        snapshot.loads(json.dumps(document))


def test_loads_refuses_a_duplicate_element_id():
    document = built()
    document["elements"][5]["id"] = "e4"
    with pytest.raises(ValueError, match="twice"):
        snapshot.loads(json.dumps(document))


def test_loads_refuses_a_parent_that_comes_later():
    document = built()
    document["elements"][1]["parentId"] = "e9"
    with pytest.raises(ValueError, match="not above it"):
        snapshot.loads(json.dumps(document))


def test_loads_refuses_a_second_root():
    document = built()
    document["elements"][1]["parentId"] = None
    with pytest.raises(ValueError, match="not above it"):
        snapshot.loads(json.dumps(document))


def test_every_element_of_the_example_validates_as_an_element_document(base):
    """A snapshot element must be storable as an element descriptor on its own (#11, #43)."""
    check = Draft202012Validator(ELEMENT_SCHEMA)
    for node in base["elements"]:
        check.validate({"version": "0.1", "element": node["element"]})
