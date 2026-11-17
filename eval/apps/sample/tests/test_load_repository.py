"""`load_repository.py`'s choices, on hand-made captures (any platform, #55)."""

from __future__ import annotations

import load_repository as lr


def node(node_id: str, **element) -> dict:
    return {"id": node_id, "parentId": None, "element": element}


GRID = "QApplication.main.customerGrid"
TABS = "QApplication.settings.tabs.qt_tabwidget_tabbar"

CAPTURE = {
    "snapshotId": "s1",
    "elements": [
        node("e0", automationId="QApplication.main", controlType="Window", name="Ana"),
        node("e1", automationId=GRID, controlType="Table", name="Müşteri listesi"),
        node("e2", automationId=GRID, controlType="Header", name="Ad"),
        node("e3", automationId=GRID, controlType="DataItem", name="Ayşe"),
        node("e4", automationId="QApplication.main.searchInput", controlType="Edit"),
        node("e5", automationId=TABS, controlType="TabItem", name="Genel"),
        node("e6", automationId=TABS, controlType="TabItem", name="Bildirimler"),
    ],
}


def test_a_unique_automation_id_is_the_whole_primary():
    element = CAPTURE["elements"][4]["element"]
    assert lr.suggest_primary(element, CAPTURE["elements"]) == {
        "automationId": "QApplication.main.searchInput"
    }


def test_a_shared_automation_id_gets_the_property_that_makes_it_unique():
    grid = CAPTURE["elements"][1]["element"]
    tab = CAPTURE["elements"][6]["element"]
    assert lr.suggest_primary(grid, CAPTURE["elements"]) == {
        "automationId": GRID,
        "name": "Müşteri listesi",
    }
    assert lr.suggest_primary(tab, CAPTURE["elements"]) == {
        "automationId": TABS,
        "name": "Bildirimler",
    }


def test_the_fallback_takes_the_rest_up_to_control_type_and_skips_empty_values():
    element = {
        "automationId": GRID,
        "name": "Müşteri listesi",
        "nearestLabel": "",
        "controlType": "Table",
    }
    primary = {"automationId": GRID, "name": "Müşteri listesi"}
    assert lr.fallback_for(element, primary) == {"controlType": "Table"}


def test_tab_items_are_wanted_by_their_name():
    wanted = lr.wanted_objects({})
    assert wanted["settings.notificationsTab"] == {
        "automationId": TABS,
        "controlType": "TabItem",
        "name": "Bildirimler",
    }


def test_plan_takes_the_first_capture_that_finds_the_object_once():
    other = {
        "snapshotId": "s0",
        "elements": [node("e0", automationId=GRID, controlType="Pane")],
    }
    wanted = {
        "main.customerGrid": {"automationId": GRID, "controlType": "Table"},
        "main.gone": {
            "automationId": "QApplication.main.gone",
            "controlType": "Button",
        },
    }
    found, missing = lr.plan(wanted, [other, CAPTURE])
    assert [(name, snap["snapshotId"], n["id"]) for name, snap, n in found] == [
        ("main.customerGrid", "s1", "e1")
    ]
    assert missing == ["main.gone"]


def test_an_element_found_twice_is_not_found():
    twice = {
        "snapshotId": "s2",
        "elements": [
            node("e0", automationId=GRID, controlType="Table"),
            node("e1", automationId=GRID, controlType="Table"),
        ],
    }
    assert (
        lr.find_element(twice, {"automationId": GRID, "controlType": "Table"}) is None
    )
