"""Checks the Turkish NL dataset (eval/nl/, #36) and its checker.

The checker is a script next to the data (eval/nl/check_pairs.py). eval/ has
its own project and Windows CI job since #122, but that job runs only the
trial app's tests, so the ai job runs this one: the dataset is the AI
service's test set, and jsonschema is already installed.
"""

import copy
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

NL_DIR = Path(__file__).resolve().parents[2] / "eval" / "nl"
_spec = importlib.util.spec_from_file_location("check_pairs", NL_DIR / "check_pairs.py")
check_pairs = importlib.util.module_from_spec(_spec)
sys.modules["check_pairs"] = check_pairs  # dataclasses look their module up
_spec.loader.exec_module(check_pairs)


# --- The dataset in the repository ---------------------------------------------


def test_repository_dataset_has_no_problems():
    report = check_pairs.check_dataset(NL_DIR)
    assert report.pairs
    assert report.ok, "\n".join(str(problem) for problem in report.problems)


def test_cli_reports_and_exits_zero(capsys):
    assert check_pairs.main([str(NL_DIR)]) == 0
    assert "No problems." in capsys.readouterr().out


# --- The checker, on a small dataset of its own --------------------------------

OBJECTS = {
    "app": "demo",
    "appVersion": "1.0",
    "source": "test fixture",
    "objects": {
        "form.nameInput": {
            "automationId": "demo.form.nameInput",
            "controlType": "Edit",
            "description": "Ad alanı",
        },
        "form.cityCombo": {
            "automationId": "demo.form.cityCombo",
            "controlType": "ComboBox",
            "description": "Şehir listesi",
            "items": ["Ankara", "İzmir"],
        },
        "form.saveButton": {
            "automationId": "demo.form.saveButton",
            "controlType": "Button",
            "description": "Kaydet butonu",
        },
        "form.messageLabel": {
            "automationId": "demo.form.messageLabel",
            "controlType": "Text",
            "description": "Mesaj etiketi",
        },
        "form.activeCheck": {
            "automationId": "demo.form.activeCheck",
            "controlType": "CheckBox",
            "description": "Aktif onay kutusu",
        },
        "form.newsCheck": {
            "automationId": "demo.form.newsCheck",
            "controlType": "CheckBox",
            "description": "Bülten onay kutusu",
        },
    },
}
GOLD = {
    "version": "0.1",
    "steps": [
        {"keyword": "Type", "target": "form.nameInput", "value": "Ayşe"},
        {"keyword": "Select", "target": "form.cityCombo", "value": "İzmir"},
        {"keyword": "Click", "target": "form.saveButton"},
        {
            "keyword": "Verify",
            "target": "form.messageLabel",
            "checkpoint": {
                "property": "name",
                "operator": "contains",
                "expected": "Kaydedildi",
            },
        },
    ],
}
TEXTS = {
    "imperative": "Ad alanına Ayşe yaz, şehirden İzmir'i seç, Kaydet'e tıkla ve mesajda 'Kaydedildi' geçtiğini doğrula.",
    "polite": "Lütfen ada Ayşe yazın, şehir olarak İzmir seçin ve kaydedin; mesaj 'Kaydedildi' içermeli.",
    "terse": "ad: ayse, sehir: izmir, kaydet, mesaj 'kaydedildi' icermeli",
}


def records() -> list[dict]:
    return [
        {
            "id": f"demo-{n:03d}",
            "app": "demo",
            "appVersion": "1.0",
            "scenarioType": "form",
            "scenario": "demo-save",
            "style": style,
            "origin": "team",
            "author": "galip",
            "text": text,
            "gold": copy.deepcopy(GOLD),
        }
        for n, (style, text) in enumerate(TEXTS.items(), 1)
    ]


