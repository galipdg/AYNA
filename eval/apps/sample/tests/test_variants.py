"""#46's change versions, on Qt's offscreen platform so macOS runs them too.

Three of the issue's criteria are checked here and not by eye:

* **at least five change versions** -- `test_at_least_five_versions`, and that each of the five
  change kinds is some version's subject;
* **a ground-truth mapping for every changed control** -- `test_every_changed_control_is_in_the_mapping`
  diffs the whole screen itself, so a control the change set does not name but the change moved
  anyway has to be in `ground_truth.json`;
* **a change log describing each change** -- `test_change_log_covers_every_version` reads
  `variants.md`.

The fourth thing these tests are for is the one a reviewer cannot see: a retype and a removal
*swap or delete a widget*, and the window still holds it as an attribute. So every version is
also played through the behaviour of the screens it touches, which is what would die on a
dangling pointer.
"""

from __future__ import annotations

import json

import pytest
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QGroupBox,
    QLabel,
    QLineEdit,
    QWidget,
)

import ground_truth
import texts
import variant_patch
import variants
import windows
from variants import (
    ID_REMOVED,
    MOVE,
    REMOVED,
    RENAME,
    REPARENT,
    RETYPE,
    VARIANTS,
)

#: The issue's first criterion.
MIN_VERSIONS = 5

CHANGE_LOG = ground_truth.GROUND_TRUTH_PATH.parent / "variants.md"


@pytest.fixture(scope="module")
def qt_app():
    """A `QApplication` with no display; the platform is in Qt's argv, never in the
    environment (`tests/test_screens.py` says what that variable did to the UIA tests)."""
    yield QApplication.instance() or QApplication(["pytest", "-platform", "offscreen"])


@pytest.fixture(autouse=True)
def no_active_variant():
    """Leave the app unchanged for the next test whatever this one set."""
    yield
    variant_patch.set_active(variants.BASELINE)


@pytest.fixture(scope="module")
def ground_truth_document(qt_app) -> dict:
    return json.loads(ground_truth.GROUND_TRUTH_PATH.read_text(encoding="utf-8"))


def screen_of(variant: str, screen: str) -> QWidget:
    return ground_truth.build_screen(screen, variant)


# --- the spec ------------------------------------------------------------------------------


def test_spec_is_sound():
    assert variants.validate() == []


def test_at_least_five_versions():
    assert len(VARIANTS) >= MIN_VERSIONS


def test_every_change_kind_is_some_version_s_subject():
    subjects = {variant.kind for variant in VARIANTS.values()}
    assert {RENAME, MOVE, RETYPE, REPARENT, ID_REMOVED, "combined"} <= subjects


def test_the_combined_version_combines_all_five():
    kinds = {change.kind for change in VARIANTS["v2f"].changes}
    assert {RENAME, MOVE, RETYPE, REPARENT, ID_REMOVED, REMOVED} == kinds


def test_every_target_is_a_control_of_its_v1_screen(qt_app):
    missing = []
    for variant in VARIANTS.values():
        for change in variant.changes:
            window = ground_truth.build_screen(change.screen)
            if window.findChild(QWidget, change.target) is None:
                missing.append(f"{variant.id} {change.screen}.{change.target}")
    assert missing == []


# --- what each kind does to the widgets ----------------------------------------------------


def test_rename_keeps_the_id_and_changes_the_name(qt_app):
    login = screen_of("v2a", "login")
    button = login.findChild(QWidget, "loginButton")
    assert button.text() == "Oturum aç"
    assert button.objectName() == "loginButton"
    assert (
        login.findChild(QWidget, "userNameInput").accessibleName() == "Kullanıcı kodu"
    )


def test_move_keeps_everything_but_the_place(qt_app):
    login = screen_of("v2b", "login")
    row = variant_patch.owning_layout(login.findChild(QWidget, "loginButton"))
    order = [row.itemAt(index).widget().objectName() for index in range(row.count())]
    assert order == ["exitButton", "clearButton", "loginButton"]

    detail = screen_of("v2b", "detail")
    form = variant_patch.owning_layout(detail.findChild(QWidget, "departmentCombo"))
    assert form.getWidgetPosition(detail.findChild(QWidget, "departmentCombo"))[0] == 0
    # The label comes along, or the moved row would be a different change from the declared.
    assert form.getWidgetPosition(detail.findChild(QWidget, "departmentLabel"))[0] == 0


def test_retype_changes_the_class_and_keeps_the_id(qt_app):
    login = screen_of("v2c", "login")
    heading = login.findChild(QWidget, "headingLabel")
    assert isinstance(heading, QLineEdit)
    assert heading.isReadOnly()
    # The string moves from the Name to the value: that is the change's whole point.
    assert heading.text() == texts.LOGIN_HEADING
    assert ground_truth.uia_name(heading) == ""

    remember = login.findChild(QWidget, "rememberMeCheck")
    assert isinstance(remember, QComboBox)
    assert [remember.itemText(i) for i in range(remember.count())] == ["Hayır", "Evet"]
    assert remember.accessibleName() == texts.LOGIN_REMEMBER_ME


def test_retype_rebinds_the_window_s_attribute(qt_app):
    """Without this the app would call `setText` on a deleted C++ object and die."""
    main = screen_of("v2c", "main")
    assert isinstance(main.result_count_label, QLineEdit)
    main.result_count_label.setText("x")


