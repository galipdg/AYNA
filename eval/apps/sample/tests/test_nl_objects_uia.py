"""`eval/nl/objects/sample.json` against the real UI Automation tree (Windows only, #36).

`nl_objects.py` builds the list from the widgets, assuming two rules: the AutomationId is the
objectName chain from the top-level window down, and the ControlType follows from the Qt
class. This walks every place an object can be -- all three settings tabs, all three wizard
pages and both dialogs -- and checks that each listed object is really there with that id
and that type. Five app launches, about half a minute.
"""

from __future__ import annotations

import json
import time

import pytest

import uia_check
from nl_objects import OUTPUT

pytestmark = pytest.mark.windows

SETTLE = 0.7


def _seen(window) -> set[tuple[str, str]]:
    return {
        (row["automation_id"], row["control_type"])
        for row in uia_check.collect_controls(window)
    }


def _dialog(owner, name: str):
    dialog = owner.child_window(auto_id=f"QApplication.{name}", control_type="Window")
    dialog.wait("exists", timeout=10)
    return dialog


def _walk_login(window):
    return _seen(window)


def _walk_main(window):
    return _seen(window)


def _walk_detail(window):
    seen = _seen(window)
    window.child_window(
        auto_id="QApplication.detail.nameInput", control_type="Edit"
    ).set_edit_text("x")
    window.child_window(
        auto_id="QApplication.detail.backButton", control_type="Button"
    ).click_input()
    return seen | _seen(_dialog(window, "discardDialog"))


def _walk_settings(window):
    seen = _seen(window)
    for tab in window.descendants(control_type="TabItem")[1:]:
        tab.select()
        time.sleep(SETTLE)
        seen |= _seen(window)
    return seen


def _walk_wizard(window):
    seen = _seen(window)
    window.child_window(
        auto_id="QApplication.wizard.nameInput", control_type="Edit"
    ).set_edit_text("Ayşe Çelik")
    next_button = window.child_window(
        auto_id="QApplication.wizard.nextButton", control_type="Button"
    )
    for _ in range(2):
        next_button.invoke()
        time.sleep(SETTLE)
        seen |= _seen(window)
    window.child_window(
        auto_id="QApplication.wizard.confirmCheck", control_type="CheckBox"
    ).toggle()
    window.child_window(
        auto_id="QApplication.wizard.finishButton", control_type="Button"
    ).click_input()
    return seen | _seen(_dialog(window, "confirmDialog"))


WALKS = {
    "login": _walk_login,
    "main": _walk_main,
    "detail": _walk_detail,
    "settings": _walk_settings,
    "wizard": _walk_wizard,
}

#: Which screen's walk reaches the objects of each window in the list.
SCREEN_OF = {"discardDialog": "detail", "confirmDialog": "wizard"}


@pytest.mark.parametrize("screen", list(WALKS))
def test_every_listed_object_is_in_the_tree_with_its_id_and_type(screen):
    objects = json.loads(OUTPUT.read_text(encoding="utf-8"))["objects"]
    expected = {
        name: (obj["automationId"], obj["controlType"])
        for name, obj in objects.items()
        if SCREEN_OF.get(name.split(".")[0], name.split(".")[0]) == screen
    }
    assert expected

    proc = uia_check.launch_app(screen)
    try:
        seen = WALKS[screen](uia_check.find_window(screen))
    finally:
        uia_check.kill_process_tree(proc)

    missing = {name: pair for name, pair in expected.items() if pair not in seen}
    assert not missing, f"not in the UIA tree as listed: {missing}"