def write(directory: Path, pairs: list[dict], objects: dict | None = None) -> Path:
    # newline="\n": LF on every OS, like a checkout under .gitattributes eol=lf.
    (directory / "objects").mkdir(exist_ok=True)
    (directory / "objects" / "demo.json").write_text(
        json.dumps(objects or OBJECTS, ensure_ascii=False),
        encoding="utf-8",
        newline="\n",
    )
    lines = [json.dumps(pair, ensure_ascii=False) + "\n" for pair in pairs]
    (directory / "pairs.jsonl").write_text(
        "".join(lines), encoding="utf-8", newline="\n"
    )
    return directory


def codes(directory: Path, min_styles: int = 3) -> set[str]:
    report = check_pairs.check_dataset(directory, min_styles=min_styles)
    return {problem.code for problem in report.problems}


def test_fixture_dataset_is_valid(tmp_path):
    assert codes(write(tmp_path, records())) == set()


def step(pairs, i):
    return pairs[0]["gold"]["steps"][i]


def same_gold_everywhere(change):
    """Apply `change` to every pair's gold, so the variants still agree."""

    def mutate(pairs, objects):
        for pair in pairs:
            change(pair["gold"]["steps"])

    return mutate


MUTATIONS = {
    "duplicate-id": ("duplicate-id", lambda p, o: p[1].update(id="demo-001")),
    "id-app": ("id-app", lambda p, o: p[0].update(id="other-001")),
    "duplicate-text": (
        "duplicate-text",
        lambda p, o: p[1].update(text=p[0]["text"].upper()),
    ),
    "unknown-target": (
        "unknown-target",
        same_gold_everywhere(lambda s: s[2].update(target="form.closeButton")),
    ),
    "select-without-value": (
        "schema",
        same_gold_everywhere(lambda s: s[1].pop("value")),
    ),
    "step-with-id": (
        "schema",
        same_gold_everywhere(
            lambda s: s[2].update(id="deb27841-13ea-4846-b144-07081ad912ce")
        ),
    ),
    "empty-gold": ("schema", lambda p, o: p[0]["gold"].update(steps=[])),
    "outsider-real-name": (
        "schema",
        lambda p, o: p[0].update(origin="outsider", author="Ayşe"),
    ),
    "type-on-button": (
        "control-type",
        same_gold_everywhere(lambda s: s[0].update(target="form.saveButton")),
    ),
    "value-on-label": (
        "control-type",
        same_gold_everywhere(lambda s: s[3]["checkpoint"].update(property="value")),
    ),
    "checked-on-button": (
        "control-type",
        same_gold_everywhere(
            lambda s: s[3].update(
                target="form.saveButton",
                checkpoint={
                    "property": "checked",
                    "operator": "equals",
                    "expected": True,
                },
            )
        ),
    ),
    "unknown-item": (
        "unknown-item",
        lambda p, o: o["objects"]["form.cityCombo"].update(items=["Ankara"]),
    ),
    "ungrounded-value": (
        "ungrounded",
        same_gold_everywhere(lambda s: s[0].update(value="Fatma")),
    ),
    "checkpoint-with-click": (
        "type-rule",
        lambda p, o: [pair.update(scenarioType="checkpoint") for pair in p],
    ),
    "only-verify-but-form": (
        "type-rule",
        same_gold_everywhere(lambda s: s.__delitem__(slice(0, 3))),
    ),
    "wait-in-form": (
        "type-rule",
        same_gold_everywhere(
            lambda s: s.insert(0, {"keyword": "Wait", "target": "form.nameInput"})
        ),
    ),
    "wait-type-without-wait": (
        "type-rule",
        lambda p, o: [pair.update(scenarioType="wait") for pair in p],
    ),
    "variants-disagree": (
        "scenario-gold",
        lambda p, o: step(p, 2).update(target="form.activeCheck"),
    ),
    "variants-mixed-type": (
        "scenario-mixed",
        lambda p, o: p[2].update(scenarioType="settings"),
    ),
    "app-version": ("app-version", lambda p, o: o.update(appVersion="1.1")),
    "items-on-edit": (
        "items",
        lambda p, o: o["objects"]["form.nameInput"].update(items=["x"]),
    ),
    "same-automation-id": (
        "duplicate-object",
        lambda p, o: o["objects"]["form.saveButton"].update(
            automationId="demo.form.nameInput"
        ),
    ),
    "few-styles": ("few-styles", lambda p, o: p[2].update(style="imperative")),
    "unknown-style": ("schema", lambda p, o: p[0].update(style="casual")),
    "unknown-tag": ("schema", lambda p, o: p[0].update(tags=["hard"])),
    # 4.4: a team text glues a suffix to a bare value ("İzmiri" for "İzmir").
    "team-value-with-glued-suffix": (
        "bare-suffix",
        lambda p, o: p[0].update(text=p[0]["text"].replace("İzmir'i", "İzmiri")),
    ),
    "team-value-inside-a-longer-word": (
        "bare-suffix",
        lambda p, o: p[2].update(text=p[2]["text"].replace("ad: ayse", "ad: xayse")),
    ),
    # 6.8: a check-box Click without the assumed start state in notes.
    "checkbox-click-without-start-state": (
        "start-state",
        same_gold_everywhere(
            lambda s: s.insert(2, {"keyword": "Click", "target": "form.activeCheck"})
        ),
    ),
}


