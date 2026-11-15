"""#47's bug-injected versions through UI Automation: is the symptom visible to a test?

`tests/test_bugs.py` proves the five bugs are in the code and that each version has exactly
one. This file asks the only question that matters for the negative scenarios: **can a step
see it** -- a Name through UI Automation, a Save button's `enabled`, a window that is not
there. Five bug versions, five app launches, one test each.

What these tests deliberately do **not** do is play the scenarios. SC-19's "category: timeout",
SC-21's "no healing proposal" and SC-31's rejected candidates are the agent's and the triage's
behaviour (#54, #62, #63), not the app's; this file pins the app-side symptom those scenarios
are written against, so a later failure is never mistaken for a broken build.

Windows only, and skipped elsewhere by the conftest.
"""

from __future__ import annotations

import sys
import time

import pytest

pytestmark = pytest.mark.windows

if sys.platform != "win32":  # keep pywinauto off other platforms
    pytest.skip("windows-only module", allow_module_level=True)

from pywinauto.findwindows import ElementNotFoundError

import model
import texts as t
import uia_check

SETTLE_TIMEOUT = 10.0


@pytest.fixture
def bugged_screen(request):
    """Start one screen of one bug version, yield the window, kill the process after."""
    bug, screen = request.param
    proc = uia_check.launch_app(screen, delay_ms=0, bug=bug)
    try:
        yield uia_check.find_window(screen)
    finally:
        uia_check.kill_process_tree(proc)


def _id(name: str) -> str:
    return f"QApplication.{name}"


def until(predicate, timeout: float = SETTLE_TIMEOUT):
    """Wait for `predicate()` to be truthy; a control not in the tree yet is "not ready"."""

    def value_or_missing():
        try:
            return predicate()
        except ElementNotFoundError:
            return None

    deadline = time.time() + timeout
    value = value_or_missing()
    while not value and time.time() < deadline:
        time.sleep(0.1)
        value = value_or_missing()
    return value


def text_of(window, name: str) -> str:
    return window.child_window(auto_id=_id(name), control_type="Text").window_text()


def edit(window, name: str):
    return window.child_window(auto_id=_id(name), control_type="Edit")


def button(window, name: str):
    return window.child_window(auto_id=_id(name), control_type="Button")


def log_in(window) -> None:
    edit(window, "login.userNameInput").set_edit_text("admin")
    edit(window, "login.passwordInput").set_edit_text("admin")
    button(window, "login.loginButton").click()


@pytest.mark.parametrize("bugged_screen", [("bug1", "login")], indirect=True)
def test_bug1_the_status_label_reads_the_wrong_thing(bugged_screen):
    """SC-21: the label is found and its Name is wrong, which is an assertion failure."""
    log_in(bugged_screen)
    status = until(lambda: text_of(bugged_screen, "login.statusLabel"))
    assert status, "the status label stayed empty, so the login did not even run"
    assert status != model.LOGIN_WELCOME.format(user="admin")
    assert "admin" in status, "the user name is still in it: the words are the bug"


@pytest.mark.parametrize("bugged_screen", [("bug2", "detail")], indirect=True)
def test_bug2_the_save_button_is_visible_and_never_enabled(bugged_screen):
    """SC-19: the condition that is never met is `enabled`, not existence."""
    save = button(bugged_screen, "detail.saveButton")
    assert save.exists() and save.is_visible(), "hidden would be element-not-found"
    assert not save.is_enabled()

    edit(bugged_screen, "detail.nameInput").set_edit_text("Ayşe Çelik")
    # Give it as long as SC-19's step would wait: this is the wait that cannot succeed.
    assert not until(save.is_enabled, timeout=5.0)
    assert button(bugged_screen, "detail.backButton").is_enabled(), (
        "only the Save button is broken"
    )


@pytest.mark.parametrize("bugged_screen", [("bug3", "wizard")], indirect=True)
def test_bug3_the_summary_has_lost_the_department(bugged_screen):
    """SC-20's Verify step, on the default department (`Kalite Güvence` is the first item)."""
    edit(bugged_screen, "wizard.nameInput").set_edit_text("Ayşe Çelik")
    button(bugged_screen, "wizard.nextButton").click()
    assert until(lambda: button(bugged_screen, "wizard.backButton").is_enabled())
    button(bugged_screen, "wizard.nextButton").click()

    summary = until(lambda: text_of(bugged_screen, "wizard.summaryLabel"))
    assert summary, "page three never showed its summary"
    assert "Ayşe Çelik" in summary, "only the department is wrong"
    assert model.DEPARTMENTS[0] not in summary


@pytest.mark.parametrize("bugged_screen", [("bug4", "detail")], indirect=True)
def test_bug4_saving_without_a_name_reports_success(bugged_screen):
    """SC-34: the required-field message a correct build shows is replaced by 'saved'."""
    edit(bugged_screen, "detail.nameInput").set_edit_text("")
    button(bugged_screen, "detail.saveButton").click()

    status = until(lambda: text_of(bugged_screen, "detail.statusLabel"))
    assert status == t.DETAIL_SAVED
    assert status != t.DETAIL_NAME_REQUIRED


@pytest.mark.parametrize("bugged_screen", [("bug5", "login")], indirect=True)
def test_bug5_the_login_opens_the_settings_window(bugged_screen):
    """SC-31: the login is fine, and the next step's screen is simply not there."""
    log_in(bugged_screen)
    status = until(lambda: text_of(bugged_screen, "login.statusLabel"))
    assert status == model.LOGIN_WELCOME.format(user="admin"), (
        "the login itself is correct"
    )

    settings = uia_check.find_window("settings", timeout=SETTLE_TIMEOUT)
    assert settings.exists()
    assert not settings.child_window(
        auto_id=_id("main.searchInput"), control_type="Edit"
    ).exists(timeout=0.5), "the list screen's controls are nowhere"

    from pywinauto import Desktop

    assert (
        not Desktop(backend="uia").window(class_name="MainWindow").exists(timeout=1.0)
    )
