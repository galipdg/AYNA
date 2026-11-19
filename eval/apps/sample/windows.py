"""The sample app's six screens (#33).

Each screen is its **own top-level window**, not a page of a stacked widget, for three
reasons: Qt builds the UIA AutomationId from the whole object chain, so a window of its own
keeps an id as short as `QApplication.login.userNameInput` -- the repository's logical name
with one prefix removed; a snapshot then covers one screen, which is what NFR-02 is scoped
to; and SC-22 needs a real second window to interrupt a run with.

What Qt exposes to UI Automation, measured on PySide6 6.12 / Windows 11
(`eval/apps/trial/README.md`, `memory-bank/learnings.md`):

* `objectName` becomes the **AutomationId**, as a dotted path over the object chain.
* `accessibleName` becomes the **Name** and *replaces* the Name the control would otherwise
  have. So it is set only where there is no useful visible text -- inputs, combo boxes, spin
  boxes, the grid -- and never on a window, a label, a button or a check box, where it would
  hide the title or the caption from every UIA client, our own checkpoints included.
* The Python class name becomes the **ClassName**, so `LoginWindow` finds the window.

The wizard's three pages are shown and hidden in place rather than put in a
`QStackedWidget`, which would add a level to every id on them
(`wizard.pages.page1.nameInput`). A `QTabWidget` cannot avoid that level, so the settings
screen's controls do carry their tab's name.
"""

from __future__ import annotations

from PySide6.QtCore import QDate, Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

import model
import texts as t
import variant_patch

# Every window's `__init__` ends with `variant_patch.apply_active(self)`, which is a no-op
# unless `sample_app.py --variant` asked for one of #46's change versions. The hook is in
# each constructor and not in `sample_app.py` because a screen opens the next one itself: a
# run that logs in has to reach the *changed* customer list, not the v1 one.

#: How long after a search the grid fills, in milliseconds. SC-18 is built on this delay:
#: playback has to wait for `openButton` to become enabled instead of sleeping. Configurable
#: from the command line (`--search-delay-ms`) so #46's and #47's versions, and a tester who
#: does not want to wait, can change it without touching the code.
DEFAULT_SEARCH_DELAY_MS = 3000


def _combo(name: str, items, accessible: str) -> QComboBox:
    """A read-only combo box with a stable Name.

    Without `accessibleName` a combo box's Name is its *current* text, which would make the
    element's identity change with the selection -- and `name` is a property the repository
    matches on (#11). The selected text stays readable through the selection itself.
    """
    combo = QComboBox()
    combo.setObjectName(name)
    combo.setAccessibleName(accessible)
    combo.addItems(list(items))
    return combo


def _line(name: str, accessible: str) -> QLineEdit:
    edit = QLineEdit()
    edit.setObjectName(name)
    edit.setAccessibleName(accessible)
    return edit


