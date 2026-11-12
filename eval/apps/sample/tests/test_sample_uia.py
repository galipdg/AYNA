"""The sample app through UI Automation: #33's criteria and the behaviour the scenarios need.

Two kinds of test:

* **The acceptance criteria**, once per screen, through the same functions `uia_check.py`
  uses -- so the criteria are checked by CI on every pull request instead of by hand.
* **The behaviour `docs/rs/scenarios.md` §C.2 promises**: the login messages (SC-14), a
  control that becomes ready late (SC-18), the modal dialog on leaving an edited form
  (SC-22) and the wizard with a Turkish item and a confirmation dialog (SC-20). These are
  the app-side preconditions of those scenarios; pinning them here means a broken app is
  never mistaken for a broken agent later.

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

import texts as t
import uia_check

#: Long enough for Qt to repaint and publish a new UIA value, short enough to fail fast.
SETTLE_TIMEOUT = 10.0

#: What SC-18 is about: the grid fills this long after the search click.
SEARCH_DELAY_MS = 3000


def _id(name: str) -> str:
    """The AutomationId of a control, which Qt builds from the whole object chain."""
    return f"QApplication.{name}"


@pytest.fixture
def screen(request):
    """Start one screen of the app, yield its window, and kill the process afterwards.

    Parametrised with the `--screen` value, so a test asks for the screen it needs instead
    of clicking its way there -- the navigation is tested by `test_screens.py`, and a test
    that starts four clicks deep fails for four reasons.
    """
    name = request.param if hasattr(request, "param") else "login"
    proc = uia_check.launch_app(name, delay_ms=SEARCH_DELAY_MS)
    try:
        yield uia_check.find_window(name)
    finally:
        uia_check.kill_process_tree(proc)


def until(predicate, timeout: float = SETTLE_TIMEOUT):
    """Wait for `predicate()` to be truthy and return it, or return the last value.

    A control that is not in the tree *yet* counts as not ready rather than as an error:
    Qt publishes a newly shown control to UI Automation a moment after the click that
    showed it, so `ElementNotFoundError` is exactly what "not ready" looks like here.
    """

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


def combo(window, name: str):
    return window.child_window(auto_id=_id(name), control_type="ComboBox")


# --- the acceptance criteria, screen by screen ---------------------------------------------


@pytest.mark.parametrize("screen", list(uia_check.WINDOW_CLASSES), indirect=True)
def test_every_control_of_the_screen_has_an_automation_id(screen):
    """#33's second criterion, read as the issue words it: through the UIA dump.

    The window frame's Minimize/Maximize/Close, a grid's cells and headers and the tab
    items are not the app's widgets and legitimately have none -- `is_app_widget` is what
    draws that line.
    """
    missing = uia_check.missing_automation_ids(uia_check.collect_controls(screen))
    assert not missing, [
        f"{row['control_type']} {row['name']!r} ({row['class_name']})"
        for row in missing
    ]


@pytest.mark.parametrize("screen", list(uia_check.WINDOW_CLASSES), indirect=True)
def test_the_screen_shows_at_least_eight_interactive_controls(screen):
    """#33's first criterion for the page that is showing.

    The settings screen's other tabs and the wizard's other pages are not in the tree at
    all, so they are counted on the widgets instead (`test_screens.py`).
    """
    controls = uia_check.interactive(uia_check.collect_controls(screen))
    assert len(controls) >= uia_check.MIN_INTERACTIVE, [
        row["automation_id"] for row in controls
    ]


@pytest.mark.parametrize("screen", list(uia_check.WINDOW_CLASSES), indirect=True)
def test_the_window_title_carries_the_app_and_its_version(screen):
    title = screen.element_info.name
    assert t.APP_NAME in title and t.VERSION in title, title


# --- login (SC-14, SC-21) ------------------------------------------------------------------


@pytest.mark.parametrize("screen", ["login"], indirect=True)
def test_the_right_credentials_are_welcomed_by_name(screen):
    edit(screen, "login.userNameInput").set_edit_text("admin")
    edit(screen, "login.passwordInput").set_edit_text("admin")
    button(screen, "login.loginButton").click()

    status = until(lambda: text_of(screen, "login.statusLabel"))
    assert "admin" in status, status


@pytest.mark.parametrize("screen", ["login"], indirect=True)
def test_a_wrong_password_says_so_in_the_status_label(screen):
    edit(screen, "login.userNameInput").set_edit_text("admin")
    edit(screen, "login.passwordInput").set_edit_text("yanlis")
    button(screen, "login.loginButton").click()

    status = until(lambda: text_of(screen, "login.statusLabel"))
    assert status == t.LOGIN_INVALID


@pytest.mark.parametrize("screen", ["login"], indirect=True)
def test_the_turkish_texts_reach_ui_automation_unchanged(screen):
    """SC-20's last line, checked where it is cheapest: the caption of a Turkish button.

    If anything on the way -- Qt, the UIA bridge, pywinauto -- mangled the encoding, every
    checkpoint on this app would be comparing against mojibake.
    """
    assert button(screen, "login.exitButton").window_text() == t.LOGIN_EXIT
    assert text_of(screen, "login.headingLabel") == t.LOGIN_HEADING


# --- the late control (SC-18) --------------------------------------------------------------


@pytest.mark.parametrize("screen", ["main"], indirect=True)
def test_the_open_button_becomes_enabled_only_after_the_grid_fills(screen):
    """SC-18's precondition: the state playback has to wait out rather than sleep through."""
    open_button = button(screen, "main.openButton")
    assert not open_button.is_enabled(), "nothing is searched yet"

    edit(screen, "main.searchInput").set_edit_text("Yılmaz")
    button(screen, "main.searchButton").click()

    # Right after the click the rows are gone and the button is still disabled: this is the
    # window of about three seconds the scenario is about.
    assert not open_button.is_enabled()
    started = time.monotonic()
    assert until(open_button.is_enabled), "the Open button never became enabled"
    waited_ms = (time.monotonic() - started) * 1000
    assert waited_ms >= SEARCH_DELAY_MS * 0.5, (
        f"the button was enabled after only {waited_ms:.0f} ms, so the delay this "
        "scenario needs is not there"
    )