def test_reparent_moves_the_control_and_lengthens_its_id(qt_app):
    login = screen_of("v2d", "login")
    group = login.findChild(QGroupBox, "credentialsGroup")
    assert group is not None
    user_name = login.findChild(QWidget, "userNameInput")
    assert user_name.parentWidget() is group
    assert (
        ground_truth.automation_id(user_name)
        == "QApplication.login.credentialsGroup.userNameInput"
    )
    # The label is inside too, so the field keeps the caption it is recognised by.
    assert login.findChild(QWidget, "userNameLabel").parentWidget() is group


def test_id_removed_clears_only_the_id(qt_app):
    login = screen_of("v2e", "login")
    buttons = [
        child
        for child in login.findChildren(QWidget)
        if getattr(child, "text", None) is not None
        and not isinstance(child, QLabel)
        and child.text() == texts.LOGIN_BUTTON
    ]
    assert len(buttons) == 1
    assert buttons[0].objectName() == ""
    assert login.findChild(QWidget, "loginButton") is None


def test_removed_takes_the_control_out_and_unbinds_it(qt_app):
    main = screen_of("v2f", "main")
    assert main.findChild(QWidget, "wizardButton") is None
    assert main.wizard_button is None


def test_the_untouched_screens_only_get_the_version_in_the_title(qt_app):
    variant_patch.set_active("v2f")
    settings = windows.SettingsWindow()
    assert settings.windowTitle() == "AYNA Örnek 1.0-v2f - Ayarlar"
    assert settings.findChild(QWidget, "saveButton") is not None


def test_the_title_says_which_version_it_is(qt_app):
    assert screen_of("v2a", "login").windowTitle() == "AYNA Örnek 1.0-v2a - Giriş"
    assert ground_truth.build_screen("login").windowTitle() == "AYNA Örnek 1.0 - Giriş"


def test_the_hook_changes_the_windows_a_screen_opens_later(qt_app):
    """A run that logs in has to reach the changed list screen, not the v1 one."""
    variant_patch.set_active("v2f")
    login = windows.LoginWindow(delay_ms=0)
    login.user_name_input.setText("admin")
    login.password_input.setText("admin")
    login.on_login()
    assert login.main_window is not None
    assert login.main_window.findChild(QWidget, "searchButton").text() == "Bul"


# --- the screens still work ----------------------------------------------------------------


@pytest.mark.parametrize("variant", list(VARIANTS))
def test_every_version_still_plays_its_screens(qt_app, variant):
    """The behaviour of each changed screen, after the widgets were swapped around.

    A retype and a removal replace or delete a widget the window holds as an attribute, so
    this is the test that would crash -- not with an assertion but with Qt taking the process
    down on a deleted object.
    """
    variant_patch.set_active(variant)
    for screen in VARIANTS[variant].screens():
        if screen == "login":
            login = windows.LoginWindow(delay_ms=0)
            login.user_name_input.setText("admin")
            login.password_input.setText("nope")
            login.on_login()
            login.on_clear()
            login.on_forgot_password()
        elif screen == "main":
            main = windows.MainWindow(delay_ms=0)
            main.on_search()
            main.fill_grid()
            assert main.customer_grid.rowCount() > 0
            main.on_open()
            main.on_clear()
        else:
            detail = windows.DetailWindow()
            detail.name_input.setText("Ayşe Çelik")
            detail.email_input.setText("ayse@example.com")
            detail.on_save()
            detail.on_reset()


# --- the ground truth ----------------------------------------------------------------------


def test_ground_truth_json_is_what_the_generator_writes(qt_app, ground_truth_document):
    """The committed file is regenerated with `ground_truth.py --write`, never edited."""
    assert ground_truth_document == ground_truth.generate()


def test_every_changed_control_is_in_the_mapping(qt_app, ground_truth_document):
    """The issue's second criterion, diffed on the screen rather than read off the spec.

    Every control whose description changed -- including one that only moved because another
    control's change pushed it -- has to have a row, and a control that is gone has to have a
    row whose `new` is `null`.
    """
    for variant_id, variant in ground_truth_document["variants"].items():
        mapped = {(row["screen"], row["control"]) for row in variant["mappings"]}
        changed = set()
        for screen in variant["screens"]:
            before = ground_truth.index_screen(ground_truth.build_screen(screen))
            after = ground_truth.index_screen(
                ground_truth.build_screen(screen, variant_id)
            )
            for control, description in before.items():
                if after.get(control) != description:
                    changed.add((screen, control))
        assert changed == mapped, variant_id


def test_every_mapping_row_says_what_happened(ground_truth_document):
    for variant_id, variant in ground_truth_document["variants"].items():
        assert variant["mappings"], variant_id
        for row in variant["mappings"]:
            where = f"{variant_id} {row['screen']}.{row['control']}"
            assert row["old"] is not None, where
            assert row["old"]["automationId"], where
            assert row["kind"], where
            if row["declared"]:
                assert row["note"], where
            # `null` on the new side means the control is gone, which only a removal does.
            assert (row["new"] is None) == (row["kind"] == REMOVED), where


def test_the_mapping_is_not_about_qt_s_own_machinery(ground_truth_document):
    for variant in ground_truth_document["variants"].values():
        assert not [
            row for row in variant["mappings"] if row["control"].startswith("qt_")
        ]


def test_change_log_covers_every_version(ground_truth_document):
    """The issue's third criterion: the log describes each change, not just each version."""
    log = CHANGE_LOG.read_text(encoding="utf-8")
    for variant_id, variant in ground_truth_document["variants"].items():
        assert variant_id in log
        for row in variant["mappings"]:
            if row["declared"]:
                assert row["control"] in log, f"{variant_id} {row['control']}"