def _label(name: str, text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName(name)
    return label


def _button(name: str, text: str) -> QPushButton:
    button = QPushButton(text)
    button.setObjectName(name)
    return button


def _check(name: str, text: str) -> QCheckBox:
    box = QCheckBox(text)
    box.setObjectName(name)
    return box


class LoginWindow(QWidget):
    """Giris: user name, password, server, two check boxes and four buttons."""

    def __init__(self, delay_ms: int = DEFAULT_SEARCH_DELAY_MS) -> None:
        super().__init__()
        self.setObjectName("login")
        self.setWindowTitle(t.title(t.LOGIN_SCREEN))
        self.setMinimumWidth(420)
        self._delay_ms = delay_ms
        self.main_window: MainWindow | None = None

        self.user_name_input = _line("userNameInput", t.LOGIN_USER_NAME)
        self.password_input = _line("passwordInput", t.LOGIN_PASSWORD)
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.server_combo = _combo("serverCombo", t.LOGIN_SERVERS, t.LOGIN_SERVER)
        self.show_password_check = _check("showPasswordCheck", t.LOGIN_SHOW_PASSWORD)
        self.remember_me_check = _check("rememberMeCheck", t.LOGIN_REMEMBER_ME)
        self.login_button = _button("loginButton", t.LOGIN_BUTTON)
        self.clear_button = _button("clearButton", t.LOGIN_CLEAR)
        self.forgot_password_link = _button("forgotPasswordLink", t.LOGIN_FORGOT)
        self.forgot_password_link.setFlat(True)
        self.exit_button = _button("exitButton", t.LOGIN_EXIT)
        self.status_label = _label("statusLabel", "")

        form = QFormLayout()
        form.addRow(_label("userNameLabel", t.LOGIN_USER_NAME), self.user_name_input)
        form.addRow(_label("passwordLabel", t.LOGIN_PASSWORD), self.password_input)
        form.addRow(_label("serverLabel", t.LOGIN_SERVER), self.server_combo)

        buttons = QHBoxLayout()
        buttons.addWidget(self.login_button)
        buttons.addWidget(self.clear_button)
        buttons.addWidget(self.exit_button)

        layout = QVBoxLayout(self)
        layout.addWidget(_label("headingLabel", t.LOGIN_HEADING))
        layout.addLayout(form)
        layout.addWidget(self.show_password_check)
        layout.addWidget(self.remember_me_check)
        layout.addLayout(buttons)
        layout.addWidget(self.forgot_password_link)
        layout.addWidget(self.status_label)

        self.login_button.clicked.connect(self.on_login)
        self.user_name_input.returnPressed.connect(self.on_login)
        self.password_input.returnPressed.connect(self.on_login)
        self.clear_button.clicked.connect(self.on_clear)
        self.forgot_password_link.clicked.connect(self.on_forgot_password)
        self.exit_button.clicked.connect(self.close)
        self.show_password_check.toggled.connect(self.on_show_password)

        variant_patch.apply_active(self)

    def on_forgot_password(self) -> None:
        self.status_label.setText(t.LOGIN_FORGOT_HINT)

    def on_show_password(self, shown: bool) -> None:
        mode = QLineEdit.EchoMode.Normal if shown else QLineEdit.EchoMode.Password
        self.password_input.setEchoMode(mode)

    def on_clear(self) -> None:
        self.user_name_input.clear()
        self.password_input.clear()
        self.status_label.setText("")

    def on_login(self) -> None:
        """Show the result, and on success open the list screen beside this window.

        This window deliberately stays open: SC-14 and SC-21 check `login.statusLabel`
        *after* the login succeeded, which a window that closed itself could not offer.
        """
        result = model.authenticate(
            self.user_name_input.text(), self.password_input.text()
        )
        self.status_label.setText(result.message)
        if not result.ok:
            return
        if self.main_window is None:
            self.main_window = MainWindow(delay_ms=self._delay_ms)
        self.main_window.show()
        self.main_window.raise_()


class MainWindow(QWidget):
    """Musteriler: a search, filters, the results grid and the way to the other screens."""

    def __init__(self, delay_ms: int = DEFAULT_SEARCH_DELAY_MS) -> None:
        super().__init__()
        self.setObjectName("main")
        self.setWindowTitle(t.title(t.MAIN_SCREEN))
        self.resize(720, 420)
        self._delay_ms = delay_ms
        self._rows: list[model.Customer] = []
        self.detail_window: DetailWindow | None = None
        self.settings_window: SettingsWindow | None = None
        self.wizard_window: WizardWindow | None = None

        self.search_input = _line("searchInput", t.MAIN_SEARCH)
        self.search_button = _button("searchButton", t.MAIN_SEARCH_BUTTON)
        self.clear_button = _button("clearButton", t.MAIN_CLEAR)
        self.city_filter_combo = _combo("cityFilterCombo", model.CITIES, t.MAIN_CITY)
        self.active_only_check = _check("activeOnlyCheck", t.MAIN_ACTIVE_ONLY)
        self.refresh_button = _button("refreshButton", t.MAIN_REFRESH)
        self.open_button = _button("openButton", t.MAIN_OPEN)
        self.settings_button = _button("settingsButton", t.MAIN_SETTINGS)
        self.wizard_button = _button("wizardButton", t.MAIN_WIZARD)
        self.result_count_label = _label("resultCountLabel", "")

        self.customer_grid = QTableWidget(0, len(t.MAIN_COLUMNS))
        self.customer_grid.setObjectName("customerGrid")
        self.customer_grid.setAccessibleName(t.MAIN_HEADING)
        self.customer_grid.setHorizontalHeaderLabels(list(t.MAIN_COLUMNS))
        self.customer_grid.verticalHeader().setVisible(False)
        self.customer_grid.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        # Measured in `eval/spikes/grid-probes.md`: with Qt's default (SelectItems) a
        # SelectionItem.Select() on a cell selects that cell only, while every row check
        # still passes -- so the step schema's promise that SelectRow selects a row would
        # be quietly false. The sample app must select by row.
        self.customer_grid.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.customer_grid.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.customer_grid.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )

        top = QGridLayout()
        top.addWidget(_label("searchLabel", t.MAIN_SEARCH), 0, 0)
        top.addWidget(self.search_input, 0, 1)
        top.addWidget(self.search_button, 0, 2)
        top.addWidget(self.clear_button, 0, 3)
        top.addWidget(_label("cityLabel", t.MAIN_CITY), 1, 0)
        top.addWidget(self.city_filter_combo, 1, 1)
        top.addWidget(self.active_only_check, 1, 2)
        top.addWidget(self.refresh_button, 1, 3)

        buttons = QHBoxLayout()
        buttons.addWidget(self.open_button)
        buttons.addWidget(self.settings_button)
        buttons.addWidget(self.wizard_button)

        layout = QVBoxLayout(self)
        layout.addWidget(_label("headingLabel", t.MAIN_HEADING))
        layout.addLayout(top)
        layout.addWidget(self.customer_grid)
        layout.addWidget(self.result_count_label)
        layout.addLayout(buttons)

        self._timer = QTimer(self)
        self._timer.setObjectName("searchTimer")
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.fill_grid)

        self.search_button.clicked.connect(self.on_search)
        self.search_input.returnPressed.connect(self.on_search)
        self.refresh_button.clicked.connect(self.on_search)
        self.clear_button.clicked.connect(self.on_clear)
        self.open_button.clicked.connect(self.on_open)
        self.settings_button.clicked.connect(self.on_settings)
        self.wizard_button.clicked.connect(self.on_wizard)

        self.open_button.setEnabled(False)

        variant_patch.apply_active(self)

    def on_search(self) -> None:
        """Clear the grid, then fill it `delay_ms` later: the late control of SC-18."""
        self.customer_grid.setRowCount(0)
        self._rows = []
        self.open_button.setEnabled(False)
        self.result_count_label.setText(t.MAIN_SEARCHING)
        self._timer.start(self._delay_ms)

    def on_clear(self) -> None:
        self._timer.stop()
        self.search_input.clear()
        self.customer_grid.setRowCount(0)
        self._rows = []
        self.open_button.setEnabled(False)
        self.result_count_label.setText("")

    def fill_grid(self) -> None:
        """Put the matches in the grid and enable the Open button. The timer calls this."""
        self._rows = model.search_customers(
            self.search_input.text(),
            self.city_filter_combo.currentText(),
            self.active_only_check.isChecked(),
        )
        self.customer_grid.setRowCount(len(self._rows))
        for row, customer in enumerate(self._rows):
            values = (
                customer.first_name,
                customer.last_name,
                customer.city,
                customer.status,
            )
            for column, value in enumerate(values):
                self.customer_grid.setItem(row, column, QTableWidgetItem(value))
        self.result_count_label.setText(
            t.MAIN_FOUND.format(count=len(self._rows))
            if self._rows
            else t.MAIN_NONE_FOUND
        )
        # SC-18's actual assertion: the button becomes enabled only now, about 3 s after
        # the click, so playback has to wait for it rather than sleep.
        self.open_button.setEnabled(bool(self._rows))

    def add_customer(self, customer: model.Customer) -> None:
        """Put a row the wizard created at the top of the grid."""
        self._rows.insert(0, customer)
        self.customer_grid.insertRow(0)
        values = (
            customer.first_name,
            customer.last_name,
            customer.city,
            customer.status,
        )
        for column, value in enumerate(values):
            self.customer_grid.setItem(0, column, QTableWidgetItem(value))
        self.result_count_label.setText(t.MAIN_FOUND.format(count=len(self._rows)))
        self.open_button.setEnabled(True)

    def selected_customer(self) -> model.Customer | None:
        """The row the user picked, or the first one when nothing is selected."""
        row = self.customer_grid.currentRow()
        if 0 <= row < len(self._rows):
            return self._rows[row]
        return self._rows[0] if self._rows else None

    def on_open(self) -> None:
        customer = self.selected_customer()
        if customer is None:
            self.result_count_label.setText(t.MAIN_SELECT_FIRST)
            return
        if self.detail_window is None:
            self.detail_window = DetailWindow(self)
        self.detail_window.show_customer(customer)

    def on_settings(self) -> None:
        if self.settings_window is None:
            self.settings_window = SettingsWindow()
        self.settings_window.show()
        self.settings_window.raise_()

    def on_wizard(self) -> None:
        if self.wizard_window is None:
            self.wizard_window = WizardWindow(self)
        self.wizard_window.restart()
        self.wizard_window.show()
        self.wizard_window.raise_()


