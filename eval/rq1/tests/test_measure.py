"""Tests for the RQ1 harness (#29).

Everything here runs off Windows: the measuring half of `measure.py` touches no UI Automation,
which is the property that lets a number be re-derived from a committed snapshot. Three of
these tests are drift guards rather than behaviour tests -- they fail when a definition this
harness shares with the product or with #6 is changed somewhere else, because a silently
changed definition makes an old RQ1 number incomparable with a new one.
"""

from __future__ import annotations

import csv
import re
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest
from ayna_agent.model import PRIMARY_PRIORITY, Element
from ayna_agent.recognition import snapshot as snap

import measure

REPO = measure.REPO


def node(element_id: int, parent: int | None = None, **properties: object) -> dict:
    """A raw walk node, the shape `snapshot.build` takes."""
    return {"id": element_id, "parent": parent, **properties}


def document(*nodes: dict) -> dict:
    """A real snapshot document, built by the agent's own builder."""
    return snap.build(
        list(nodes),
        window={"handle": 1, "title": "Giriş", "className": "Window", "processId": 2},
        app={"exeName": "pilot.exe"},
        started_at=datetime(2026, 11, 12, 9, 0, tzinfo=UTC),
        duration_ms=120,
        snapshot_id="11111111-1111-4111-8111-111111111111",
    )


def screen_of(*nodes: dict) -> measure.Screen:
    return measure.measure_screen(
        document(*nodes), app="pilot", screen="main", path=Path("main.json")
    )


# ------------------------------------------------------------------ what counts as a control


def test_the_interactive_set_is_still_the_one_6_measured() -> None:
    """RQ1's numbers are printed next to the D1 table, so the denominators must agree."""
    source = (REPO / "eval" / "spikes" / "uia_tree_dump.py").read_text(encoding="utf-8")
    body = re.search(r"INTERACTIVE_TYPES = frozenset\(\{(.*?)\}\)", source, re.DOTALL)
    assert body, (
        "uia_tree_dump.py no longer defines INTERACTIVE_TYPES as a frozenset literal"
    )
    assert set(re.findall(r'"([A-Za-z]+)"', body.group(1))) == measure.INTERACTIVE_TYPES


def test_a_titlebar_and_everything_under_it_is_the_frame() -> None:
    doc = document(
        node(0, None, control_type="Window", name="Giriş"),
        node(1, 0, control_type="TitleBar"),
        node(2, 1, control_type="Button", name="Kapat"),
        node(3, 0, control_type="Button", name="Tamam", automation_id="ok"),
    )
    assert measure.frame_ids(doc["elements"]) == {"e1", "e2"}


def test_frame_buttons_and_non_interactive_types_are_not_controls() -> None:
    result = screen_of(
        node(0, None, control_type="Window", name="Giriş"),
        node(1, 0, control_type="TitleBar"),
        node(2, 1, control_type="Button", name="Kapat"),
        node(3, 0, control_type="Pane"),
        node(4, 3, control_type="Button", name="Tamam", automation_id="ok"),
    )
    assert [(c.element_id, c.control_type) for c in result.controls] == [
        ("e4", "Button")
    ]


# ------------------------------------------------------------------- the proposal (the rule)


def test_the_proposal_priority_matches_the_descriptor_adr() -> None:
    assert measure.PROPOSAL_FIELDS[: len(PRIMARY_PRIORITY)] == PRIMARY_PRIORITY
    assert measure.PROPOSAL_FIELDS[-1] == "control_type"


def test_the_proposal_priority_matches_the_clients_own_list() -> None:
    """The Spy is what proposes a primary set; RQ1 must measure its order, not a guess."""
    source = (REPO / "client" / "src" / "shared" / "repository.ts").read_text(
        encoding="utf-8"
    )
    body = re.search(r"IDENTIFYING_FIELDS = \[(.*?)\] as const", source, re.DOTALL)
    assert body, (
        "repository.ts no longer defines IDENTIFYING_FIELDS as an array literal"
    )
    fields = re.findall(r"'(\w+)'", body.group(1))
    usable = fields[: fields.index("controlType") + 1]
    assert usable == [measure.JSON_NAMES[name] for name in measure.PROPOSAL_FIELDS]


def test_a_unique_automation_id_is_the_whole_set() -> None:
    result = screen_of(
        node(0, None, control_type="Window", name="Giriş"),
        node(1, 0, control_type="Edit", automation_id="user", name="Kullanıcı"),
    )
    (control,) = result.controls
    assert control.primary == {"automationId": "user"}
    assert control.match_count == 1
    assert control.recognised
    assert control.reason == measure.UNIQUE