@pytest.mark.parametrize("screen", ["main"], indirect=True)
def test_the_grid_lists_the_matches_with_their_turkish_text(screen):
    edit(screen, "main.searchInput").set_edit_text("Yılmaz")
    button(screen, "main.searchButton").click()
    assert until(button(screen, "main.openButton").is_enabled)

    grid = screen.child_window(auto_id=_id("main.customerGrid"), control_type="Table")
    cells = [item.window_text() for item in grid.descendants(control_type="DataItem")]
    assert "Ayşe" in cells and "Mustafa" in cells
    headers = [item.window_text() for item in grid.descendants(control_type="Header")]
    assert list(t.MAIN_COLUMNS) == [h for h in headers if h in t.MAIN_COLUMNS]


# --- the unexpected window (SC-22) ---------------------------------------------------------


@pytest.mark.parametrize("screen", ["detail"], indirect=True)
def test_leaving_an_edited_form_opens_a_modal_dialog_of_its_own(screen):
    """SC-22's precondition: a second window the run did not expect, with its own title.

    **Where the dialog sits in the tree is the finding here.** At the Win32 level it is a
    top-level window of its own (its own HWND, owned by the form, titled "Değişiklikleri
    at?"), but UI Automation reports it as a `Window` **child of its owner**, not as a child
    of the desktop: `Desktop(backend="uia").windows()` never lists it, while a walk of the
    form finds it. Good news for SC-22 -- the agent can name the dialog from the window it
    was already working on -- and a trap for any client that watches only the desktop for
    new windows. Measured 2026-11-12, PySide6 6.12.
    """
    edit(screen, "detail.nameInput").set_edit_text("Başka İsim")
    button(screen, "detail.backButton").click()

    dialog = screen.child_window(auto_id=_id("discardDialog"), control_type="Window")
    assert until(lambda: dialog.exists()), "no discard dialog appeared"
    assert dialog.element_info.name == t.DISCARD_TITLE
    assert dialog.child_window(
        auto_id=_id("discardDialog.yesButton"), control_type="Button"
    ).exists()
    assert dialog.child_window(
        auto_id=_id("discardDialog.noButton"), control_type="Button"
    ).exists()

    # "No" keeps the form, which is what makes the dialog an interruption rather than a
    # step on the way out.
    dialog.child_window(
        auto_id=_id("discardDialog.noButton"), control_type="Button"
    ).click()
    assert until(lambda: not dialog.exists())
    assert screen.exists() and screen.is_visible()


