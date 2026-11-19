"""The NL dataset's object list for this app, `eval/nl/objects/sample.json` (#36).

Offscreen, so macOS runs it too. Whether the ids and types are what UI Automation really
reports is `test_nl_objects_uia.py`'s job, on Windows.
"""

from __future__ import annotations

import json

import jsonschema
import pytest

import nl_objects

SCHEMA = nl_objects.OUTPUT.parents[1] / "objects.schema.json"


@pytest.fixture(scope="module")
def built():
    nl_objects.offscreen_app()
    return nl_objects.build()


def test_the_committed_file_is_what_the_generator_writes(built):
    committed = nl_objects.OUTPUT.read_text(encoding="utf-8")
    assert committed == nl_objects.render(built), "run nl_objects.py --write"


def test_the_file_matches_the_datasets_schema(built):
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(built, schema)


def test_objects_share_an_automation_id_only_when_their_names_differ(built):
    """`eval/nl/check_pairs.py` rejects a shared id unless every object gives a distinct
    `name`: only the settings tab items do, because Qt gives them the tab bar's id."""
    by_id: dict[str, list[dict]] = {}
    for obj in built["objects"].values():
        by_id.setdefault(obj["automationId"], []).append(obj)
    shared = {i: objs for i, objs in by_id.items() if len(objs) > 1}
    assert set(shared) == {"QApplication.settings.tabs.qt_tabwidget_tabbar"}
    names = [
        obj.get("name")
        for obj in shared["QApplication.settings.tabs.qt_tabwidget_tabbar"]
    ]
    assert None not in names and len(set(names)) == len(names)


def test_the_settings_tab_items_are_listed_with_their_names(built):
    tabs = {
        name: (obj["controlType"], obj["name"])
        for name, obj in built["objects"].items()
        if obj["controlType"] == "TabItem"
    }
    assert tabs == {
        "settings.generalTab": ("TabItem", "Genel"),
        "settings.notificationsTab": ("TabItem", "Bildirimler"),
        "settings.advancedTab": ("TabItem", "Gelişmiş"),
    }


def test_every_screen_and_dialog_has_its_window(built):
    windows = {n for n, o in built["objects"].items() if o["controlType"] == "Window"}
    assert windows == {
        f"{s}.window"
        for s in (
            "login",
            "main",
            "detail",
            "settings",
            "wizard",
            "discardDialog",
            "confirmDialog",
        )
    }


def test_hidden_tabs_and_pages_are_listed_too(built):
    """What the UIA dump alone would miss: an unselected tab, a wizard page not showing."""
    objects = built["objects"]
    assert objects["settings.emailNotificationsCheck"]["automationId"] == (
        "QApplication.settings.tabs.qt_tabwidget_stackedwidget."
        "notificationsTab.emailNotificationsCheck"
    )
    assert objects["wizard.summaryLabel"]["controlType"] == "Text"
    assert objects["wizard.startDateEdit"]["controlType"] == "Spinner"


def test_every_combo_box_lists_its_items_exactly_as_shown(built):
    objects = built["objects"]
    combos = [o for o in objects.values() if o["controlType"] == "ComboBox"]
    assert combos and all(o.get("items") for o in combos)
    assert "Kalite Güvence" in objects["wizard.departmentCombo"]["items"]  # SC-20
    assert not [o for o in objects.values() if "items" in o and o not in combos]


def test_caption_labels_are_left_out_and_checked_labels_are_in(built):
    objects = built["objects"]
    assert "login.userNameLabel" not in objects
    for name in (
        "login.statusLabel",  # SC-21, bug1
        "detail.statusLabel",  # SC-34, bug4
        "wizard.summaryLabel",  # SC-20, bug3
        "main.resultCountLabel",
    ):
        assert objects[name]["controlType"] == "Text"


def test_a_description_with_no_object_fails_the_build(monkeypatch):
    nl_objects.offscreen_app()
    monkeypatch.setitem(nl_objects.DESCRIPTIONS, "login.goneButton", "yok")
    with pytest.raises(ValueError, match="login.goneButton"):
        nl_objects.build()