def test_a_generated_automation_id_is_skipped_and_the_name_is_used() -> None:
    result = screen_of(
        node(0, None, control_type="Window", name="Giriş"),
        node(1, 0, control_type="Button", automation_id="1001", name="Tamam"),
    )
    (control,) = result.controls
    assert control.primary == {"name": "Tamam"}
    assert control.recognised


def test_the_set_grows_only_while_it_narrows() -> None:
    """Two buttons share a Name; the parent path is what separates them."""
    result = screen_of(
        node(0, None, control_type="Window", name="Giriş"),
        node(1, 0, control_type="Pane", automation_id="left"),
        node(2, 1, control_type="Button", name="Sil"),
        node(3, 0, control_type="Group", automation_id="right"),
        node(4, 3, control_type="Button", name="Sil"),
    )
    first, second = result.controls
    assert first.primary == {"name": "Sil", "parentPath": "Window/Pane"}
    assert second.primary == {"name": "Sil", "parentPath": "Window/Group"}
    assert first.recognised and second.recognised


def test_two_identical_controls_stay_ambiguous() -> None:
    """Same type, same name, same parent path: no primary property can separate them."""
    result = screen_of(
        node(0, None, control_type="Window", name="Giriş"),
        node(1, 0, control_type="Button", name="Sil"),
        node(2, 0, control_type="Button", name="Sil"),
    )
    assert [control.match_count for control in result.controls] == [2, 2]
    assert [control.reason for control in result.controls] == [
        measure.AMBIGUOUS,
        measure.AMBIGUOUS,
    ]
    assert not any(control.recognised for control in result.controls)


def test_a_nameless_control_falls_through_to_its_parent_path() -> None:
    """The first usable property wins even when it is far down the priority."""
    result = screen_of(
        node(0, None, control_type="Window", name="Giriş"),
        node(1, 0, control_type="ListItem"),
    )
    (control,) = result.controls
    assert control.primary == {"parentPath": "Window"}
    assert control.reason == measure.UNIQUE


def test_an_element_with_no_usable_property_at_all_reports_no_property() -> None:
    control = measure.Control(
        app="pilot",
        screen="main",
        snapshot_id="s",
        element_id="e1",
        control_type="Button",
        descriptor=Element(),
        primary={},
        match_count=0,
    )
    assert control.reason == measure.NO_PROPERTY
    assert not control.recognised


def test_the_window_is_the_scope_of_uniqueness() -> None:
    """A name unique in its own window counts, even if another window reuses it."""
    one = screen_of(
        node(0, None, control_type="Window", name="Giriş"),
        node(1, 0, control_type="Button", name="Tamam"),
    )
    two = screen_of(
        node(0, None, control_type="Window", name="Ayarlar"),
        node(1, 0, control_type="Button", name="Tamam"),
    )
    assert all(control.recognised for control in (*one.controls, *two.controls))


# -------------------------------------------------------------------------- the agent import


def test_the_imported_agent_modules_stay_free_of_ui_automation() -> None:
    """The whole measuring half depends on this: both modules say so in their docstrings."""
    forbidden = re.compile(r"^\s*(?:import|from)\s+(pywinauto|comtypes|ctypes|win32)")
    for relative in ("ayna_agent/model.py", "ayna_agent/playback/resolve.py"):
        source = (REPO / "agent" / relative).read_text(encoding="utf-8")
        offenders = [line for line in source.splitlines() if forbidden.match(line)]
        assert not offenders, (
            f"{relative} now imports Windows-only modules: {offenders}"
        )


# -------------------------------------------------------------------------------- the labels


LABEL_HEADER = "elementId,label,note\n"


def test_labels_are_read_and_applied(tmp_path: Path) -> None:
    result = screen_of(
        node(0, None, control_type="Window", name="Giriş"),
        node(1, 0, control_type="Button", name="Tamam", automation_id="ok"),
        node(2, 0, control_type="ListItem", name="satır"),
    )
    path = tmp_path / "pilot-main.csv"
    path.write_text(
        LABEL_HEADER
        + "e1,control,\ne2,ignore,a row not a control\n,missing,Yardım bağlantısı\n",
        encoding="utf-8",
    )
    measure.apply_labels(result, path)

    assert result.labelled
    assert result.missing == ["Yardım bağlantısı"]
    assert [control.label for control in result.controls] == ["control", "ignore"]
    assert [control.element_id for control in measure.counted(result)] == ["e1"]


def test_an_unlabelled_screen_counts_every_control() -> None:
    result = screen_of(
        node(0, None, control_type="Window", name="Giriş"),
        node(1, 0, control_type="Button", name="Tamam"),
    )
    assert measure.counted(result) == result.controls