class DetailWindow(QWidget):
    """Musteri detayi: the form with the required field and the discard-changes dialog."""

    def __init__(self, main_window: MainWindow | None = None) -> None:
        super().__init__()
        self.setObjectName("detail")
        self.setWindowTitle(t.title(t.DETAIL_SCREEN))
        self.setMinimumWidth(460)
        self._main_window = main_window
        self._saved: tuple = ()

        self.name_input = _line("nameInput", t.DETAIL_NAME)
        self.email_input = _line("emailInput", t.DETAIL_EMAIL)
        self.department_combo = _combo(
            "departmentCombo", model.DEPARTMENTS, t.DETAIL_DEPARTMENT
        )
        self.city_combo = _combo("cityCombo", model.CITIES[1:], t.DETAIL_CITY)
        self.notes_input = QPlainTextEdit()
        self.notes_input.setObjectName("notesInput")
        self.notes_input.setAccessibleName(t.DETAIL_NOTES)
        self.notes_input.setFixedHeight(70)
        self.active_check = _check("activeCheck", t.DETAIL_ACTIVE)
        self.save_button = _button("saveButton", t.DETAIL_SAVE)
        self.reset_button = _button("resetButton", t.DETAIL_RESET)
        self.back_button = _button("backButton", t.DETAIL_BACK)
        self.status_label = _label("statusLabel", "")

        form = QFormLayout()
        form.addRow(_label("nameLabel", t.DETAIL_NAME), self.name_input)
        form.addRow(_label("emailLabel", t.DETAIL_EMAIL), self.email_input)
        form.addRow(
            _label("departmentLabel", t.DETAIL_DEPARTMENT), self.department_combo
        )
        form.addRow(_label("cityLabel", t.DETAIL_CITY), self.city_combo)
        form.addRow(_label("notesLabel", t.DETAIL_NOTES), self.notes_input)

        buttons = QHBoxLayout()
        buttons.addWidget(self.save_button)
        buttons.addWidget(self.reset_button)
        buttons.addWidget(self.back_button)

        layout = QVBoxLayout(self)
        layout.addWidget(_label("headingLabel", t.DETAIL_HEADING))
        layout.addLayout(form)
        layout.addWidget(self.active_check)
        layout.addLayout(buttons)
        layout.addWidget(self.status_label)

        self.save_button.clicked.connect(self.on_save)
        self.reset_button.clicked.connect(self.on_reset)
        self.back_button.clicked.connect(self.on_back)

        # The form as built *is* its saved state: the two combo boxes start on their first
        # item, so a hard-coded empty tuple would make an untouched form look edited and
        # the discard dialog would open on the way out of a form nobody changed.
        self._saved = self._values()

        variant_patch.apply_active(self)

    def show_customer(self, customer: model.Customer) -> None:
        """Load a row into the form and treat that state as saved."""
        self.name_input.setText(f"{customer.first_name} {customer.last_name}")
        self.email_input.setText("")
        self.city_combo.setCurrentText(customer.city)
        self.notes_input.setPlainText("")
        self.active_check.setChecked(customer.active)
        self.status_label.setText("")
        self._saved = self._values()
        self.show()
        self.raise_()

    def _values(self) -> tuple:
        return (
            self.name_input.text(),
            self.email_input.text(),
            self.department_combo.currentText(),
            self.city_combo.currentText(),
            self.notes_input.toPlainText(),
            self.active_check.isChecked(),
        )

    def is_edited(self) -> bool:
        return self._values() != self._saved

    def on_save(self) -> None:
        problems = model.validate_detail(
            self.name_input.text(), self.email_input.text()
        )
        if problems:
            self.status_label.setText(problems[0])
            return
        self._saved = self._values()
        self.status_label.setText(t.DETAIL_SAVED)

    def on_reset(self) -> None:
        name, email, department, city, notes, active = self._saved
        self.name_input.setText(name)
        self.email_input.setText(email)
        self.department_combo.setCurrentText(department)
        self.city_combo.setCurrentText(city)
        self.notes_input.setPlainText(notes)
        self.active_check.setChecked(active)
        self.status_label.setText("")

    def on_back(self) -> None:
        """Leaving an edited form asks first (SC-22), in an application-modal dialog."""
        if self.is_edited():
            dialog = QuestionDialog(
                "discardDialog", t.DISCARD_TITLE, t.DISCARD_QUESTION, self
            )
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
        self.hide()
        if self._main_window is not None:
            self._main_window.raise_()


