"""Tests for schema_compat.py. Run from the repository root:

python -m unittest discover -s .github/contracts -v
"""

from __future__ import annotations

import copy
import glob
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

import schema_compat as sc

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def doc(version: str = "0.1", **props: object) -> dict:
    """A document schema in the shape of schemas/: a version const and closed objects."""
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "urn:ayna:schema:test",
        "type": "object",
        "required": ["version", "name"],
        "additionalProperties": False,
        "properties": {
            "version": {"const": version},
            "name": {"type": "string", "maxLength": 100},
            "status": {"enum": ["passed", "failed"]},
            "count": {"type": "integer", "minimum": 0},
            **props,
        },
        "$defs": {"row": {"type": "object", "properties": {"index": {"type": "integer"}}}},
    }


def changed(old: dict, version: str, edit) -> dict:
    new = copy.deepcopy(old)
    edit(new)
    _, pointer = sc.version_of(new)
    assert pointer is not None
    target = new
    parts = pointer.lstrip("/").split("/")
    for part in parts[:-1]:
        target = target[part]
    target[parts[-1]] = version
    return new


class CheckTest(unittest.TestCase):
    def errors(self, old, new):
        return sc.check("schemas/x.schema.json", old, new)[0]

    def assertBreaking(self, old, new, fragment):
        errors = self.errors(old, new)
        self.assertTrue(any(fragment in e for e in errors), errors)

    def test_identical_schemas_pass(self):
        self.assertEqual(self.errors(doc(), doc()), [])

    def test_wording_changes_need_no_bump(self):
        new = copy.deepcopy(doc())
        new["description"] = "new words"
        new["properties"]["name"]["title"] = "Name"
        self.assertEqual(self.errors(doc(), new), [])

    def test_a_rule_change_without_a_version_bump_fails(self):
        new = copy.deepcopy(doc())
        new["properties"]["extra"] = {"type": "string"}
        self.assertBreaking(doc(), new, "version is still 0.1")

    def test_a_new_optional_property_is_an_addition(self):
        new = changed(doc(), "0.2", lambda s: s["properties"].update(extra={"type": "string"}))
        self.assertEqual(self.errors(doc(), new), [])

    def test_a_property_called_like_an_annotation_still_counts(self):
        old = doc(title={"type": "string"})
        new = changed(old, "0.2", lambda s: s["properties"].pop("title"))
        self.assertBreaking(old, new, "/properties/title: property removed")

    def test_removing_a_property_breaks(self):
        new = changed(doc(), "0.2", lambda s: s["properties"].pop("count"))
        self.assertBreaking(doc(), new, "/properties/count: property removed")

    def test_a_new_required_property_breaks(self):
        new = changed(doc(), "0.2", lambda s: s["required"].append("count"))
        self.assertBreaking(doc(), new, "newly required: ['count']")

    def test_enum_values_may_be_added_but_not_removed(self):
        added = changed(doc(), "0.2", lambda s: s["properties"]["status"]["enum"].append("notRun"))
        self.assertEqual(self.errors(doc(), added), [])
        removed = changed(doc(), "0.2", lambda s: s["properties"]["status"]["enum"].remove("failed"))
        self.assertBreaking(doc(), removed, "values removed: ['failed']")

    def test_types_may_widen_but_not_narrow(self):
        wider = changed(doc(), "0.2", lambda s: s["properties"]["count"].update(type="number"))
        self.assertEqual(self.errors(doc(), wider), [])
        nullable = changed(doc(), "0.2", lambda s: s["properties"]["name"].update(type=["string", "null"]))
        self.assertEqual(self.errors(doc(), nullable), [])
        narrower = changed(wider, "0.3", lambda s: s["properties"]["count"].update(type="integer"))
        self.assertBreaking(wider, narrower, "no longer accepts ['number']")

    def test_bounds_may_loosen_but_not_tighten(self):
        looser = changed(doc(), "0.2", lambda s: s["properties"]["name"].update(maxLength=200))
        self.assertEqual(self.errors(doc(), looser), [])
        tighter = changed(doc(), "0.2", lambda s: s["properties"]["name"].update(maxLength=50))
        self.assertBreaking(doc(), tighter, "maxLength: lowered to 50")
        raised = changed(doc(), "0.2", lambda s: s["properties"]["count"].update(minimum=1))
        self.assertBreaking(doc(), raised, "minimum: raised to 1")

    def test_a_new_pattern_breaks(self):
        new = changed(doc(), "0.2", lambda s: s["properties"]["name"].update(pattern="^[a-z]+$"))
        self.assertBreaking(doc(), new, "pattern")

    def test_closing_an_open_object_breaks(self):
        new = changed(doc(), "0.2", lambda s: s["$defs"]["row"].update(additionalProperties=False))
        self.assertBreaking(doc(), new, "/$defs/row/additionalProperties: now refuses every value")

    def test_a_typed_property_in_an_open_object_breaks(self):
        # The open object took any value under this name before.
        new = changed(
            doc(), "0.2", lambda s: s["$defs"]["row"]["properties"].update(value={"type": "string"})
        )
        self.assertBreaking(doc(), new, "/$defs/row/properties/value: was unconstrained")

    def test_removing_a_definition_breaks(self):
        new = changed(doc(), "0.2", lambda s: s["$defs"].pop("row"))
        self.assertBreaking(doc(), new, "/$defs/row: definition removed")

    def test_branches_may_be_added_but_not_removed(self):
        old = doc(target={"oneOf": [{"type": "string"}, {"type": "integer"}]})
        added = changed(old, "0.2", lambda s: s["properties"]["target"]["oneOf"].append({"type": "null"}))
        self.assertEqual(self.errors(old, added), [])
        removed = changed(old, "0.2", lambda s: s["properties"]["target"]["oneOf"].pop())
        self.assertBreaking(old, removed, "a branch was removed")

    def test_a_changed_reference_is_followed(self):
        old = doc(row={"$ref": "#/$defs/row"})

        def edit(s):
            s["$defs"]["row2"] = {"type": "string"}
            s["properties"]["row"]["$ref"] = "#/$defs/row2"

        self.assertBreaking(
            old, changed(old, "0.2", edit), "/properties/row/type: no longer accepts ['object']"
        )

    def test_moving_rules_into_a_definition_is_no_change(self):
        new = changed(
            doc(),
            "0.2",
            lambda s: (
                s["$defs"].update(name={"type": "string", "maxLength": 100}),
                s["properties"].update(name={"description": "now shared", "$ref": "#/$defs/name"}),
            ),
        )
        self.assertEqual(self.errors(doc(), new), [])
        tighter = changed(new, "0.3", lambda s: s["$defs"]["name"].update(maxLength=10))
        self.assertBreaking(new, tighter, "/$defs/name/maxLength: lowered to 10")

    def keyword_rules(self, *entries):
        """A step-like schema: rules per keyword as allOf if/then entries."""
        return doc(
            keyword={"enum": ["Click", "Type"]},
            value={"type": "string"},
        ) | {"allOf": list(entries)}

    def test_a_rule_for_a_new_keyword_is_an_addition(self):
        old = self.keyword_rules(
            {"if": {"properties": {"keyword": {"const": "Type"}}}, "then": {"required": ["value"]}}
        )

        def edit(s):
            s["properties"]["keyword"]["enum"].append("SelectRow")
            s["properties"]["row"] = {"type": "integer"}
            s["allOf"].append(
                {"if": {"properties": {"keyword": {"const": "SelectRow"}}}, "then": {"required": ["row"]}}
            )
            s["allOf"].append(
                {
                    "if": {"properties": {"keyword": {"enum": ["Click", "Type"]}}},
                    "then": {"properties": {"row": False}},
                }
            )
            s["allOf"][0]["if"]["properties"]["keyword"] = {"enum": ["Type", "SelectRow"]}

        self.assertEqual(self.errors(old, changed(old, "0.2", edit)), [])

    def test_a_new_rule_for_an_old_keyword_breaks(self):
        old = self.keyword_rules(
            {"if": {"properties": {"keyword": {"const": "Type"}}}, "then": {"required": ["value"]}}
        )
        new = changed(
            old,
            "0.2",
            lambda s: s["allOf"].append(
                {
                    "if": {"properties": {"keyword": {"const": "Click"}}},
                    "then": {"properties": {"value": False}},
                }
            ),
        )
        self.assertBreaking(old, new, "/allOf/1: a schema was added")

    def test_a_rule_that_now_fires_on_an_old_keyword_breaks(self):
        old = self.keyword_rules(
            {"if": {"properties": {"keyword": {"const": "Type"}}}, "then": {"required": ["value"]}}
        )
        new = changed(
            old,
            "0.2",
            lambda s: s["allOf"][0]["if"]["properties"].update(keyword={"enum": ["Type", "Click"]}),
        )
        self.assertBreaking(old, new, "/allOf/0")

    def test_a_tighter_rule_for_an_old_keyword_breaks(self):
        old = self.keyword_rules(
            {
                "if": {"properties": {"keyword": {"const": "Type"}}},
                "then": {"properties": {"value": {"maxLength": 100}}},
            }
        )
        new = changed(
            old,
            "0.2",
            lambda s: (
                s["properties"]["keyword"]["enum"].append("Select"),
                s["allOf"][0]["if"]["properties"].update(keyword={"enum": ["Type", "Select"]}),
                s["allOf"][0]["then"]["properties"]["value"].update(maxLength=10),
            ),
        )
        self.assertBreaking(old, new, "/allOf/0/then/properties/value/maxLength: lowered to 10")

    def test_a_keyword_the_check_cannot_read_fails_closed(self):
        new = changed(
            doc(),
            "0.2",
            lambda s: s.update({"if": {"required": ["count"]}, "then": {"required": ["status"]}}),
        )
        self.assertBreaking(doc(), new, "`if` changed")

    def test_a_major_version_allows_a_breaking_change(self):
        new = changed(doc(), "1.0", lambda s: s["properties"].pop("count"))
        errors, notes = sc.check("schemas/x.schema.json", doc(), new)
        self.assertEqual(errors, [])
        self.assertTrue(any("breaking change allowed" in n for n in notes), notes)

    def test_the_version_may_not_go_down(self):
        self.assertBreaking(
            doc("0.2"), changed(doc("0.2"), "0.1", lambda s: s["properties"].pop("count")), "went down"
        )

    def test_message_contracts_keep_their_version_under_defs(self):
        old = {
            "$defs": {"version": {"const": "1.0"}, "ping": {"type": "object", "additionalProperties": False}}
        }
        new = changed(old, "1.1", lambda s: s["$defs"]["ping"].update(properties={"x": {"type": "string"}}))
        self.assertEqual(self.errors(old, new), [])
        broke = changed(old, "1.1", lambda s: s["$defs"].pop("ping"))
        self.assertBreaking(old, broke, "definition removed")

    def test_new_and_deleted_files(self):
        self.assertEqual(
            sc.check("schemas/x.schema.json", None, doc()),
            ([], ["schemas/x.schema.json: new contract, nothing to compare"]),
        )
        self.assertBreaking(doc(), None, "deleted")

    def test_a_schema_without_a_version_fails(self):
        self.assertBreaking(doc(), {"type": "object"}, "no version")


class RepositorySchemasTest(unittest.TestCase):
    """The real contracts: each names its version and passes against itself."""

    def test_every_schema_names_its_version(self):
        files = sorted(glob.glob(os.path.join(ROOT, "schemas", "*.schema.json")))
        self.assertGreaterEqual(len(files), 6)
        for path in files:
            with open(path, encoding="utf-8") as f:
                schema = json.load(f)
            version, _ = sc.version_of(schema)
            self.assertIsNotNone(version, path)
            self.assertEqual(sc.check(path, schema, copy.deepcopy(schema)), ([], []), path)


if __name__ == "__main__":
    unittest.main()
