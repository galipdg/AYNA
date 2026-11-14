"""Tests for the win32 fallback trial (#23).

Nothing here touches UI Automation or pywinauto: what is worth testing is the two judgements
the report rests on -- "win32 added a number UIA did not have" and "the number survived a
restart" -- because both are easy to get silently wrong in a direction that flatters the
fallback. The probing itself is Windows-only and is recorded as a manual check.
"""

from __future__ import annotations

import json
from pathlib import Path

import win32_probe as probe


def seen(
    element_id: str = "e1",
    control_type: str = "Button",
    automation_id: str | None = None,
    name: str | None = "Tamam",
    class_name: str | None = "Button",
    handle: int | None = 123456,
    control_id: int | None = None,
) -> probe.Seen:
    win32 = None if handle is None else {"className": class_name, "control_id": control_id}
    return probe.Seen(
        element_id=element_id,
        control_type=control_type,
        automation_id=automation_id,
        name=name,
        class_name=class_name,
        native_window_handle=handle,
        win32=win32,
    )


# ------------------------------------------------------- what counts as a usable UIA id


def test_a_developer_chosen_automation_id_is_usable() -> None:
    assert seen(automation_id="m_tbPassword").uia_id_usable


def test_a_bare_number_is_not_a_usable_automation_id() -> None:
    """`model._GENERATED_ID`'s own first example is a Win32 control id, so this is the rule
    the product already applies -- the trial must not quietly use a laxer one."""
    assert not seen(automation_id="1050270").uia_id_usable
    assert not seen(automation_id="").uia_id_usable
    assert not seen(automation_id=None).uia_id_usable


# ------------------------------------------------------ what counts as a win32 gain


def test_a_zero_control_id_is_not_a_gain() -> None:
    """Zero is Windows' "this window has no control id", and WinForms leaves it at zero for
    the controls it creates itself. Counting it would invent a gain out of an absence."""
    assert not seen(control_id=0).win32_adds_a_number


def test_the_same_number_arriving_by_another_road_is_not_a_gain() -> None:
    """UIA's AutomationId for a Win32 control usually *is* its control id. A fallback that
    hands back the number already in the snapshot has added nothing."""
    assert not seen(automation_id="1050270", control_id=1050270).win32_adds_a_number


def test_a_control_id_on_an_element_uia_cannot_name_is_a_gain() -> None:
    item = seen(automation_id=None, control_id=1001)
    assert item.win32_adds_a_number
    assert not item.uia_id_usable


def test_an_element_with_no_window_of_its_own_cannot_gain_anything() -> None:
    """A WPF window is one HWND, so none of its controls has one -- this is the "which control
    types do not gain" half of the acceptance criterion, and it is structural."""
    item = seen(handle=None, automation_id=None)
    assert not item.has_hwnd
    assert item.win32 is None
    assert not item.win32_adds_a_number


# ------------------------------------------------------------------------- the table


def test_the_table_counts_per_control_type_and_totals_them() -> None:
    rows = probe.by_control_type(
        [
            seen("e1", "Button", automation_id="ok"),
            seen("e2", "Button", automation_id=None, control_id=1001),
            seen("e3", "Spinner", automation_id="1050270", control_id=1050270),
        ]
    )
    by_name = {row.control_type: row for row in rows}
    assert by_name["Button"].total == 2
    assert by_name["Button"].uia_identified == 1
    assert by_name["Button"].win32_adds == 1
    assert by_name["Button"].gained == ["e2"]
    assert by_name["Spinner"].win32_adds == 0, "the same number is not an addition"
    assert by_name[probe.TOTAL].total == 3
    assert by_name[probe.TOTAL].uia_identified == 1
    assert rows[-1].control_type == probe.TOTAL, "the total is the last row"


def test_the_total_row_is_rendered_in_bold_and_every_row_appears() -> None:
    lines = probe.table(probe.by_control_type([seen(), seen("e2", "Edit")]))
    assert lines[0].startswith("| control type |")
    assert any("**TOTAL**" in line for line in lines)
    assert len(lines) == 2 + 3  # header, rule, two types, total


def test_a_type_with_no_element_produces_no_row() -> None:
    assert probe.by_control_type([]) == []


# ------------------------------------------------------------------- across two runs


def test_an_element_is_matched_across_runs_by_what_cannot_change() -> None:
    """Not the element id (a position in one walk), not the HWND (session-scoped), and not
    the AutomationId -- that is the thing under test."""
    assert probe.key_of(seen(element_id="e1", handle=1)) == probe.key_of(
        seen(element_id="e99", handle=2)
    )


