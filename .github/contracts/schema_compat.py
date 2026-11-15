"""Breaking-change check for the JSON Schemas in schemas/ (#52, ADR contracts-v1-freeze).

Compares every schema file with its version at a base git ref and fails when a change could
break a party that was built against the old version:

- a document or message the old schema accepted is now refused (a property, `$defs` entry,
  `oneOf`/`anyOf` branch or enum value removed; a new required property; a narrower type,
  bound or pattern; `additionalProperties` closed), or
- a property or definition the old schema promised is gone, so a reader that used it breaks.

Additions are allowed: a new optional property, `$defs` entry, enum value or branch. Readers
must ignore what they do not know (tolerant reader, see the ADR).

A breaking change passes only together with a new major version (the first number of the
version: 0.2 -> 1.0, 1.3 -> 2.0). Every other change to a schema's rules needs a version
bump too (schemas/AGENTS.md); changes to annotations alone (title, description, examples, ...)
do not.

The version is the `const` at /properties/version (documents such as the step schema) or at
/$defs/version (message contracts such as ws-runs and agent-rpc).

What the check cannot classify is reported as breaking, so it fails closed.

Usage: python .github/contracts/schema_compat.py --base <git ref> [schema files...]
       (default files: schemas/*.schema.json). Standard library only.
"""

from __future__ import annotations

import argparse
import glob
import json
import subprocess
import sys
from collections.abc import Iterator
from typing import Any

ANNOTATIONS = frozenset(
    {
        "title",
        "description",
        "$comment",
        "examples",
        "default",
        "deprecated",
        "readOnly",
        "writeOnly",
    }
)

VERSION_POINTERS = ("/properties/version/const", "/$defs/version/const")

# Lower bounds: raising or adding one narrows. Upper bounds: lowering or adding one narrows.
LOWER_BOUNDS = ("minimum", "exclusiveMinimum", "minLength", "minItems", "minProperties")
UPPER_BOUNDS = ("maximum", "exclusiveMaximum", "maxLength", "maxItems", "maxProperties")

HANDLED = frozenset(
    {
        "$schema",
        "$id",
        "$ref",
        "$defs",
        "type",
        "enum",
        "const",
        "required",
        "properties",
        "additionalProperties",
        "items",
        "prefixItems",
        "oneOf",
        "anyOf",
        "allOf",
        "pattern",
        "format",
        "uniqueItems",
        *LOWER_BOUNDS,
        *UPPER_BOUNDS,
    }
)


def pointer_get(doc: Any, pointer: str) -> Any:
    node = doc
    for raw in pointer.lstrip("/").split("/"):
        part = raw.replace("~1", "/").replace("~0", "~")
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def version_of(schema: Any) -> tuple[str | None, str | None]:
    """(version, pointer) of a schema, or (None, None) if it names none."""
    for pointer in VERSION_POINTERS:
        value = pointer_get(schema, pointer)
        if isinstance(value, str):
            return value, pointer
    return None, None


def parse(version: str) -> tuple[int, ...]:
    """ "1.10" -> (1, 10); a part that is not a number counts as -1."""
    return tuple(int(p) if p.isdigit() else -1 for p in version.lstrip("vV").split("."))


def major(version: str) -> int:
    return parse(version)[0]


def strip_annotations(node: Any) -> Any:
    """The schema without annotation keywords, to tell a rule change from a wording change.

    Annotation names are only dropped where they are keywords, never as property names in
    `properties` or `$defs`, so a property called `title` still counts.
    """
    if isinstance(node, list):
        return [strip_annotations(item) for item in node]
    if not isinstance(node, dict):
        return node
    out = {}
    for key, value in node.items():
        if key in ANNOTATIONS:
            continue
        if key in ("const", "enum"):
            out[key] = value  # values, not schemas: compared as they are
        elif key in ("properties", "$defs") and isinstance(value, dict):
            out[key] = {name: strip_annotations(sub) for name, sub in value.items()}
        else:
            out[key] = strip_annotations(value)
    return out


def type_set(schema: dict[str, Any]) -> set[str] | None:
    value = schema.get("type")
    if value is None:
        return None
    return {value} if isinstance(value, str) else set(value)


