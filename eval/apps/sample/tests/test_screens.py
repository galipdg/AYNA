"""Every screen's controls, counted without a display (#33, criterion 1).

`uia_check.py` checks the same criterion through UI Automation, but it can only see the
page that is **showing**: the settings screen's other two tabs and the wizard's other two
pages are not in the tree at all. So the count per tab and per page is done here, on the
widgets themselves, with Qt's offscreen platform -- which also means macOS runs it.

Criterion 2 (an AutomationId on every control) stays with `uia_check.py`, because that is
how the criterion is worded and because only UI Automation can say what the id became.
"""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QTabBar,
    QTableWidget,
    QWidget,
)

import windows

#: #33's first criterion.
MIN_INTERACTIVE = 8

#: Widget classes a user acts on. A spin box and a date edit own an internal `QLineEdit`
#: (`qt_spinbox_lineedit`), so a widget whose parent is itself one of these is Qt's own
#: machinery and does not count twice. A `QTabBar` is kept even though Qt named it
#: (`qt_tabwidget_tabbar`): it is a control the tester clicks, and UI Automation reports it
#: as the screen's `Tab`.
INTERACTIVE = (
    QPushButton,
    QCheckBox,
    QComboBox,
    QLineEdit,
    QPlainTextEdit,
    QSpinBox,
    QDateEdit,
    QTableWidget,
    QTabBar,
)


@pytest.fixture(scope="module")
def qt_app():
    """A QApplication on Qt's offscreen platform, so these tests need no display.

    The platform is chosen in Qt's own argv and **not** with `QT_QPA_PLATFORM`: an
    environment variable set here is inherited by every process started later in the same
    pytest run, and `tests/test_sample_uia.py` and the trial app's UIA tests start the real
    apps as child processes -- which would then come up with no window at all and never be
    found through UI Automation. Measured 2026-11-12: with the variable set, all 25 UIA
    tests here and the trial app's 5 timed out.
    """
    app = QApplication.instance() or QApplication(["pytest", "-platform", "offscreen"])
    yield app


def interactive_controls(window: QWidget) -> list[QWidget]:
    """The controls of `window` that are on the page or tab currently chosen.

    `isVisibleTo` answers "would this be visible if the window were shown", so nothing has
    to be put on screen and a hidden wizard page or an unselected tab is excluded exactly
    as UI Automation would exclude it.
    """
    found = []
    for widget in window.findChildren(QWidget):
        if not isinstance(widget, INTERACTIVE):
            continue
        if isinstance(widget.parentWidget(), INTERACTIVE):
            continue  # a spin box's own line edit, not a control of its own
        if widget.isVisibleTo(window):
            found.append(widget)
    return found


def names(window: QWidget) -> set[str]:
    return {control.objectName() for control in interactive_controls(window)}


@pytest.mark.parametrize(
    "factory",
    [
        windows.LoginWindow,
        windows.MainWindow,
        windows.DetailWindow,
        windows.SettingsWindow,
    ],
    ids=["login", "main", "detail", "settings"],
)
def test_a_screen_has_at_least_eight_interactive_controls(qt_app, factory):
    window = factory()
    controls = interactive_controls(window)
    assert len(controls) >= MIN_INTERACTIVE, (
        f"{factory.__name__} has {len(controls)}: {sorted(names(window))}"
    )


def test_every_control_of_every_screen_has_an_object_name(qt_app):
    """The source half of criterion 2: a control we build is never left unnamed.

    An objectName is what becomes the AutomationId, so a missing one here is a control the
    repository could only find by its text. Qt's own internals (`qt_*`) are not ours.
    """
    for factory in (
        windows.LoginWindow,
        windows.MainWindow,
        windows.DetailWindow,
        windows.SettingsWindow,
        windows.WizardWindow,
    ):
        window = factory()
        unnamed = [
            type(widget).__name__
            for widget in window.findChildren(QWidget)
            if isinstance(widget, INTERACTIVE) and not widget.objectName()
        ]
        assert not unnamed, f"{factory.__name__} has unnamed controls: {unnamed}"


def test_every_settings_tab_has_at_least_eight_interactive_controls(qt_app):
    # The tab bar, Kaydet and Kapat are on every tab, so each tab's own four controls are
    # what make up the rest. SC-16 clicks the second tab, so it is not enough for the first
    # one to be rich.
    window = windows.SettingsWindow()
    for index in range(window.tabs.count()):
        window.tabs.setCurrentIndex(index)
        controls = interactive_controls(window)
        assert len(controls) >= MIN_INTERACTIVE, (
            f"tab {window.tabs.tabText(index)!r} has {len(controls)}: "
            f"{sorted(names(window))}"
        )


