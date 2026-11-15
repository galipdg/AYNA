"""#47's bug-injected versions, on Qt's offscreen platform so macOS runs them too.

Both of the issue's criteria are checked here rather than by eye:

* **at least five injected bugs** -- `test_at_least_five_bugs`, and that each of the five kinds
  the plan's SA-B row names is one version of its own;
* **for each bug, the scenario that must fail is named** --
  `test_every_bug_names_a_scenario_that_exists` looks the id *and the title* up in
  `docs/rs/scenarios.md`, so a renumbered or renamed scenario fails the suite instead of
  rotting in `bugs.md`.

The test that matters most is `test_every_version_shows_exactly_its_own_bug`: it reads all five
symptoms on every version, so a bug that also broke something else -- or a patch that leaked
out of `reset()` into the next test -- is a failure. "One functional bug each" is the whole
point of the set; a version with two is unusable as evidence, because a failing step could no
longer be attributed.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

import bug_patch
import bugs
import model
import texts
import windows
from bugs import BUGS, KINDS, NO_BUG

#: The issue's first criterion.
MIN_BUGS = 5

#: The reference scenarios each bug has to name. galip's file (`docs/rs/`), read-only here.
SCENARIOS = Path(__file__).resolve().parents[4] / "docs" / "rs" / "scenarios.md"

BUG_LOG = Path(__file__).resolve().parents[1] / "bugs.md"


@pytest.fixture(scope="module")
def qt_app():
    """A `QApplication` with no display; the platform is in Qt's argv, never in the
    environment (`tests/test_screens.py` says what that variable did to the UIA tests)."""
    yield QApplication.instance() or QApplication(["pytest", "-platform", "offscreen"])


@pytest.fixture(autouse=True)
def correct_app_again():
    """Take the bug back out, whatever the test did. The patches are process-wide."""
    yield
    bug_patch.reset()


def logged_in_window(delay_ms: int = 0):
    """Log in with the right credentials and return (login window, what it opened)."""
    login = windows.LoginWindow(delay_ms=delay_ms)
    login.user_name_input.setText("admin")
    login.password_input.setText("admin")
    login.on_login()
    return login, login.main_window


def symptoms(qt_app) -> set[str]:
    """Which of the five bugs' symptoms the app shows **right now**.

    One probe per bug, each the cheapest observation that distinguishes the broken build from
    the correct one -- and all five are run against every version, which is how "exactly one
    bug" is checked.
    """
    # Every window stays in a local until it has been read: a window that goes out of scope
    # takes its C++ children with it, and `window.save_button` would then be a dead pointer.
    found: set[str] = set()
    if "Hoş geldiniz" not in model.authenticate("admin", "admin").message:
        found.add("bug1")
    detail = windows.DetailWindow()
    if not detail.save_button.isEnabled():
        found.add("bug2")
    if "Kalite Güvence" not in model.wizard_summary("Ayşe", "Kalite Güvence", "Uzman"):
        found.add("bug3")
    if not model.validate_detail("", ""):
        found.add("bug4")
    login, opened = logged_in_window()
    if not isinstance(opened, windows.MainWindow):
        found.add("bug5")
    del detail, login
    return found


# --- the spec ------------------------------------------------------------------------------


def test_spec_is_sound():
    assert bugs.validate() == []


def test_at_least_five_bugs():
    assert len(BUGS) >= MIN_BUGS


def test_every_kind_the_plan_names_is_one_version():
    assert {bug.kind for bug in BUGS.values()} == set(KINDS)


def test_every_bug_names_a_scenario_that_exists():
    """The issue's second criterion, checked against the RS rather than against itself."""
    scenarios = SCENARIOS.read_text(encoding="utf-8")
    for bug in BUGS.values():
        heading = f"#### {bug.scenario} · {bug.scenario_title}"
        assert heading in scenarios, (
            f"{bug.id}: {heading!r} is not in docs/rs/scenarios.md"
        )


def test_four_of_the_five_bugs_are_the_ones_the_scenarios_ask_for():
    """The RS specifies four of them down to the control; those may not drift.

    SC-19 wants the detail form's Save button disabled, SC-21 a wrong text in the **login**
    status label, SC-31 a login that opens the wrong screen, SC-34 the missing validation.
    """
    by_scenario = {bug.scenario: bug for bug in BUGS.values()}
    assert by_scenario["SC-19"].control == "detail.saveButton"
    assert by_scenario["SC-21"].control == "login.statusLabel"
    assert by_scenario["SC-31"].screen == "login"
    assert by_scenario["SC-34"].control == "detail.nameInput"