@pytest.mark.parametrize("name", MUTATIONS)
def test_checker_reports_the_broken_rule(tmp_path, name):
    code, mutate = MUTATIONS[name]
    pairs, objects = records(), copy.deepcopy(OBJECTS)
    mutate(pairs, objects)
    assert code in codes(write(tmp_path, pairs, objects))


def test_an_outsider_text_is_kept_as_written(tmp_path):
    """4.4: the glued-suffix rule is for team pairs; outsider texts are not edited."""
    pairs = records()
    pairs[0].update(
        origin="outsider",
        author="ext-01",
        text=pairs[0]["text"].replace("İzmir'i", "İzmiri"),
        notes='value read as "İzmir" (4.4)',
    )
    assert codes(write(tmp_path, pairs)) == set()


@pytest.mark.parametrize(
    "written",
    ["İzmir'i", '"İzmir"i', "‘İzmir’i", "'İzmir'", "İzmir", "İzmir, sonra"],
)
def test_a_quoted_or_whole_team_value_passes(tmp_path, written):
    pairs = records()
    pairs[0]["text"] = pairs[0]["text"].replace("İzmir'i", written)
    assert "bare-suffix" not in codes(write(tmp_path, pairs))


@pytest.mark.parametrize(
    ("literal", "text", "alone"),
    [
        ("ankara", "ankara'yi sec", True),
        ("ankara", "sehir: ankara", True),
        ("ankara", "ankarayi sec", False),
        ("ankara", "ankarayi sec, sonra ankara yaz", True),
        ("1234", "1234u yaz", False),
        ("admin", "admin/admin ile", True),
        ("admin", "superadmin yaz", False),
        ("welcome, admin!", "'welcome, admin!'i gor", True),
        ("kalite guvence", "kalite guvencesi sec", False),
    ],
)
def test_stands_alone(literal, text, alone):
    assert check_pairs._stands_alone(literal, text) is alone


def checkbox_pairs(notes: str | None) -> list[dict]:
    """The fixture with 'Aktif kutusunu işaretle' (a Click on the CheckBox) in every text."""
    pairs = records()
    for pair in pairs:
        pair["text"] += " Aktif kutusunu işaretle."
        pair["gold"]["steps"].insert(
            2, {"keyword": "Click", "target": "form.activeCheck"}
        )
        if notes is not None:
            pair["notes"] = notes
    return pairs


@pytest.mark.parametrize(
    "notes",
    [
        "start state: unchecked (6.8)",
        "Start state: checked",
        "start state: form.activeCheck unchecked; the save keeps it",
    ],
)
def test_a_checkbox_click_with_its_start_state_passes(tmp_path, notes):
    assert codes(write(tmp_path, checkbox_pairs(notes))) == set()