class Comparer:
    """Walks an old and a new schema side by side and collects breaking changes."""

    def __init__(self, old_root: Any, new_root: Any, skip: str | None) -> None:
        self.old_root = old_root
        self.new_root = new_root
        self.skip = skip  # the version const's pointer: it is expected to change
        self.found: list[str] = []
        self._refs_seen: set[tuple[str, str]] = set()

    def report(self, path: str, message: str) -> None:
        self.found.append(f"{path or '/'}: {message}")

    def resolve(self, root: Any, ref: str) -> Any:
        if not ref.startswith("#"):
            return None
        return pointer_get(root, ref[1:]) if ref != "#" else root

    def compare(self, old: Any, new: Any, path: str) -> None:
        if old is True or old == {}:
            if not (new is True or new == {}):
                if new is False:
                    self.report(path, "now refuses every value")
                elif isinstance(new, dict) and strip_annotations(new) != {}:
                    self.report(path, "was unconstrained and now has rules")
            return
        if old is False:
            return  # nothing was valid, so nothing can break
        if new is False:
            self.report(path, "now refuses every value")
            return
        if new is True or new == {}:
            return  # widened to anything
        if not isinstance(old, dict) or not isinstance(new, dict):
            if old != new:
                self.report(path, "changed in a way this check cannot read")
            return
        if old.get("$ref") != new.get("$ref"):
            # Different references (or one side inline): compare what they stand for. The same
            # reference on both sides is compared once, under $defs.
            pair = (old.get("$ref"), new.get("$ref"), path)
            if pair in self._refs_seen:
                return
            self._refs_seen.add(pair)
            old_inline, new_inline = self.inline(old, self.old_root), self.inline(new, self.new_root)
            if old_inline is None or new_inline is None:
                self.report(f"{path}/$ref", f"changed from {old.get('$ref')} to {new.get('$ref')}")
                return
            old, new = old_inline, new_inline

        for key in sorted(set(old) | set(new)):
            if key in ANNOTATIONS:
                continue
            sub = f"{path}/{key}"
            if key not in HANDLED:
                if strip_annotations(old.get(key)) != strip_annotations(new.get(key)):
                    self.report(sub, f"`{key}` changed; this check cannot tell if that is compatible")
                continue

        self._compare_types(old, new, path)
        self._compare_values(old, new, path)
        self._compare_bounds(old, new, path)
        self._compare_objects(old, new, path)
        self._compare_arrays(old, new, path)
        self._compare_combinators(old, new, path)
        self._compare_defs(old, new, path)

    def inline(self, node: dict, root: Any, depth: int = 0) -> dict | None:
        """`node` with its local `$ref` replaced by the definition, or None if that is unclear."""
        if "$ref" not in node:
            return node
        target = self.resolve(root, node["$ref"])
        if not isinstance(target, dict) or depth > 20:
            return None
        target = self.inline(target, root, depth + 1)
        if target is None:
            return None
        siblings = {k: v for k, v in node.items() if k != "$ref"}
        for key, value in siblings.items():
            if key not in ANNOTATIONS and key in target and target[key] != value:
                return None  # both constrain the same keyword: an intersection this check does not compute
        return {**target, **siblings}

    def _compare_types(self, old: dict, new: dict, path: str) -> None:
        old_types, new_types = type_set(old), type_set(new)
        if new_types is None:
            return
        if old_types is None:
            self.report(f"{path}/type", f"now must be {sorted(new_types)}")
            return
        lost = {t for t in old_types if t not in new_types and not (t == "integer" and "number" in new_types)}
        if lost:
            self.report(f"{path}/type", f"no longer accepts {sorted(lost)}")

    def _compare_values(self, old: dict, new: dict, path: str) -> None:
        if "enum" in new:
            if "enum" not in old:
                self.report(f"{path}/enum", "now limited to a list of values")
            else:
                removed = [v for v in old["enum"] if v not in new["enum"]]
                if removed:
                    self.report(f"{path}/enum", f"values removed: {removed}")
        if "const" in new and f"{path}/const" != self.skip:
            if "const" not in old:
                self.report(f"{path}/const", f"now must be {new['const']!r}")
            elif old["const"] != new["const"]:
                self.report(f"{path}/const", f"changed from {old['const']!r} to {new['const']!r}")
        for key in ("pattern", "format"):
            if key in new and old.get(key) != new[key]:
                was = f"from {old[key]!r} " if key in old else ""
                self.report(f"{path}/{key}", f"changed {was}to {new[key]!r}")
        if new.get("uniqueItems") is True and old.get("uniqueItems") is not True:
            self.report(f"{path}/uniqueItems", "items must now be unique")
        for key in ("$schema", "$id"):
            if key in old and old.get(key) != new.get(key):
                self.report(f"{path}/{key}", f"changed from {old[key]!r} to {new.get(key)!r}")

    def _compare_bounds(self, old: dict, new: dict, path: str) -> None:
        for key in LOWER_BOUNDS:
            if key in new and (key not in old or new[key] > old[key]):
                self.report(f"{path}/{key}", f"raised to {new[key]}")
        for key in UPPER_BOUNDS:
            if key in new and (key not in old or new[key] < old[key]):
                self.report(f"{path}/{key}", f"lowered to {new[key]}")

    def _compare_objects(self, old: dict, new: dict, path: str) -> None:
        added_required = sorted(set(new.get("required", [])) - set(old.get("required", [])))
        if added_required:
            self.report(f"{path}/required", f"newly required: {added_required}")
        old_props = old.get("properties", {})
        new_props = new.get("properties", {})
        old_extra = old.get("additionalProperties", True)
        new_extra = new.get("additionalProperties", True)
        for name, old_sub in old_props.items():
            sub = f"{path}/properties/{name}"
            if name not in new_props:
                self.report(sub, "property removed")
            else:
                self.compare(old_sub, new_props[name], sub)
        for name in new_props.keys() - old_props.keys():
            # A new property was covered by additionalProperties before.
            self.compare(old_extra, new_props[name], f"{path}/properties/{name}")
        if "additionalProperties" in old or "additionalProperties" in new:
            self.compare(old_extra, new_extra, f"{path}/additionalProperties")

    def _compare_arrays(self, old: dict, new: dict, path: str) -> None:
        if "items" in old or "items" in new:
            self.compare(old.get("items", True), new.get("items", True), f"{path}/items")
        old_prefix, new_prefix = old.get("prefixItems", []), new.get("prefixItems", [])
        if len(old_prefix) != len(new_prefix):
            self.report(f"{path}/prefixItems", "number of positional items changed")
        for i, (a, b) in enumerate(zip(old_prefix, new_prefix, strict=False)):
            self.compare(a, b, f"{path}/prefixItems/{i}")

    def _compare_combinators(self, old: dict, new: dict, path: str) -> None:
        for key in ("oneOf", "anyOf"):
            if key not in old and key not in new:
                continue
            if key not in old:
                self.report(f"{path}/{key}", "now must match one of a list of schemas")
                continue
            old_list, new_list = old[key], new.get(key, [])
            if key not in new:
                continue  # dropped: wider
            if len(new_list) < len(old_list):
                self.report(f"{path}/{key}", "a branch was removed")
            for i, (a, b) in enumerate(zip(old_list, new_list, strict=False)):
                self.compare(a, b, f"{path}/{key}/{i}")
        old_all, new_all = old.get("allOf", []), new.get("allOf", [])
        for i, (a, b) in enumerate(zip(old_all, new_all, strict=False)):
            sub = f"{path}/allOf/{i}"
            if not self._conditional_still_fits(a, b, old, sub):
                self.compare(a, b, sub)
        for i in range(len(old_all), len(new_all)):
            if not self._never_applies_to_old(new_all[i], old):
                self.report(f"{path}/allOf/{i}", "a schema was added that every value must match")

    # The step schema states its per-keyword rules as `allOf` entries of the form
    # {"if": {"properties": {"keyword": {"const": "SelectRow"}}}, "then": {...}}. Such an entry
    # is harmless to old documents when it can only fire on values the old schema refused, or
    # when it only constrains properties the old schema did not allow at all.

    def accepted_values(self, schema: dict, name: str) -> list | None:
        """The values the old schema allows for property `name`, if it lists them."""
        prop = schema.get("properties", {}).get(name)
        if isinstance(prop, dict):
            prop = self.inline(prop, self.old_root)
        if not isinstance(prop, dict):
            return None
        if "const" in prop:
            return [prop["const"]]
        return prop.get("enum")

    def condition_values(self, condition: Any) -> dict[str, list] | None:
        """{property: values} of an `if` that only tests properties against const/enum values."""
        if not isinstance(condition, dict):
            return None
        rest = set(strip_annotations(condition)) - {"properties", "required"}
        props = condition.get("properties")
        if rest or not isinstance(props, dict) or not props:
            return None
        out = {}
        for name, test in props.items():
            if not isinstance(test, dict) or set(strip_annotations(test)) - {"const", "enum"}:
                return None
            out[name] = [test["const"]] if "const" in test else list(test.get("enum", []))
        return out

    def _never_applies_to_old(self, entry: Any, old: dict) -> bool:
        if not isinstance(entry, dict) or set(strip_annotations(entry)) - {"if", "then"}:
            return False
        tested = self.condition_values(entry.get("if"))
        if tested:
            for name, values in tested.items():
                allowed = self.accepted_values(old, name)
                if allowed is not None and not any(v in allowed for v in values):
                    return True  # fires only on values the old schema refused
        then = entry.get("then")
        if isinstance(then, dict) and set(strip_annotations(then)) <= {"properties"}:
            unknown = set(then.get("properties", {})) - set(old.get("properties", {}))
            if unknown == set(then.get("properties", {})) and old.get("additionalProperties") is False:
                return True  # constrains only properties the old schema did not allow
        return False

    def _conditional_still_fits(self, a: Any, b: Any, old: dict, path: str) -> bool:
        """True when an if/then entry only fires on more values, all of them refused before."""
        if not isinstance(a, dict) or not isinstance(b, dict):
            return False
        keys = set(strip_annotations(a)) | set(strip_annotations(b))
        if keys - {"if", "then"} or strip_annotations(a.get("if")) == strip_annotations(b.get("if")):
            return False
        old_test, new_test = self.condition_values(a.get("if")), self.condition_values(b.get("if"))
        if not old_test or not new_test or old_test.keys() != new_test.keys():
            return False
        if a.get("if", {}).get("required") != b.get("if", {}).get("required"):
            return False
        for name in new_test:
            added = [v for v in new_test[name] if v not in old_test[name]]
            allowed = self.accepted_values(old, name)
            if added and (allowed is None or any(v in allowed for v in added)):
                return False
        self.compare(a.get("then", True), b.get("then", True), f"{path}/then")
        return True

    def _compare_defs(self, old: dict, new: dict, path: str) -> None:
        old_defs, new_defs = old.get("$defs", {}), new.get("$defs", {})
        for name, old_sub in old_defs.items():
            sub = f"{path}/$defs/{name}"
            if name not in new_defs:
                self.report(sub, "definition removed")
            else:
                self.compare(old_sub, new_defs[name], sub)


