"""Installs one of #47's bug versions into the running app, and can take it back out.

`bugs.py` declares the five bugs and the scenario each one must fail; this module is the only
place that changes the app's behaviour. Each patch is a few lines, and it is deliberately
written as "what a developer would have got wrong" rather than as a hole punched through the
app: a message constant edited for one state, two arguments of the same shape swapped, one
validation rule dropped, a button left disabled, a window opened instead of another.

**Installed before the first window, not per window.** Qt binds a slot when `connect` is
called, so swapping a method on an instance afterwards would leave every connected signal
calling the old one -- `windows.py`'s constructors connect theirs in `__init__`. So a bug
version patches **module globals and class methods** once, before anything is built
(`sample_app.py --bug bug2`), which is also what a real buggy build looks like: the defect is
in the code, not in one instance.

`reset()` puts everything back, because the patches are process-wide and
`tests/test_bugs.py` has to compare the correct app with the broken one in one run.

Two notes on where the patches land, both learned from the app's own code:

* **`model.py` does `from texts import …`**, so a text bug patches `model.LOGIN_WELCOME` and
  not `texts.LOGIN_WELCOME`: the from-import copied the value into `model`'s namespace at
  import time, and patching `texts` would change nothing. (`texts.py`'s docstring predicted
  the wrong-label bug would be "a one-line change" there -- it is one line, in `model`.)
* **The window title does carry the version**, like #46's change versions, by patching
  `texts.title`: `windows.py` calls `t.title(...)` at construction, so every window of a bug
  build reads `AYNA Örnek 1.0-bug2 - …` and a screenshot says which build it came from.
"""

from __future__ import annotations

from typing import Any

import model
import texts
import windows
from bugs import BUGS, NO_BUG

#: What was replaced, so `reset()` can put it back: (object, attribute, original value).
_originals: list[tuple[Any, str, Any]] = []

#: The bug version currently installed; `none` is the correct app.
_active: str = NO_BUG


def active() -> str:
    """The installed bug version, `none` when the app is the correct one."""
    return _active


def install(bug: str | None) -> None:
    """Install a bug version. `None` or `none` leaves the app correct.

    Call it **before the first window is built**; see the module docstring for why.
    """
    global _active
    if bug in (None, NO_BUG):
        return
    if bug not in BUGS:
        raise ValueError(f"unknown bug {bug!r}")
    if _active != NO_BUG:
        raise RuntimeError(
            f"{_active} is already installed; a version has exactly one bug, and two "
            f"would make a failing step impossible to attribute"
        )
    _PATCHES[bug]()
    _patch(texts, "title", _title_with(bug))
    _active = bug


def reset() -> None:
    """Undo whatever `install` did, in reverse order. The app is correct again."""
    global _active
    while _originals:
        target, name, original = _originals.pop()
        setattr(target, name, original)
    _active = NO_BUG


def _patch(target: Any, name: str, value: Any) -> None:
    _originals.append((target, name, getattr(target, name)))
    setattr(target, name, value)


def _title_with(bug: str):
    """`texts.title`, with the bug version in it: `AYNA Örnek 1.0-bug2 - Giriş`."""
    original = texts.title

    def title(screen: str) -> str:
        return texts.with_variant(original(screen), bug)

    return title


# --- bug1: the wrong label (SC-21) ---------------------------------------------------------


def _wrong_login_status_label() -> None:
    """A successful login reports the wrong thing, on the label SC-21 verifies.

    The user name is still in the message, so the only difference is the words -- which is
    what makes it a label bug rather than a formatting crash.
    """
    _patch(model, "LOGIN_WELCOME", "Oturum kapatıldı, {user}")


# --- bug2: the disabled button (SC-19) -----------------------------------------------------


def _save_button_stays_disabled() -> None:
    """The detail form's Save button is built disabled and nothing enables it again.

    `__init__` is wrapped rather than the button being hidden: SC-19 is about a wait that
    cannot succeed ("timeout", condition `enabled`), and a hidden control would be
    element-not-found, which is a different category and a different scenario.
    """
    original = windows.DetailWindow.__init__

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        original(self, *args, **kwargs)
        self.save_button.setEnabled(False)

    _patch(windows.DetailWindow, "__init__", __init__)


# --- bug3: the wrong saved value (SC-20) ---------------------------------------------------


def _summary_carries_the_role_twice() -> None:
    """The wizard's summary gets the role where the department belongs.

    Two arguments of the same shape swapped at the call site, so the department the author
    selected on page two never reaches page three and SC-20's Verify step fails.
    """

    def wizard_summary(name: str, department: str, role: str) -> str:
        return model.WIZARD_SUMMARY.format(
            name=name.strip(), department=role, role=role
        )

    _patch(model, "wizard_summary", wizard_summary)


# --- bug4: the missing validation (SC-34) --------------------------------------------------


def _required_name_rule_is_gone() -> None:
    """The detail form accepts an empty name. The e-mail rule still works.

    Exactly one rule is dropped, as `model.validate_detail`'s docstring promises: a version
    that validated nothing would fail every detail-form test, and SC-34's CI job would no
    longer be evidence about the required field.
    """

    def validate_detail(name: str, email: str) -> list[str]:
        problems = []
        if email.strip() and "@" not in email:
            problems.append(model.DETAIL_EMAIL_INVALID)
        return problems

    _patch(model, "validate_detail", validate_detail)


# --- bug5: the wrong navigation (SC-31) ----------------------------------------------------


def _login_opens_the_settings_screen() -> None:
    """Logging in succeeds and opens Ayarlar instead of the customer list.

    The welcome message is still the correct one, so the failure of the *next* step cannot be
    blamed on the login: SC-31 needs a run where the element really is gone, the healer
    offers candidates from the wrong screen, and the tester rejects them.
    """

    def on_login(self) -> None:
        result = model.authenticate(
            self.user_name_input.text(), self.password_input.text()
        )
        self.status_label.setText(result.message)
        if not result.ok:
            return
        if self.main_window is None:
            # The attribute is typed `MainWindow | None` and now holds a settings window:
            # that *is* the bug, and it also keeps the window alive, which a local would not.
            self.main_window = windows.SettingsWindow()
        self.main_window.show()
        self.main_window.raise_()

    _patch(windows.LoginWindow, "on_login", on_login)


#: Bug id -> the function that installs it.
_PATCHES = {
    "bug1": _wrong_login_status_label,
    "bug2": _save_button_stays_disabled,
    "bug3": _summary_carries_the_role_twice,
    "bug4": _required_name_rule_is_gone,
    "bug5": _login_opens_the_settings_screen,
}
