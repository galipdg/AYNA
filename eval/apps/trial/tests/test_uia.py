"""UIA-level tests for the trial app: AutomationIds and the login flow.

These cover acceptance criteria 2 and 3 of issue #9 automatically, so they do
not have to be re-checked by hand at every weekly Windows session.
"""

from __future__ import annotations

import sys
import time

import pytest

pytestmark = pytest.mark.windows

if sys.platform != "win32":  # keep PySide6/pywinauto imports off other platforms
    pytest.skip("windows-only module", allow_module_level=True)

import uia_dump
from app import INVALID_MESSAGE, WELCOME_MESSAGE, WINDOW_TITLE

# Qt builds the AutomationId from the whole object chain, so every control is
# prefixed with the application and window objectName.
PREFIX = "QApplication.loginWindow."

EXPECTED_AUTOMATION_IDS = {
    PREFIX + name
    for name in (
        "usernameInput",
        "passwordInput",
        "rememberMeCheckBox",
        "loginButton",
        "statusLabel",
    )
}

# The status label is repainted after the click; give Qt a moment to publish it.
STATUS_TIMEOUT = 5.0


@pytest.fixture(scope="module")
def window():
    """Start the trial app once for this module and close it afterwards."""
    proc = uia_dump.launch_app()
    try:
        yield uia_dump.find_window()
    finally:
        uia_dump.kill_process_tree(proc)


def status_text(window) -> str:
    return window.child_window(
        auto_id=PREFIX + "statusLabel", control_type="Text"
    ).window_text()


def submit_login(window, username: str, password: str) -> str:
    """Fill the form, press Login and return the status label text."""
    before = status_text(window)
    window.child_window(
        auto_id=PREFIX + "usernameInput", control_type="Edit"
    ).set_edit_text(username)
    window.child_window(
        auto_id=PREFIX + "passwordInput", control_type="Edit"
    ).set_edit_text(password)
    window.child_window(auto_id=PREFIX + "loginButton", control_type="Button").click()

    deadline = time.time() + STATUS_TIMEOUT
    while time.time() < deadline:
        current = status_text(window)
        if current and current != before:
            return current
        time.sleep(0.1)
    return status_text(window)


def test_window_title_is_exposed_as_the_uia_name(window) -> None:
    assert window.element_info.name == WINDOW_TITLE


def test_every_input_and_button_has_an_automation_id(window) -> None:
    rows = uia_dump.collect_controls(window)
    assert uia_dump.required_widgets(rows), "no app widgets found to check"
    missing = uia_dump.missing_automation_ids(rows)
    assert missing == [], f"controls without an AutomationId: {missing}"


def test_expected_automation_ids_are_exposed(window) -> None:
    found = {row["automation_id"] for row in uia_dump.collect_controls(window)}
    assert EXPECTED_AUTOMATION_IDS <= found, (
        f"missing: {EXPECTED_AUTOMATION_IDS - found}"
    )


def test_valid_login_shows_welcome(window) -> None:
    message = submit_login(window, "admin", "admin")
    assert message == WELCOME_MESSAGE
    assert "Welcome" in message


def test_wrong_password_shows_error(window) -> None:
    assert submit_login(window, "admin", "wrong") == INVALID_MESSAGE