@pytest.mark.parametrize("screen", ["detail"], indirect=True)
def test_an_unedited_form_goes_back_without_asking(screen):
    """No dialog when nothing was changed -- the form just goes away.

    `exists`, not `is_visible`: a hidden window leaves the UI Automation tree altogether,
    and `is_visible` on an element that is no longer there raises instead of answering.
    """
    button(screen, "detail.backButton").click()
    assert until(lambda: not screen.exists(timeout=0.2))


@pytest.mark.parametrize("screen", ["detail"], indirect=True)
def test_saving_without_a_name_shows_the_required_message(screen):
    """SC-34's rule, which the bug-injected version removes."""
    edit(screen, "detail.nameInput").set_edit_text("")
    button(screen, "detail.saveButton").click()
    status = until(lambda: text_of(screen, "detail.statusLabel"))
    assert status == t.DETAIL_NAME_REQUIRED


# --- the wizard and its confirmation dialog (SC-20) ----------------------------------------


@pytest.mark.parametrize("screen", ["wizard"], indirect=True)
def test_the_department_combo_offers_its_turkish_items_through_ui_automation(screen):
    """What SC-20's `Select` step has to find: the items, by their exact text.

    Two measurements worth keeping (2026-11-12, PySide6 6.12):

    * A Qt combo box has **no item children until it is expanded** -- `ExpandCollapse`
      first, and then one `List` child with a `ListItem` per item.
    * Its current value is **not** its Name. The Name is the `accessibleName`, which this
      app sets on purpose so that the element's identity does not change with the
      selection; the value is the ValuePattern / LegacyIAccessible one.

    *Choosing* an item is playback's problem rather than this app's, and UI Automation
    alone does not solve it: `SelectionItem.Select`, `Invoke` on the item and
    `ValuePattern.SetValue` all leave a Qt combo box unchanged. The task note for #33 keeps
    the measurement; it is an open question for #40.
    """
    import model

    edit(screen, "wizard.nameInput").set_edit_text("Ayşe Çelik")
    button(screen, "wizard.nextButton").click()

    department = combo(screen, "wizard.departmentCombo")
    assert until(department.is_visible)
    assert department.element_info.name == t.WIZARD_DEPARTMENT
    assert department.legacy_properties().get("Value") == model.DEPARTMENTS[0]

    department.expand()
    items = until(
        lambda: [
            item.window_text()
            for item in department.descendants(control_type="ListItem")
        ]
    )
    department.collapse()
    assert items == list(model.DEPARTMENTS), items


@pytest.mark.parametrize("screen", ["wizard"], indirect=True)
def test_finishing_the_wizard_asks_in_a_second_window_and_then_creates_the_record(
    screen,
):
    """SC-20's tail: the summary names the department, and Finish opens the dialog.

    The department is the combo's own first item, so the summary can be shown to carry it
    without selecting anything -- which is the half of SC-20 that belongs to the app.
    """
    edit(screen, "wizard.nameInput").set_edit_text("Ayşe Çelik")
    # One click per page, each waited for: clicking Next twice in a row sends the second
    # click before Qt has shown page two, and the wizard then stays where it was.
    for page in (t.WIZARD_PAGE_TWO, t.WIZARD_PAGE_THREE):
        button(screen, "wizard.nextButton").click()
        showing = lambda expected=page: text_of(screen, "wizard.pageLabel") == expected
        assert until(showing), page

    summary = until(lambda: text_of(screen, "wizard.summaryLabel"))
    assert "Kalite Güvence" in summary, summary
    assert "Ayşe Çelik" in summary, summary

    screen.child_window(
        auto_id=_id("wizard.confirmCheck"), control_type="CheckBox"
    ).click()
    button(screen, "wizard.finishButton").click()

    # Nested under its owner, exactly like the discard dialog.
    dialog = screen.child_window(auto_id=_id("confirmDialog"), control_type="Window")
    assert until(lambda: dialog.exists()), "no confirmation dialog appeared"
    assert dialog.element_info.name == t.CONFIRM_TITLE
    dialog.child_window(
        auto_id=_id("confirmDialog.yesButton"), control_type="Button"
    ).click()

    status = until(lambda: text_of(screen, "wizard.statusLabel"))
    assert "Ayşe Çelik" in status, status
