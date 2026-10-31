"""Checks the Turkish NL dataset in eval/nl/ (#36).

Every line of `pairs.jsonl` (and of `heldout.jsonl` once #57 freezes it) must
be a pair record (`pair.schema.json`) whose gold steps validate against
`schemas/step.schema.json` and target objects of the app version the pair was
written for (`objects/<app>.json`, `objects.schema.json`). On top of the
schemas it checks what a schema cannot:

- ids and texts are unique, and an id starts with its app code;
- each keyword and checkpoint property fits the target's control type;
- a Select value is one of the target's items, when the object lists them;
- every Type/Select value and text checkpoint appears in the text, and in a
  team pair at least once with no letter or digit glued to it (no suffix
  dropped from a bare value; quote it or use an apostrophe);
- a pair that clicks a check box states the assumed start state in `notes`
  (Click toggles);
- the scenario-type rules (checkpoint: only Verify; wait: has a Wait);
- the variants of one scenario share app, type and gold steps, and a scenario
  never sits on both sides of the held-out split;
- the held-out file matches its recorded SHA-256 (`heldout.sha256`);
- each scenario type of an app has at least `--min-styles` phrasing styles.

Rules behind every check: guideline.md. Needs only `jsonschema` (the ai/
module's dependency). From the repository root:

    ai/.venv/bin/python eval/nl/check_pairs.py
    ai/.venv/bin/python eval/nl/check_pairs.py --min-styles 0   # set still growing
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

HERE = Path(__file__).resolve().parent
STEP_SCHEMA_PATH = HERE.parents[1] / "schemas" / "step.schema.json"
PAIRS, HELDOUT, HELDOUT_SHA = "pairs.jsonl", "heldout.jsonl", "heldout.sha256"
MIN_STYLES = 3

# Control types a keyword or checkpoint property can act on (guideline 6.3).
# Keywords and properties not listed here fit every control type.
KEYWORD_CONTROLS = {
    "Type": {"Edit", "ComboBox", "Document"},
    "Select": {"ComboBox", "List"},
}
PROPERTY_CONTROLS = {
    "value": {"Edit", "ComboBox", "Document"},
    "checked": {"CheckBox"},
    "selected": {"RadioButton", "ListItem", "TabItem", "DataItem"},
}
ITEM_CONTROLS = {"ComboBox", "List"}
# A Click toggles a check box, so the pair must say what it toggled from
# (guideline 6.8): "start state: unchecked", optionally naming the box.
START_STATE = re.compile(r"\bstart state\b[^;\n]*?\b(?:un)?checked\b", re.IGNORECASE)


@dataclass(frozen=True)
class Problem:
    where: str
    code: str
    message: str

    def __str__(self) -> str:
        return f"{self.where}: [{self.code}] {self.message}"


@dataclass
class Pair:
    file: str
    line: int
    record: dict
    valid: bool = False  # passed pair.schema.json

    @property
    def where(self) -> str:
        return f"{self.file}:{self.line}"


@dataclass
class Report:
    pairs: list[Pair] = field(default_factory=list)
    objects: dict[str, dict] = field(default_factory=dict)  # app -> objects file
    problems: list[Problem] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems

    def add(self, where: str, code: str, message: str) -> None:
        self.problems.append(Problem(where, code, message))


def fold(text: str) -> str:
    """Lower-case, without diacritics (ç→c, ı/İ→i, ş→s …), single spaces.

    Used only to find a value in the text, so "sifre" and "Şifre" match.
    """
    decomposed = unicodedata.normalize("NFKD", text.lower().replace("ı", "i"))
    plain = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(plain.split())


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _validators(step_schema: Path) -> tuple[Draft202012Validator, Draft202012Validator]:
    step = _load_json(step_schema)
    registry = Registry().with_resource(step["$id"], Resource.from_contents(step))
    pair = Draft202012Validator(
        _load_json(HERE / "pair.schema.json"), registry=registry
    )
    objects = Draft202012Validator(_load_json(HERE / "objects.schema.json"))
    return pair, objects


def _schema_problems(validator: Draft202012Validator, instance) -> list[str]:
    errors = sorted(validator.iter_errors(instance), key=lambda e: e.json_path)
    return [f"{error.json_path}: {error.message}" for error in errors]


def check_dataset(
    data_dir: Path, min_styles: int = MIN_STYLES, step_schema: Path = STEP_SCHEMA_PATH
) -> Report:
    """Check pairs.jsonl, heldout.jsonl (if any) and objects/*.json in data_dir."""
    report = Report()
    pair_validator, objects_validator = _validators(step_schema)
    if not (data_dir / PAIRS).exists():
        report.add(PAIRS, "missing-file", f"{data_dir / PAIRS} does not exist")
    for name in (PAIRS, HELDOUT):
        if (data_dir / name).exists():
            _load_pairs(data_dir / name, pair_validator, report)
    _check_heldout_hash(data_dir, report)
    for path in sorted((data_dir / "objects").glob("*.json")):
        _load_objects(path, objects_validator, report)

    valid = [pair for pair in report.pairs if pair.valid]
    for app in sorted({pair.record["app"] for pair in valid} - report.objects.keys()):
        report.add(f"objects/{app}.json", "missing-objects", "missing or invalid")
    for pair in valid:
        _check_pair(pair, report)
    _check_unique(valid, report)
    _check_scenarios(valid, report)
    _check_styles(valid, min_styles, report)
    return report


def _load_pairs(path: Path, validator: Draft202012Validator, report: Report) -> None:
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        where = f"{path.name}:{number}"
        if not line.strip():
            report.add(where, "blank-line", "JSON lines files have no blank lines")
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            report.add(where, "invalid-json", str(exc))
            continue
        messages = _schema_problems(validator, record)
        for message in messages:
            report.add(where, "schema", message)
        report.pairs.append(Pair(path.name, number, record, valid=not messages))


def _load_objects(path: Path, validator: Draft202012Validator, report: Report) -> None:
    where = f"objects/{path.name}"
    try:
        data = _load_json(path)
    except json.JSONDecodeError as exc:
        report.add(where, "invalid-json", str(exc))
        return
    messages = _schema_problems(validator, data)
    for message in messages:
        report.add(where, "schema", message)
    if messages:
        return
    if data["app"] != path.stem:
        report.add(where, "app-mismatch", f"app {data['app']!r} != file name")
    seen: dict[str, str] = {}
    for name, obj in data["objects"].items():
        if "items" in obj and obj["controlType"] not in ITEM_CONTROLS:
            report.add(where, "items", f"{name}: only ComboBox and List have items")
        first = seen.setdefault(obj["automationId"], name)
        if first != name:
            report.add(
                where,
                "duplicate-object",
                f"{name} and {first} have the same automationId",
            )
    report.objects[path.stem] = data


def _check_heldout_hash(data_dir: Path, report: Report) -> None:
    heldout, sha_file = data_dir / HELDOUT, data_dir / HELDOUT_SHA
    if not sha_file.exists():
        if heldout.exists():
            report.add(
                HELDOUT,
                "not-frozen",
                f"record its SHA-256 in {HELDOUT_SHA} in the same commit (#57)",
            )
        return
    if not heldout.exists():
        report.add(HELDOUT_SHA, "missing-file", f"{HELDOUT} is missing")
        return
    recorded = (sha_file.read_text(encoding="utf-8").split() or [""])[0]
    actual = hashlib.sha256(heldout.read_bytes()).hexdigest()
    if recorded != actual:
        report.add(
            HELDOUT,
            "heldout-changed",
            f"SHA-256 {actual} != recorded {recorded}: the frozen split was edited",
        )


def _literals(step: dict) -> Iterable[str]:
    """Texts of a step that the description must contain."""
    if step["keyword"] in ("Type", "Select") and step["value"]:
        yield step["value"]
    if step["keyword"] == "Verify":
        expected = step["checkpoint"]["expected"]
        if isinstance(expected, str) and expected:
            yield expected


def _stands_alone(literal: str, text: str) -> bool:
    """True if `literal` occurs in `text` with no letter or digit glued to it.

    Both are folded. Only an end of `literal` that is itself a letter or digit
    needs a boundary: "Welcome, admin!" may be followed by anything.
    """
    start = text.find(literal)
    while start != -1:
        end = start + len(literal)
        before = text[start - 1] if start else ""
        after = text[end] if end < len(text) else ""
        glued = (literal[0].isalnum() and before.isalnum()) or (
            literal[-1].isalnum() and after.isalnum()
        )
        if not glued:
            return True
        start = text.find(literal, start + 1)
    return False


def _check_pair(pair: Pair, report: Report) -> None:
    record, where = pair.record, pair.where
    app = record["app"]
    if not record["id"].startswith(f"{app}-"):
        report.add(where, "id-app", f"id {record['id']!r} must start with {app}-")
    steps = record["gold"]["steps"]
    keywords = [step["keyword"] for step in steps]
    kind = record["scenarioType"]
    if kind == "checkpoint" and set(keywords) != {"Verify"}:
        report.add(where, "type-rule", "a checkpoint pair has only Verify steps")
    if kind != "checkpoint" and set(keywords) == {"Verify"}:
        report.add(where, "type-rule", "only Verify steps: use scenarioType checkpoint")
    if kind == "wait" and "Wait" not in keywords:
        report.add(where, "type-rule", "a wait pair has a Wait step")
    if kind not in ("wait", "checkpoint") and "Wait" in keywords:
        report.add(where, "type-rule", "a pair with a Wait step is scenarioType wait")

    text = fold(record["text"])
    team = record["origin"] == "team"
    for i, step in enumerate(steps):
        at = f"gold.steps[{i}]"
        for literal in _literals(step):
            folded = fold(literal)
            if folded not in text:
                report.add(where, "ungrounded", f"{at}: {literal!r} is not in the text")
            elif team and not _stands_alone(folded, text):
                report.add(
                    where,
                    "bare-suffix",
                    f"{at}: {literal!r} is in the text only with letters attached; "
                    "a team pair quotes the value or puts a suffix after an "
                    "apostrophe (4.4)",
                )

    objects = report.objects.get(app)
    if objects is None:  # reported once per app
        return
    if record["appVersion"] != objects["appVersion"]:
        report.add(
            where,
            "app-version",
            f"appVersion {record['appVersion']!r} != objects/{app}.json "
            f"{objects['appVersion']!r}",
        )
    for i, step in enumerate(steps):
        at = f"gold.steps[{i}]"
        obj = objects["objects"].get(step["target"])
        if obj is None:
            report.add(
                where,
                "unknown-target",
                f"{at}: {step['target']} is not in objects/{app}.json",
            )
            continue
        control, keyword = obj["controlType"], step["keyword"]
        allowed = KEYWORD_CONTROLS.get(keyword)
        if allowed and control not in allowed:
            report.add(where, "control-type", f"{at}: {keyword} on a {control}")
        if (
            keyword == "Click"
            and control == "CheckBox"
            and not START_STATE.search(record.get("notes", ""))
        ):
            report.add(
                where,
                "start-state",
                f"{at}: Click toggles {step['target']}; give the assumed start "
                "state in notes, e.g. 'start state: unchecked' (6.8)",
            )
        if keyword == "Verify":
            prop = step["checkpoint"]["property"]
            allowed = PROPERTY_CONTROLS.get(prop)
            if allowed and control not in allowed:
                report.add(
                    where, "control-type", f"{at}: property {prop} on a {control}"
                )
        if keyword == "Select" and "items" in obj and step["value"] not in obj["items"]:
            report.add(
                where,
                "unknown-item",
                f"{at}: {step['value']!r} is not an item of {step['target']}",
            )


def _check_unique(pairs: Sequence[Pair], report: Report) -> None:
    ids: dict[str, str] = {}
    texts: dict[str, str] = {}
    for pair in pairs:
        first = ids.setdefault(pair.record["id"], pair.where)
        if first != pair.where:
            report.add(pair.where, "duplicate-id", f"id already used at {first}")
        first = texts.setdefault(fold(pair.record["text"]), pair.where)
        if first != pair.where:
            report.add(pair.where, "duplicate-text", f"same text as {first}")


def _canonical(value) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def _check_scenarios(pairs: Sequence[Pair], report: Report) -> None:
    groups: dict[str, list[Pair]] = defaultdict(list)
    for pair in pairs:
        groups[pair.record["scenario"]].append(pair)
    for scenario, members in groups.items():
        first = members[0]
        for pair in members[1:]:
            for key in ("app", "appVersion", "scenarioType"):
                if pair.record[key] != first.record[key]:
                    report.add(
                        pair.where,
                        "scenario-mixed",
                        f"{key} differs from {first.where} (scenario {scenario})",
                    )
            if _canonical(pair.record["gold"]) != _canonical(first.record["gold"]):
                report.add(
                    pair.where,
                    "scenario-gold",
                    f"gold differs from {first.where} (scenario {scenario})",
                )
        if len({pair.file for pair in members}) > 1:
            report.add(
                first.where,
                "scenario-split",
                f"scenario {scenario} is in both {PAIRS} and {HELDOUT}",
            )


def _check_styles(pairs: Sequence[Pair], min_styles: int, report: Report) -> None:
    styles: dict[tuple[str, str], set[str]] = defaultdict(set)
    for pair in pairs:
        styles[pair.record["app"], pair.record["scenarioType"]].add(
            pair.record["style"]
        )
    for (app, kind), found in sorted(styles.items()):
        if len(found) < min_styles:
            report.add(
                f"app {app}, type {kind}",
                "few-styles",
                f"{len(found)} phrasing style(s) {sorted(found)}, need {min_styles}",
            )


def summary(report: Report) -> str:
    """Pair counts per file, app and scenario type, with the styles used."""
    files = Counter(pair.file for pair in report.pairs)
    lines = [
        f"{len(report.pairs)} pairs ("
        + (", ".join(f"{name} {n}" for name, n in files.items()) or "no files")
        + ")"
    ]
    valid = [pair.record for pair in report.pairs if pair.valid]
    for app in sorted({record["app"] for record in valid}):
        records = [record for record in valid if record["app"] == app]
        version = report.objects.get(app, {}).get("appVersion", "?")
        outsiders = sum(record["origin"] == "outsider" for record in records)
        scenarios = len({record["scenario"] for record in records})
        lines.append(
            f"app {app} (version {version}): {len(records)} pairs, "
            f"{scenarios} scenarios, {outsiders} by outsiders"
        )
        lines.append(f"  {'type':<11} {'pairs':>5} {'scenarios':>9}  styles")
        for kind in sorted({record["scenarioType"] for record in records}):
            of_kind = [record for record in records if record["scenarioType"] == kind]
            lines.append(
                f"  {kind:<11} {len(of_kind):>5} "
                f"{len({record['scenario'] for record in of_kind}):>9}  "
                + ", ".join(sorted({record["style"] for record in of_kind}))
            )
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="check_pairs.py", description="Check the Turkish NL dataset (#36)."
    )
    parser.add_argument(
        "data_dir",
        nargs="?",
        type=Path,
        default=HERE,
        help="folder with pairs.jsonl and objects/ (default: eval/nl)",
    )
    parser.add_argument(
        "--min-styles",
        type=int,
        default=MIN_STYLES,
        help="phrasing styles each scenario type of an app needs (default: 3)",
    )
    args = parser.parse_args(argv)
    report = check_dataset(args.data_dir, min_styles=args.min_styles)
    print(summary(report))
    if report.ok:
        print("No problems.")
        return 0
    print(f"{len(report.problems)} problem(s):")
    for problem in report.problems:
        print(f"  {problem}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