@pytest.mark.parametrize(
    "notes", [None, "", "toggles the box", "start state: see the app; unchecked"]
)
def test_a_checkbox_click_without_its_start_state_fails(tmp_path, notes):
    assert codes(write(tmp_path, checkbox_pairs(notes))) == {"start-state"}


def test_two_clicks_on_one_checkbox_need_one_start_state(tmp_path):
    pairs = checkbox_pairs("start state: unchecked")
    for pair in pairs:
        pair["text"] += " Sonra işaretini kaldır."
        pair["gold"]["steps"].insert(
            3, {"keyword": "Click", "target": "form.activeCheck"}
        )
    assert codes(write(tmp_path, pairs)) == set()


def two_checkbox_pairs(notes: str) -> list[dict]:
    """checkbox_pairs plus 'Bülten kutusunu da işaretle': Clicks on two boxes."""
    pairs = checkbox_pairs(notes)
    for pair in pairs:
        pair["text"] += " Bülten kutusunu da işaretle."
        pair["gold"]["steps"].insert(
            3, {"keyword": "Click", "target": "form.newsCheck"}
        )
    return pairs


@pytest.mark.parametrize(
    "notes",
    [
        "start state: form.activeCheck unchecked; start state: form.newsCheck checked",
        "Start state: form.newsCheck unchecked (6.8)\nstart state: form.activeCheck unchecked",
    ],
)
def test_two_checkboxes_with_a_start_state_each_pass(tmp_path, notes):
    assert codes(write(tmp_path, two_checkbox_pairs(notes))) == set()


@pytest.mark.parametrize(
    "notes",
    [
        "start state: unchecked",
        "start state: unchecked; start state: unchecked",
        "start state: form.activeCheck unchecked",
        "start state: form.activeCheck unchecked, form.newsCheck checked",
        "start state: form.activeCheck and form.newsCheck unchecked",
        "start state: form.activeCheck unchecked; start state: form.newsCheckX checked",
    ],
)
def test_two_checkboxes_need_one_named_start_state_each(tmp_path, notes):
    """6.8: one phrase per box, naming that box only (#176 review)."""
    assert codes(write(tmp_path, two_checkbox_pairs(notes))) == {"start-state"}


def test_each_checkbox_without_its_start_state_is_reported_at_its_click(tmp_path):
    notes = "start state: form.activeCheck unchecked"
    report = check_pairs.check_dataset(write(tmp_path, two_checkbox_pairs(notes)))
    messages = [problem.message for problem in report.problems]
    assert len(messages) == len(TEXTS)
    assert all(
        m.startswith("gold.steps[3]: Click toggles form.newsCheck") for m in messages
    )


def test_checking_a_checkbox_state_needs_no_start_state(tmp_path):
    def verify_checked(steps):
        steps.append(
            {
                "keyword": "Verify",
                "target": "form.activeCheck",
                "checkpoint": {
                    "property": "checked",
                    "operator": "equals",
                    "expected": True,
                },
            }
        )

    pairs = records()
    same_gold_everywhere(verify_checked)(pairs, None)
    assert codes(write(tmp_path, pairs)) == set()


def guideline_section(number: int) -> str:
    text = (NL_DIR / "guideline.md").read_text(encoding="utf-8")
    start = text.index(f"\n## {number}. ")
    return text[start : text.index("\n## ", start + 1)]


def first_column(section: str) -> set[str]:
    """Names in backticks that start a table row: | `name` | ..."""
    return set(re.findall(r"^\| `(\w+)` \|", section, flags=re.MULTILINE))


def field_values(section: str, name: str) -> set[str]:
    """Values in backticks in the Meaning cell of the field table row of `name`."""
    row = re.search(rf"^\| `{name}` \| \w+ \|(.*)\|$", section, flags=re.MULTILINE)
    return set(re.findall(r"`(\w+)`", row.group(1)))