def test_a_changed_control_id_means_the_fallback_cannot_work() -> None:
    first = [seen("e1", automation_id=None, control_id=1001)]
    second = [seen("e7", automation_id=None, control_id=2002)]
    drift = probe.compare_runs(first, second)

    assert drift.matched == 1
    assert drift.control_id_changed == [("e1", 1001, 2002)]
    assert "NOT stable" in drift.verdict


def test_a_stable_control_id_beside_an_unstable_automation_id_is_the_case_for_it() -> None:
    first = [seen("e1", automation_id="1050270", control_id=1001)]
    second = [seen("e1", automation_id="1050999", control_id=1001)]
    drift = probe.compare_runs(first, second)

    assert drift.automation_id_changed == [("e1", "1050270", "1050999")]
    assert drift.control_id_stable == 1
    assert "pays for itself" in drift.verdict


def test_both_numbers_stable_points_at_the_models_rule_not_a_second_backend() -> None:
    rows = [seen("e1", automation_id="1050270", control_id=1001)]
    drift = probe.compare_runs(rows, list(rows))

    assert drift.automation_id_changed == []
    assert drift.control_id_stable == 1
    assert "the model's" in drift.verdict


def test_no_control_id_anywhere_leaves_nothing_to_fall_back_to() -> None:
    rows = [seen("e1", automation_id=None, control_id=0)]
    drift = probe.compare_runs(rows, list(rows))

    assert drift.control_id_stable == 0
    assert "nothing for a" in drift.verdict


def test_elements_sharing_a_key_are_dropped_rather_than_guessed() -> None:
    """Two nameless siblings of the same class cannot be told apart across runs, and guessing
    would invent stability. The probe reports how many it matched so the gap is visible."""
    rows = [
        seen("e1", automation_id=None, name=None, control_id=1001),
        seen("e2", automation_id=None, name=None, control_id=1002),
        seen("e3", name="Kaydet", automation_id="save"),
    ]
    drift = probe.compare_runs(rows, list(rows))
    assert drift.matched == 1, "only the named one can be matched"


def test_the_window_handle_is_expected_to_move_and_is_reported_separately() -> None:
    """`NEVER_MATCH` calls it session-scoped; the probe prints it so a run where it did *not*
    move is recognisable as the same process rather than a restart."""
    first = [seen("e1", handle=111)]
    second = [seen("e1", handle=222)]
    assert probe.compare_runs(first, second).handle_stable == 0
    assert probe.compare_runs(first, list(first)).handle_stable == 1


# ----------------------------------------------------------------------- round trip


def test_a_saved_run_reads_back_unchanged(tmp_path: Path) -> None:
    rows = [seen("e1", automation_id=None, control_id=1001), seen("e2", handle=None)]
    path = tmp_path / "run.json"
    path.write_text(
        json.dumps({"elements": [item.to_dict() for item in rows]}), encoding="utf-8"
    )
    back = [probe.from_dict(row) for row in json.loads(path.read_text(encoding="utf-8"))["elements"]]

    assert [item.element_id for item in back] == ["e1", "e2"]
    assert back[0].win32_control_id == 1001
    assert back[1].win32 is None
    assert [item.uia_id_usable for item in back] == [False, False]


def test_runs_compare_even_when_elements_have_no_name_or_class() -> None:
    """A nameless element is the entire population #23 is about, and `None` does not compare
    with `str`, so sorting the match keys raw crashes on every real run."""
    rows = [
        seen("e1", "Pane", automation_id="199002", name=None, class_name=None, control_id=1),
        seen("e2", "Edit", automation_id="1001", name="Ara", class_name="Edit", control_id=1001),
    ]
    drift = probe.compare_runs(rows, list(rows))
    assert drift.matched == 2


def test_elements_without_a_window_do_not_count_as_a_stable_handle() -> None:
    """58 of KeePass 2's 74 elements have no window at all, so counting `None == None` as
    "the handle did not move" reported 49 stable handles and read as evidence against
    `NEVER_MATCH`'s session-scoped claim."""
    rows = [
        seen("e1", "Button", name="Tamam", handle=None),
        seen("e2", "Button", name="İptal", handle=None),
        seen("e3", "Edit", name="Ara", handle=7),
    ]
    drift = probe.compare_runs(rows, list(rows))
    assert drift.matched == 3
    assert drift.handle_stable == 1, "only the one element that has a window"