@pytest.mark.parametrize(
    ("rows", "message"),
    [
        ("e1,yes,\n", "is not one of"),
        (",missing,\n", "must name the control"),
        (",control,\n", "needs an elementId"),
    ],
)
def test_a_bad_label_file_is_refused(tmp_path: Path, rows: str, message: str) -> None:
    path = tmp_path / "pilot-main.csv"
    path.write_text(LABEL_HEADER + rows, encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        measure.load_labels(path)


def test_a_label_for_an_element_the_snapshot_has_not_is_refused(tmp_path: Path) -> None:
    """A label file belongs to one snapshot; a recapture renumbers the elements."""
    result = screen_of(
        node(0, None, control_type="Window", name="Giriş"),
        node(1, 0, control_type="Button", name="Tamam"),
    )
    path = tmp_path / "pilot-main.csv"
    path.write_text(LABEL_HEADER + "e1,control,\ne7,control,\n", encoding="utf-8")
    with pytest.raises(ValueError, match="e7"):
        measure.apply_labels(result, path)


def test_a_half_labelled_screen_is_refused(tmp_path: Path) -> None:
    """`counted()` keeps only `control` rows, so an unlabelled row would leave the denominator.

    That is the same distortion a control AYNA never found causes -- the rate goes up -- and it
    is exactly what labelling exists to prevent, so a partially labelled screen must not
    measure at all rather than print a plausible wrong number.
    """
    result = screen_of(
        node(0, None, control_type="Window", name="Giris"),
        node(1, 0, control_type="Button", name="Tamam"),
        node(2, 0, control_type="Button", name="Iptal"),
        node(3, 0, control_type="CheckBox", name="Beni hatirla"),
    )
    path = tmp_path / "pilot-main.csv"
    path.write_text(LABEL_HEADER + "e1,control,\n", encoding="utf-8")
    with pytest.raises(ValueError, match="2 of 3 measured controls"):
        measure.apply_labels(result, path)
    assert not result.labelled


def test_a_fully_labelled_screen_measures(tmp_path: Path) -> None:
    """The guard counts `ignore` as labelled: it is a decision, not an omission."""
    result = screen_of(
        node(0, None, control_type="Window", name="Giris"),
        node(1, 0, control_type="Button", name="Tamam"),
        node(2, 0, control_type="Button", name="Iptal"),
    )
    path = tmp_path / "pilot-main.csv"
    path.write_text(
        LABEL_HEADER + "e1,control,\ne2,ignore,layout only\n", encoding="utf-8"
    )
    measure.apply_labels(result, path)
    assert [control.element_id for control in measure.counted(result)] == ["e1"]


# --------------------------------------------------------------------------------- the rates


def test_rates_are_per_control_type_with_a_total() -> None:
    result = screen_of(
        node(0, None, control_type="Window", name="Giriş"),
        node(1, 0, control_type="Edit", automation_id="user"),
        node(2, 0, control_type="Button", name="Sil"),
        node(3, 0, control_type="Button", name="Sil"),
    )
    rows = measure.rate_rows(result.controls)
    by_type = {row["controlType"]: row for row in rows}

    assert rows[0]["controlType"] == "Button", "commonest type first"
    assert rows[-1]["controlType"] == measure.TOTAL
    assert by_type["Button"]["controls"] == 2
    assert by_type["Button"]["recognised"] == 0
    assert by_type["Button"]["ambiguous"] == 2
    assert by_type["Edit"]["recognisedShare"] == "100.0"
    assert by_type[measure.TOTAL]["controls"] == 3
    assert by_type[measure.TOTAL]["recognisedShare"] == "33.3"
    assert by_type[measure.TOTAL]["byAutomationId"] == 1
    assert by_type[measure.TOTAL]["byName"] == 2


def test_missing_controls_enter_only_the_total_denominator() -> None:
    result = screen_of(
        node(0, None, control_type="Window", name="Giriş"),
        node(1, 0, control_type="Edit", automation_id="user"),
    )
    rows = measure.rate_rows(result.controls, missing=1)
    total = rows[-1]
    assert total["controls"] == 2
    assert total["recognised"] == 1
    assert total["recognisedShare"] == "50.0"
    assert total["missing"] == 1
    assert rows[0]["missing"] == 0


def test_share_of_nothing_is_an_empty_cell() -> None:
    assert measure.share(0, 0) == ""
    assert measure.share(1, 3) == "33.3"


def test_an_app_with_no_control_still_writes_a_total_row() -> None:
    rows = measure.rate_rows([])
    assert [row["controlType"] for row in rows] == [measure.TOTAL]
    assert rows[0]["controls"] == 0
    assert rows[0]["recognisedShare"] == ""


# ----------------------------------------------------------------------------------- the CSV


def test_the_csv_opens_in_excel_as_utf8(tmp_path: Path) -> None:
    path = measure.write_csv(
        tmp_path / "out.csv", ("name", "value"), [{"name": "Şifre", "value": 1}]
    )
    raw = path.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf"), "Excel needs the BOM to read UTF-8"
    assert b"\r\n" in raw
    with path.open(encoding="utf-8-sig", newline="") as handle:
        assert list(csv.DictReader(handle)) == [{"name": "Şifre", "value": "1"}]


def test_the_control_csv_carries_the_evidence_and_the_empty_label_column() -> None:
    result = screen_of(
        node(0, None, control_type="Window", name="Giriş"),
        node(1, 0, control_type="Edit", automation_id="user", name="Kullanıcı"),
    )
    (row,) = measure.control_rows([result])
    assert set(measure.CONTROL_COLUMNS) == set(row)
    assert row["elementId"] == "e1"
    assert row["automationId"] == "user"
    assert row["windowTitle"] == "Giriş"
    assert row["primaryProperties"] == "automationId"
    assert row["primary"] == '{"automationId": "user"}'
    assert row["recognised"] == "yes"
    assert row["label"] == "", "the label column is the human's to fill"


def test_every_rate_column_is_produced() -> None:
    (row,) = measure.rate_rows([])
    assert set(measure.RATE_COLUMNS) == set(row)


def test_the_property_columns_cannot_collide_with_the_row_label() -> None:
    """`byControlType` counts the property; `controlType` says which row this is."""
    assert measure.by_column("control_type") == "byControlType"
    assert "controlType" in measure.RATE_COLUMNS
    assert len(set(measure.RATE_COLUMNS)) == len(measure.RATE_COLUMNS)


# ------------------------------------------------------------------------------- the summary


def test_the_summary_says_which_denominator_it_used() -> None:
    result = screen_of(
        node(0, None, control_type="Window", name="Giriş"),
        node(1, 0, control_type="Edit", automation_id="user"),
    )
    unlabelled = "\n".join(measure.summary_table("pilot", [result]))
    assert "no labels" in unlabelled
    assert "100.0%" in unlabelled

    result.labelled = True
    result.controls = [replace(result.controls[0], label=measure.LABEL_CONTROL)]
    labelled = "\n".join(measure.summary_table("pilot", [result]))
    assert "ground truth, 1/1 screen(s) labelled" in labelled


# ---------------------------------------------------------------------------------- the apps


def test_the_registry_lists_the_d1_pilots_in_order() -> None:
    apps = measure.load_apps()
    assert measure.pilot_ids(apps) == ["handbrake", "keepass2"]
    assert apps["keepassxc"]["pilot"] is None, "D1 makes the third pilot conditional"


def test_every_registered_app_names_its_process_and_its_screens() -> None:
    for app_id, entry in measure.load_apps().items():
        assert entry["process"].endswith(".exe"), app_id
        assert entry["screens"], app_id
        for screen in entry["screens"]:
            assert re.fullmatch(r"[a-z0-9-]+", screen["name"]), screen
            assert screen["state"] and screen["open"], screen


def test_measuring_an_unknown_app_fails_without_writing_anything() -> None:
    assert measure.main(["measure", "notepad"]) == 2


# ------------------------------------------------------------------ which window is a screen


def window(title: str) -> dict:
    """A `list_windows` entry, in the order `EnumWindows` answers: top of the Z-order first."""
    return {
        "handle": abs(hash(title)) % 100000,
        "title": title,
        "processName": "pilot.exe",
    }


def test_a_screen_is_captured_from_the_topmost_window_alone() -> None:
    """Two windows open means two screens, not one screen in two files.

    `measure` counts every snapshot file of an app, so capturing KeePass 2's main form again
    under `entry-editor` would count its controls twice and lift the rate.
    """
    staged, left = measure.pick_windows(
        [window("Add Entry"), window("vault - KeePass")]
    )
    assert [w["title"] for w in staged] == ["Add Entry"]
    assert [w["title"] for w in left] == ["vault - KeePass"]


def test_one_window_is_captured_whole_and_nothing_is_left() -> None:
    staged, left = measure.pick_windows([window("HandBrake")])
    assert [w["title"] for w in staged] == ["HandBrake"]
    assert left == []


def test_all_windows_captures_every_one_and_reports_nothing_skipped() -> None:
    windows = [window("Add Entry"), window("vault - KeePass")]
    staged, left = measure.pick_windows(windows, all_windows=True)
    assert [w["title"] for w in staged] == ["Add Entry", "vault - KeePass"]
    assert left == []


def test_a_single_window_keeps_the_screen_name_and_several_are_numbered() -> None:
    """The bare name is what a screen's snapshot is called; the suffix only appears with
    `--all-windows`, where the file no longer stands for one screen."""
    assert measure.snapshot_name("entry-editor", 0, 1) == "entry-editor"
    assert measure.snapshot_name("entry-editor", 0, 2) == "entry-editor-1"
    assert measure.snapshot_name("entry-editor", 1, 2) == "entry-editor-2"
