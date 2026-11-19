"""#46's change versions through UI Automation: is the ground truth what a provider reports?

`ground_truth.json` is generated from the Qt side (`ground_truth.py`), on the three rules this
app's UIA behaviour was measured by. That makes the *mapping* certain -- it is what the patch
reports it did -- but the property values on each side are derived, and two of them had never
been read off a real provider before this file existed:

1. what UIA reports for a control whose `objectName` was cleared (v2e),
2. which ControlType a `QGroupBox` container gets (v2d, v2f).

So every row of the mapping is checked here against the real tree, screen by screen and
version by version. A row that disagrees means the derivation is wrong and the mapping has to
be regenerated -- not that the app is broken.

Windows only, and skipped elsewhere by the conftest.
"""

from __future__ import annotations

import json
import sys

import pytest

pytestmark = pytest.mark.windows

if sys.platform != "win32":  # keep pywinauto off other platforms
    pytest.skip("windows-only module", allow_module_level=True)

import ground_truth
import uia_check

GROUND_TRUTH = json.loads(ground_truth.GROUND_TRUTH_PATH.read_text(encoding="utf-8"))

#: One case per (version, screen) the version changes: 17 app launches in total.
CASES = [
    (variant_id, screen)
    for variant_id, variant in GROUND_TRUTH["variants"].items()
    for screen in variant["screens"]
]


@pytest.fixture
def changed_screen(request):
    """Start one screen of one version, yield (rows, window), and kill the process after."""
    variant, screen = request.param
    proc = uia_check.launch_app(screen, delay_ms=0, variant=variant)
    try:
        window = uia_check.find_window(screen)
        yield uia_check.collect_controls(window), window
    finally:
        uia_check.kill_process_tree(proc)


def mappings(variant: str, screen: str) -> list[dict]:
    return [
        row
        for row in GROUND_TRUTH["variants"][variant]["mappings"]
        if row["screen"] == screen
    ]


def by_automation_id(rows: list[dict], automation_id: str) -> list[dict]:
    """The app's own widgets with that id.

    `is_app_widget` is not optional here: a `QTableWidget`'s inner Pane and its four Headers
    are not Qt widgets and inherit the **grid's** AutomationId, so an unfiltered lookup for
    the grid finds six elements (measured 2026-11-15).
    """
    return [
        row
        for row in rows
        if row["automation_id"] == automation_id and uia_check.is_app_widget(row)
    ]


def by_name_and_class(rows: list[dict], name: str, class_name: str) -> list[dict]:
    return [
        row for row in rows if row["name"] == name and row["class_name"] == class_name
    ]


@pytest.mark.parametrize(
    "changed_screen", CASES, indirect=True, ids=lambda case: f"{case[0]}-{case[1]}"
)
def test_every_mapped_control_is_in_the_tree_as_the_mapping_says(
    changed_screen, request
):
    """The `new` side of every row, element by element, against the live tree.

    The title is checked here rather than in a test of its own: each case costs an app
    launch, and a test that only reads the title would double the suite's 17 of them.
    """
    rows, window = changed_screen
    variant, screen = request.node.callspec.params["changed_screen"]
    assert f"1.0-{variant} - " in window.window_text()
    for mapping in mappings(variant, screen):
        new = mapping["new"]
        where = f"{variant} {screen}.{mapping['control']}"
        if new is None:
            # A removed control: nothing with its old id and nothing of its class with its
            # old name is left on the screen.
            old = mapping["old"]
            assert not by_automation_id(rows, old["automationId"]), where
            assert not by_name_and_class(rows, old["name"], old["className"]), where
            continue
        if new["automationId"]:
            found = by_automation_id(rows, new["automationId"])
        else:
            found = by_name_and_class(rows, new["name"], new["className"])
        assert len(found) == 1, f"{where}: found {len(found)} elements"
        element = found[0]
        assert element["automation_id"] == new["automationId"], where
        assert element["name"] == new["name"], where
        assert element["class_name"] == new["className"], where
        if new["controlType"] is not None:
            assert element["control_type"] == new["controlType"], where


@pytest.mark.parametrize(
    "changed_screen",
    [case for case in CASES if case[0] == "v2e"],
    indirect=True,
    ids=lambda case: f"{case[0]}-{case[1]}",
)
def test_a_cleared_object_name_falls_back_to_the_class_name(changed_screen, request):
    """The first open question, and the answer was not the one the mapping first predicted.

    A control with no `objectName` is **not** a control without an AutomationId: Qt puts its
    class name in the path, so `login.loginButton` becomes
    `QApplication.login.QPushButton`. Three consequences, which is why v2e earns its place:

    * the id is no longer the logical name a scenario was written against;
    * it is not unique either -- two same-class siblings that both lose their name would
      share one id;
    * and #33's "an AutomationId on every control" still **passes**, so a check that only
      counts missing ids cannot see this change at all.
    """
    rows, _window = changed_screen
    variant, screen = request.node.callspec.params["changed_screen"]
    cleared = [
        mapping
        for mapping in mappings(variant, screen)
        if mapping["kind"] == "id-removed"
    ]
    assert cleared, f"{variant} {screen} has no id-removed row"
    for mapping in cleared:
        where = f"{screen}.{mapping['control']}"
        new = mapping["new"]
        found = by_name_and_class(rows, new["name"], new["className"])
        assert len(found) == 1, where
        assert found[0]["automation_id"] == new["automationId"], where
        assert found[0]["automation_id"].endswith("." + new["className"]), where
        assert mapping["control"] not in found[0]["automation_id"], where
        assert found[0]["control_type"] == new["controlType"], where
    # The measurement, stated the way it surprised us: the dump's own criterion is still met.
    assert uia_check.missing_automation_ids(rows) == []


@pytest.mark.parametrize(
    "changed_screen",
    [("v2d", "login"), ("v2d", "main"), ("v2d", "detail")],
    indirect=True,
    ids=lambda case: f"{case[0]}-{case[1]}",
)
def test_a_new_container_is_in_the_tree_with_the_controls_inside_it(
    changed_screen, request
):
    """The second open question: a `QGroupBox` is in the tree, and what its ControlType is.

    The mapping leaves the container's own ControlType out rather than guessing it, so this
    test pins what a provider actually says -- and that the moved controls hang below it.
    """
    rows, _window = changed_screen
    _variant, screen = request.node.callspec.params["changed_screen"]
    groups = [row for row in rows if row["class_name"] == "QGroupBox"]
    assert len(groups) == 1, f"{screen}: {len(groups)} group boxes"
    group = groups[0]
    assert group["automation_id"].startswith(f"QApplication.{screen}.")
    assert group["control_type"] == "Group"
    inside = [
        row
        for row in rows
        if row["automation_id"].startswith(group["automation_id"] + ".")
    ]
    assert inside, f"{screen}: nothing below {group['automation_id']}"