def test_closed_lists_in_the_pair_schema_match_the_guideline():
    """style, tags, scenarioType and origin are closed enums, as in the guideline."""
    schema = json.loads((NL_DIR / "pair.schema.json").read_text(encoding="utf-8"))
    properties = schema["properties"]
    styles = guideline_section(5)
    assert set(properties["style"]["enum"]) == first_column(styles)
    tags = styles[styles.index("**Tags**") :]
    assert set(properties["tags"]["items"]["enum"]) == set(
        re.findall(r"^- `(\w+)` —", tags, flags=re.MULTILINE)
    )
    assert set(properties["scenarioType"]["enum"]) == first_column(guideline_section(3))
    # The record format (2) lists origin's values, and repeats style's and tags'.
    fields = guideline_section(2)
    assert set(properties["origin"]["enum"]) == field_values(fields, "origin")
    assert set(properties["style"]["enum"]) == field_values(fields, "style")
    assert set(properties["tags"]["items"]["enum"]) == field_values(fields, "tags")


def test_pair_of_an_app_without_objects_file(tmp_path):
    pairs = records()
    for pair in pairs:
        pair.update(app="other", id=pair["id"].replace("demo", "other"))
    assert "missing-objects" in codes(write(tmp_path, pairs))


def test_broken_lines_are_reported(tmp_path):
    directory = write(tmp_path, records())
    with (directory / "pairs.jsonl").open("a", encoding="utf-8", newline="\n") as f:
        f.write("\n{not json\n")
    assert {"blank-line", "invalid-json"} <= codes(directory)


def test_min_styles_zero_accepts_a_growing_set(tmp_path):
    directory = write(tmp_path, records()[:1])
    assert codes(directory) == {"few-styles"}
    assert codes(directory, min_styles=0) == set()


# --- Held-out split (#57) ---------------------------------------------------------


def heldout_records() -> list[dict]:
    pairs = records()
    for n, pair in enumerate(pairs, 4):
        pair.update(
            id=f"demo-{n:03d}",
            scenario="demo-save-heldout",
            text=pair["text"].replace("Ayşe", "Fatma").replace("ayse", "fatma"),
        )
        pair["gold"]["steps"][0]["value"] = "Fatma"
    return pairs


def write_heldout(directory: Path, pairs: list[dict], frozen: bool) -> None:
    # The digest is of the LF string, so the file must be LF on Windows too.
    lines = "".join(json.dumps(pair, ensure_ascii=False) + "\n" for pair in pairs)
    (directory / "heldout.jsonl").write_text(lines, encoding="utf-8", newline="\n")
    if frozen:
        digest = hashlib.sha256(lines.encode("utf-8")).hexdigest()
        (directory / "heldout.sha256").write_text(
            f"{digest}  heldout.jsonl\n", encoding="utf-8", newline="\n"
        )


def test_frozen_heldout_split_passes(tmp_path):
    directory = write(tmp_path, records())
    write_heldout(directory, heldout_records(), frozen=True)
    assert codes(directory) == set()


def test_heldout_split_without_recorded_hash(tmp_path):
    directory = write(tmp_path, records())
    write_heldout(directory, heldout_records(), frozen=False)
    assert "not-frozen" in codes(directory)


def test_heldout_split_edited_after_freezing(tmp_path):
    directory = write(tmp_path, records())
    write_heldout(directory, heldout_records(), frozen=True)
    with (directory / "heldout.jsonl").open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(heldout_records()[0] | {"id": "demo-009"}) + "\n")
    assert "heldout-changed" in codes(directory)


def test_scenario_on_both_sides_of_the_split(tmp_path):
    directory = write(tmp_path, records())
    pairs = heldout_records()
    for pair in pairs:
        pair["scenario"] = "demo-save"
        pair["gold"]["steps"][0]["value"] = "Ayşe"
        pair["text"] = pair["text"].replace("Fatma", "Ayşe").replace("fatma", "ayse")
        pair["text"] += " (tekrar)"
    write_heldout(directory, pairs, frozen=True)
    assert "scenario-split" in codes(directory)


def test_fold_ignores_case_and_turkish_diacritics():
    assert check_pairs.fold("Şifre  İÇİN Iğdır'a") == "sifre icin igdir'a"