# --- installing and taking back out --------------------------------------------------------


def test_installing_nothing_leaves_the_app_correct(qt_app):
    bug_patch.install(NO_BUG)
    assert bug_patch.active() == NO_BUG
    assert symptoms(qt_app) == set()


def test_an_unknown_bug_is_refused():
    with pytest.raises(ValueError):
        bug_patch.install("bug99")


def test_two_bugs_at_once_are_refused():
    """A version has exactly one bug, or a failing step cannot be attributed to one."""
    bug_patch.install("bug1")
    with pytest.raises(RuntimeError):
        bug_patch.install("bug2")


def test_reset_restores_the_correct_app(qt_app):
    bug_patch.install("bug4")
    assert symptoms(qt_app) == {"bug4"}
    bug_patch.reset()
    assert bug_patch.active() == NO_BUG
    assert symptoms(qt_app) == set()


@pytest.mark.parametrize("bug", list(BUGS))
def test_the_title_carries_the_bug_version(qt_app, bug):
    bug_patch.install(bug)
    assert texts.title(texts.LOGIN_SCREEN) == f"AYNA Örnek 1.0-{bug} - Giriş"
    login = windows.LoginWindow()
    assert login.windowTitle().endswith(f"1.0-{bug} - Giriş")


# --- one bug each, and the symptom is the declared one -------------------------------------


@pytest.mark.parametrize("bug", list(BUGS))
def test_every_version_shows_exactly_its_own_bug(qt_app, bug):
    bug_patch.install(bug)
    assert symptoms(qt_app) == {bug}


def test_bug1_shows_the_wrong_text_in_the_login_status_label(qt_app):
    """SC-21: the element is still found, so the category has to be 'assertion failed'."""
    correct = model.authenticate("admin", "admin").message
    bug_patch.install("bug1")
    login, _opened = logged_in_window()
    shown = login.status_label.text()
    assert shown != correct
    assert "admin" in shown, "the user name is still in it: the words are the bug"
    assert login.findChild(windows.QLabel, "statusLabel") is not None


def test_bug2_leaves_the_save_button_disabled_even_after_an_edit(qt_app):
    """SC-19: a wait that cannot succeed. Visible but never enabled, not missing."""
    bug_patch.install("bug2")
    detail = windows.DetailWindow()
    assert not detail.save_button.isEnabled()
    detail.name_input.setText("Ayşe Çelik")
    assert not detail.save_button.isEnabled()
    assert not detail.save_button.isHidden(), (
        "hidden would be element-not-found, not timeout"
    )
    assert detail.back_button.isEnabled(), "only the Save button is broken"


def test_bug3_drops_the_department_from_the_wizard_summary(qt_app):
    """SC-20's Verify step: the summary has to contain the department that was selected."""
    bug_patch.install("bug3")
    wizard = windows.WizardWindow()
    wizard.name_input.setText("Ayşe Çelik")
    wizard.on_next()
    assert wizard.department_combo.currentText() == "Kalite Güvence"
    wizard.on_next()
    summary = wizard.summary_label.text()
    assert "Kalite Güvence" not in summary
    assert "Ayşe Çelik" in summary, "only the department is wrong"


def test_bug4_saves_a_record_with_no_name(qt_app):
    """SC-34: the required-field rule is gone, and the e-mail rule still works."""
    bug_patch.install("bug4")
    detail = windows.DetailWindow()
    detail.name_input.setText("")
    detail.on_save()
    assert detail.status_label.text() == texts.DETAIL_SAVED

    detail.email_input.setText("not-an-address")
    detail.on_save()
    assert detail.status_label.text() == texts.DETAIL_EMAIL_INVALID


def test_bug5_opens_the_settings_screen_instead_of_the_list(qt_app):
    """SC-31: the login is fine, and every control of the next step's screen is gone."""
    bug_patch.install("bug5")
    login, opened = logged_in_window()
    assert login.status_label.text() == model.authenticate("admin", "admin").message
    assert isinstance(opened, windows.SettingsWindow)
    assert opened.findChild(windows.QWidget, "searchInput") is None


# --- the bug log ---------------------------------------------------------------------------


def test_bugs_md_describes_every_bug(qt_app):
    """Not a criterion of its own, but the log is what a reviewer and #62 read."""
    log = BUG_LOG.read_text(encoding="utf-8")
    for bug in BUGS.values():
        for fragment in (bug.id, bug.kind, bug.scenario, bug.control, bug.patched):
            assert fragment in log, f"{bug.id}: {fragment!r} is not in bugs.md"