def breaking_changes(old: Any, new: Any) -> list[str]:
    _, pointer = version_of(new)
    comparer = Comparer(old, new, pointer)
    comparer.compare(old, new, "")
    return comparer.found


def check(path: str, old: Any | None, new: Any | None) -> tuple[list[str], list[str]]:
    """(errors, notes) for one schema file. `old` None: new file; `new` None: deleted."""
    if old is None:
        return [], [f"{path}: new contract, nothing to compare"]
    if new is None:
        return [f"{path}: the schema was deleted"], []
    old_version, _ = version_of(old)
    new_version, _ = version_of(new)
    if new_version is None:
        return [f"{path}: no version (const at {' or '.join(VERSION_POINTERS)})"], []
    if strip_annotations(old) == strip_annotations(new):
        return [], []
    if old_version == new_version:
        return [
            (
                f"{path}: the rules changed but the version is still {new_version}; "
                "bump it (minor for additions, major for a breaking change) and write the ADR"
            )
        ], []
    if old_version is not None and parse(new_version) < parse(old_version):
        return [f"{path}: version went down from {old_version} to {new_version}"], []
    found = breaking_changes(old, new)
    if old_version is not None and major(new_version) > major(old_version):
        return [], [
            f"{path}: major version {old_version} -> {new_version}, breaking change allowed: {item}"
            for item in found
        ]
    return [f"{path}: breaking change in {old_version} -> {new_version}: {item}" for item in found], []


def read_at(ref: str, path: str) -> Any | None:
    result = subprocess.run(
        ["git", "show", f"{ref}:{path}"], check=False, capture_output=True, text=True, encoding="utf-8"
    )
    if result.returncode != 0:
        return None
    return json.loads(result.stdout)


def read_file(path: str) -> Any | None:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def base_files(ref: str) -> Iterator[str]:
    result = subprocess.run(
        ["git", "ls-tree", "--name-only", f"{ref}", "schemas/"],
        capture_output=True,
        text=True,
        check=True,
    )
    for name in result.stdout.split():
        if name.endswith(".schema.json"):
            yield name


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--base", required=True, help="git ref to compare with, e.g. origin/main")
    parser.add_argument("files", nargs="*")
    args = parser.parse_args(argv)
    files = args.files or sorted(set(glob.glob("schemas/*.schema.json")) | set(base_files(args.base)))
    errors: list[str] = []
    for path in files:
        found, notes = check(path, read_at(args.base, path), read_file(path))
        errors += found
        for note in notes:
            print(note)
    for error in errors:
        file = error.split(":", 1)[0]
        print(f"::error file={file}::{error}")
    if not errors:
        print(f"schemas: no breaking change against {args.base} ({len(files)} files)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