class SettingsWindow(QWidget):
    """Ayarlar: three tabs, one of them with the e-mail-notifications check box (SC-16)."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("settings")
        self.setWindowTitle(t.title(t.SETTINGS_SCREEN))
        self.setMinimumWidth(460)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("tabs")

        general = QWidget()
        general.setObjectName("generalTab")
        self.theme_combo = _combo("themeCombo", t.SETTINGS_THEMES, t.SETTINGS_THEME)
        self.language_combo = _combo(
            "languageCombo", t.SETTINGS_LANGUAGES, t.SETTINGS_LANGUAGE
        )
        self.startup_check = _check("startupCheck", t.SETTINGS_STARTUP)
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setObjectName("timeoutSpin")
        self.timeout_spin.setAccessibleName(t.SETTINGS_TIMEOUT)
        self.timeout_spin.setRange(1, 600)
        self.timeout_spin.setValue(10)
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setObjectName("fontSizeSpin")
        self.font_size_spin.setAccessibleName(t.SETTINGS_FONT_SIZE)
        self.font_size_spin.setRange(8, 24)
        self.font_size_spin.setValue(10)
        general_form = QFormLayout(general)
        general_form.addRow(_label("themeLabel", t.SETTINGS_THEME), self.theme_combo)
        general_form.addRow(
            _label("languageLabel", t.SETTINGS_LANGUAGE), self.language_combo
        )
        general_form.addRow(
            _label("timeoutLabel", t.SETTINGS_TIMEOUT), self.timeout_spin
        )
        general_form.addRow(
            _label("fontSizeLabel", t.SETTINGS_FONT_SIZE), self.font_size_spin
        )
        general_form.addRow(self.startup_check)

        notifications = QWidget()
        notifications.setObjectName("notificationsTab")
        self.email_notifications_check = _check(
            "emailNotificationsCheck", t.SETTINGS_EMAIL_NOTIFICATIONS
        )
        self.desktop_notifications_check = _check(
            "desktopNotificationsCheck", t.SETTINGS_DESKTOP_NOTIFICATIONS
        )
        self.frequency_combo = _combo(
            "frequencyCombo", t.SETTINGS_FREQUENCIES, t.SETTINGS_FREQUENCY
        )
        self.email_address_input = _line("emailAddressInput", t.SETTINGS_EMAIL_ADDRESS)
        self.quiet_hours_check = _check("quietHoursCheck", t.SETTINGS_QUIET_HOURS)
        notifications_form = QFormLayout(notifications)
        notifications_form.addRow(self.email_notifications_check)
        notifications_form.addRow(self.desktop_notifications_check)
        notifications_form.addRow(self.quiet_hours_check)
        notifications_form.addRow(
            _label("frequencyLabel", t.SETTINGS_FREQUENCY), self.frequency_combo
        )
        notifications_form.addRow(
            _label("emailAddressLabel", t.SETTINGS_EMAIL_ADDRESS),
            self.email_address_input,
        )

        advanced = QWidget()
        advanced.setObjectName("advancedTab")
        self.log_level_combo = _combo(
            "logLevelCombo", t.SETTINGS_LOG_LEVELS, t.SETTINGS_LOG_LEVEL
        )
        self.cache_size_spin = QSpinBox()
        self.cache_size_spin.setObjectName("cacheSizeSpin")
        self.cache_size_spin.setAccessibleName(t.SETTINGS_CACHE_SIZE)
        self.cache_size_spin.setRange(16, 4096)
        self.cache_size_spin.setValue(256)
        self.proxy_input = _line("proxyInput", t.SETTINGS_PROXY)
        self.experimental_check = _check("experimentalCheck", t.SETTINGS_EXPERIMENTAL)
        self.defaults_button = _button("defaultsButton", t.SETTINGS_DEFAULTS)
        advanced_form = QFormLayout(advanced)
        advanced_form.addRow(
            _label("logLevelLabel", t.SETTINGS_LOG_LEVEL), self.log_level_combo
        )
        advanced_form.addRow(_label("proxyLabel", t.SETTINGS_PROXY), self.proxy_input)
        advanced_form.addRow(
            _label("cacheSizeLabel", t.SETTINGS_CACHE_SIZE), self.cache_size_spin
        )
        advanced_form.addRow(self.experimental_check)
        advanced_form.addRow(self.defaults_button)

        self.tabs.addTab(general, t.SETTINGS_GENERAL_TAB)
        self.tabs.addTab(notifications, t.SETTINGS_NOTIFICATIONS_TAB)
        self.tabs.addTab(advanced, t.SETTINGS_ADVANCED_TAB)

        self.save_button = _button("saveButton", t.SETTINGS_SAVE)
        self.close_button = _button("closeButton", t.SETTINGS_CLOSE)
        self.status_label = _label("statusLabel", "")

        buttons = QHBoxLayout()
        buttons.addWidget(self.save_button)
        buttons.addWidget(self.close_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.tabs)
        layout.addLayout(buttons)
        layout.addWidget(self.status_label)

        self.save_button.clicked.connect(self.on_save)
        self.close_button.clicked.connect(self.close)
        self.defaults_button.clicked.connect(self.on_defaults)

        variant_patch.apply_active(self)

    def on_save(self) -> None:
        self.status_label.setText(t.SETTINGS_SAVED)

    def on_defaults(self) -> None:
        self.theme_combo.setCurrentIndex(0)
        self.language_combo.setCurrentIndex(0)
        self.startup_check.setChecked(False)
        self.timeout_spin.setValue(10)
        self.email_notifications_check.setChecked(False)
        self.desktop_notifications_check.setChecked(False)
        self.frequency_combo.setCurrentIndex(0)
        self.email_address_input.clear()
        self.quiet_hours_check.setChecked(False)
        self.proxy_input.clear()
        self.log_level_combo.setCurrentIndex(0)
        self.cache_size_spin.setValue(256)
        self.experimental_check.setChecked(False)
        self.status_label.setText(t.SETTINGS_RESET)


class WizardWindow(QWidget):
    """Sihirbaz: three pages in one window, so every id stays `wizard.<control>`."""

    PAGES = 3

    def __init__(self, main_window: MainWindow | None = None) -> None:
        super().__init__()
        self.setObjectName("wizard")
        self.setWindowTitle(t.title(t.WIZARD_SCREEN))
        self.setMinimumWidth(460)
        self._main_window = main_window
        self._page = 1

        self.step_label = _label("stepLabel", "")
        self.page_label = _label("pageLabel", "")

        self.name_input = _line("nameInput", t.WIZARD_NAME)
        self.email_input = _line("emailInput", t.WIZARD_EMAIL)
        self.phone_input = _line("phoneInput", t.WIZARD_PHONE)
        self.record_type_combo = _combo(
            "recordTypeCombo", t.WIZARD_RECORD_TYPES, t.WIZARD_RECORD_TYPE
        )
        self.name_label = _label("nameLabel", t.WIZARD_NAME)
        self.email_label = _label("emailLabel", t.WIZARD_EMAIL)
        self.phone_label = _label("phoneLabel", t.WIZARD_PHONE)
        self.record_type_label = _label("recordTypeLabel", t.WIZARD_RECORD_TYPE)

        self.department_combo = _combo(
            "departmentCombo", model.DEPARTMENTS, t.WIZARD_DEPARTMENT
        )
        self.role_combo = _combo("roleCombo", model.ROLES, t.WIZARD_ROLE)
        self.start_date_edit = QDateEdit(QDate(2026, 1, 1))
        self.start_date_edit.setObjectName("startDateEdit")
        self.start_date_edit.setAccessibleName(t.WIZARD_START_DATE)
        self.start_date_edit.setCalendarPopup(False)
        self.remote_check = _check("remoteCheck", t.WIZARD_REMOTE)
        self.department_label = _label("departmentLabel", t.WIZARD_DEPARTMENT)
        self.role_label = _label("roleLabel", t.WIZARD_ROLE)
        self.start_date_label = _label("startDateLabel", t.WIZARD_START_DATE)

        # No accessibleName: SC-20 checks this label's Name, which is its own text.
        self.summary_label = _label("summaryLabel", "")
        self.confirm_check = _check("confirmCheck", t.WIZARD_CONFIRM)
        self.send_email_check = _check("sendEmailCheck", t.WIZARD_SEND_EMAIL)
        self.note_input = _line("noteInput", t.WIZARD_NOTE)
        self.note_label = _label("noteLabel", t.WIZARD_NOTE)
        self.copy_button = _button("copyButton", t.WIZARD_COPY)

        self.back_button = _button("backButton", t.WIZARD_BACK)
        self.next_button = _button("nextButton", t.WIZARD_NEXT)
        self.finish_button = _button("finishButton", t.WIZARD_FINISH)
        self.cancel_button = _button("cancelButton", t.WIZARD_CANCEL)
        self.status_label = _label("statusLabel", "")

        form = QFormLayout()
        form.addRow(self.name_label, self.name_input)
        form.addRow(self.email_label, self.email_input)
        form.addRow(self.phone_label, self.phone_input)
        form.addRow(self.record_type_label, self.record_type_combo)
        form.addRow(self.department_label, self.department_combo)
        form.addRow(self.role_label, self.role_combo)
        form.addRow(self.start_date_label, self.start_date_edit)
        form.addRow(self.note_label, self.note_input)

        buttons = QHBoxLayout()
        buttons.addWidget(self.back_button)
        buttons.addWidget(self.next_button)
        buttons.addWidget(self.finish_button)
        buttons.addWidget(self.cancel_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.step_label)
        layout.addWidget(self.page_label)
        layout.addLayout(form)
        layout.addWidget(self.summary_label)
        layout.addWidget(self.confirm_check)
        layout.addWidget(self.send_email_check)
        layout.addWidget(self.remote_check)
        layout.addWidget(self.copy_button)
        layout.addLayout(buttons)
        layout.addWidget(self.status_label)

        # Each page's widgets, shown and hidden in place. Every page carries at least
        # eight interactive controls of its own once the four wizard buttons are counted,
        # which is #33's first criterion read per page rather than per window.
        self._on_page = {
            1: (
                self.name_label,
                self.name_input,
                self.email_label,
                self.email_input,
                self.phone_label,
                self.phone_input,
                self.record_type_label,
                self.record_type_combo,
            ),
            2: (
                self.department_label,
                self.department_combo,
                self.role_label,
                self.role_combo,
                self.start_date_label,
                self.start_date_edit,
                self.remote_check,
            ),
            3: (
                self.summary_label,
                self.confirm_check,
                self.send_email_check,
                self.note_label,
                self.note_input,
                self.copy_button,
            ),
        }

        self.back_button.clicked.connect(self.on_back)
        self.next_button.clicked.connect(self.on_next)
        self.finish_button.clicked.connect(self.on_finish)
        self.cancel_button.clicked.connect(self.close)
        self.copy_button.clicked.connect(self.on_copy)
        self.restart()

        variant_patch.apply_active(self)

    def restart(self) -> None:
        """Back to page one, for a second run of the wizard in the same session."""
        self._page = 1
        self.status_label.setText("")
        self._show_page()

    def _show_page(self) -> None:
        for page, widgets in self._on_page.items():
            for widget in widgets:
                widget.setVisible(page == self._page)
        self.step_label.setText(
            t.WIZARD_STEP.format(current=self._page, total=self.PAGES)
        )
        self.page_label.setText(
            {1: t.WIZARD_PAGE_ONE, 2: t.WIZARD_PAGE_TWO, 3: t.WIZARD_PAGE_THREE}[
                self._page
            ]
        )
        self.back_button.setEnabled(self._page > 1)
        self.next_button.setEnabled(self._page < self.PAGES)
        self.finish_button.setEnabled(self._page == self.PAGES)
        if self._page == self.PAGES:
            self.summary_label.setText(
                model.wizard_summary(
                    self.name_input.text(),
                    self.department_combo.currentText(),
                    self.role_combo.currentText(),
                )
            )

    def on_next(self) -> None:
        if self._page == 1 and not self.name_input.text().strip():
            self.status_label.setText(t.WIZARD_NAME_REQUIRED)
            return
        self.status_label.setText("")
        self._page = min(self._page + 1, self.PAGES)
        self._show_page()

    def on_back(self) -> None:
        self.status_label.setText("")
        self._page = max(self._page - 1, 1)
        self._show_page()

    def on_copy(self) -> None:
        """Put the summary on the clipboard, so the button does something observable."""
        from PySide6.QtGui import QGuiApplication

        clipboard = QGuiApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(self.summary_label.text())
        self.status_label.setText(t.WIZARD_COPIED)

    def on_finish(self) -> None:
        """Ask first (SC-20), then create the row and leave the window on its summary."""
        if not self.confirm_check.isChecked():
            self.status_label.setText(t.WIZARD_NOT_CONFIRMED)
            return
        dialog = QuestionDialog(
            "confirmDialog", t.CONFIRM_TITLE, t.CONFIRM_QUESTION, self
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        name = self.name_input.text().strip()
        first, _, last = name.partition(" ")
        self.status_label.setText(t.WIZARD_CREATED.format(name=name))
        if self._main_window is not None:
            self._main_window.add_customer(
                model.Customer(first, last, model.CITIES[1], True)
            )


class QuestionDialog(QDialog):
    """A yes/no question in its own window: the discard dialog and the wizard's confirm.

    One class for both, because the two differ only in their id, title and question --
    and because SC-22's result has to name the dialog's **title**, so each gets its own.
    """

    def __init__(
        self, name: str, title: str, question: str, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setObjectName(name)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(320)

        self.question_label = _label("questionLabel", question)
        self.question_label.setWordWrap(True)
        self.yes_button = _button("yesButton", t.DIALOG_YES)
        self.no_button = _button("noButton", t.DIALOG_NO)
        self.no_button.setDefault(True)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(self.yes_button)
        buttons.addWidget(self.no_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.question_label)
        layout.addLayout(buttons)

        self.yes_button.clicked.connect(self.accept)
        self.no_button.clicked.connect(self.reject)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        variant_patch.apply_active(self)