def test_every_wizard_page_has_at_least_eight_interactive_controls(qt_app):
    window = windows.WizardWindow()
    seen = []
    for page in range(1, windows.WizardWindow.PAGES + 1):
        window._page = page
        window._show_page()
        controls = interactive_controls(window)
        seen.append(sorted(names(window)))
        assert len(controls) >= MIN_INTERACTIVE, (
            f"wizard page {page} has {len(controls)}: {sorted(names(window))}"
        )
    # The pages really are different pages, not the same controls three times.
    assert seen[0] != seen[1] != seen[2]


def test_the_version_is_in_every_window_title(qt_app):
    """#33 asks for the version in the title bar; #46 and #47 ship changed copies."""
    for factory in (
        windows.LoginWindow,
        windows.MainWindow,
        windows.DetailWindow,
        windows.SettingsWindow,
        windows.WizardWindow,
    ):
        title = factory().windowTitle()
        assert windows.t.VERSION in title, title
        assert windows.t.APP_NAME in title, title


def test_the_grid_selects_whole_rows(qt_app):
    """Measured in `eval/spikes/grid-probes.md`: with Qt's default `SelectItems` a
    SelectionItem.Select() on a cell selects that cell alone, while every row check still
    passes -- so the step schema's SelectRow would be quietly false on this app."""
    # The window has to stay referenced: it owns the grid, and a collected window takes
    # the C++ object with it ("Internal C++ object already deleted").
    window = windows.MainWindow()
    behaviour = window.customer_grid.selectionBehavior()
    assert behaviour == QTableWidget.SelectionBehavior.SelectRows


def test_the_grid_is_not_editable_so_a_click_cannot_change_the_data(qt_app):
    window = windows.MainWindow()
    assert (
        window.customer_grid.editTriggers() == QTableWidget.EditTrigger.NoEditTriggers
    )


def test_the_search_fills_the_grid_and_enables_the_open_button(qt_app):
    """SC-18 without the wait: the timer's work, called directly.

    What the scenario is about is that `openButton` is disabled from the click until the
    rows arrive, which is the state playback has to wait out.
    """
    window = windows.MainWindow(delay_ms=10_000)
    window.search_input.setText("Yılmaz")
    window.on_search()
    assert not window.open_button.isEnabled()
    assert window.customer_grid.rowCount() == 0

    window.fill_grid()  # what the timer does when the delay is over
    assert window.open_button.isEnabled()
    assert window.customer_grid.rowCount() == 2
    assert window.customer_grid.item(0, 1).text() == "Yılmaz"


def test_clearing_the_search_takes_the_open_button_back_with_it(qt_app):
    window = windows.MainWindow(delay_ms=0)
    window.search_input.setText("Yılmaz")
    window.on_search()
    window.fill_grid()
    window.on_clear()
    assert not window.open_button.isEnabled()
    assert window.customer_grid.rowCount() == 0
    assert window.search_input.text() == ""


def test_an_edited_detail_form_knows_it_is_edited(qt_app):
    """What makes SC-22's dialog appear; the dialog itself needs a real desktop."""
    window = windows.DetailWindow()
    window.show_customer(windows.model.CUSTOMERS[0])
    assert not window.is_edited()
    window.name_input.setText("Başka İsim")
    assert window.is_edited()
    window.on_save()
    assert not window.is_edited(), "a saved form has nothing to discard"


def test_saving_without_a_name_is_refused_and_keeps_the_form_dirty(qt_app):
    window = windows.DetailWindow()
    window.show_customer(windows.model.CUSTOMERS[0])
    window.name_input.setText("   ")
    window.on_save()
    assert window.status_label.text() == windows.t.DETAIL_NAME_REQUIRED
    assert window.is_edited(), "a refused save must not count as saved"


def test_the_wizard_refuses_to_leave_page_one_without_a_name(qt_app):
    window = windows.WizardWindow()
    window.on_next()
    assert window.status_label.text() == windows.t.WIZARD_NAME_REQUIRED
    assert window.step_label.text() == windows.t.WIZARD_STEP.format(current=1, total=3)


def test_the_wizard_summary_names_the_chosen_department(qt_app):
    """SC-20's Verify step reads this label's text, which is its UIA Name."""
    window = windows.WizardWindow()
    window.name_input.setText("Ayşe Çelik")
    window.on_next()
    window.department_combo.setCurrentText("Kalite Güvence")
    window.on_next()
    assert "Kalite Güvence" in window.summary_label.text()
    assert "Ayşe Çelik" in window.summary_label.text()
    assert window.finish_button.isEnabled()


def test_the_wizard_will_not_finish_before_the_confirmation_box_is_ticked(qt_app):
    """The check that keeps SC-20's dialog from opening by accident."""
    window = windows.WizardWindow()
    window.name_input.setText("Ayşe Çelik")
    window.on_next()
    window.on_next()
    window.on_finish()  # no dialog: the box is clear, so this returns at once
    assert window.status_label.text() == windows.t.WIZARD_NOT_CONFIRMED
