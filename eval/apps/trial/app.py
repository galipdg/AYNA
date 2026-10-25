"""One-screen login trial app for AYNA (issue #9).

The point of this app is not the login itself but the UI Automation data it
exposes. What Qt's Windows UIA backend actually does, measured on PySide6
6.12.0 / Windows 11 (see `memory-bank/learnings.md`):

* ``objectName`` becomes the **AutomationId**, but as a dotted path built from
  the whole object chain, e.g. ``QApplication.loginWindow.usernameInput``.
* ``accessibleName`` becomes the **UIA Name** and *replaces* whatever Name the
  control would otherwise have — the window title for a top-level window, the
  visible text for a label. So it is set only on controls that have no useful
  visible text of their own (here: the two input fields). Setting it on the
  window or on the labels would hide the title and the status text from every
  UIA client, including our own checkpoints.
* The Python class name becomes the UIA **ClassName** (``LoginWindow``), which
  makes it a stable handle for finding the window.

Run it with:
    .venv/Scripts/python.exe eval/apps/trial/app.py
"""

from __future__ import annotations

import sys
from dataclasses import dataclass

from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

WINDOW_TITLE = "AYNA Trial - Login"

VALID_USERNAME = "admin"
VALID_PASSWORD = "admin"

WELCOME_MESSAGE = "Welcome, admin!"
INVALID_MESSAGE = "Invalid username or password"
EMPTY_MESSAGE = "Username and password are required"


@dataclass(frozen=True)
class LoginResult:
    """Outcome of a credential check and the message the status label shows."""

    ok: bool
    message: str


def authenticate(username: str, password: str) -> LoginResult:
    """Check credentials.

    Kept as a pure function so the rules can be tested without a display or
    Windows; the widget layer only renders the result.
    """
    if not username or not password:
        return LoginResult(ok=False, message=EMPTY_MESSAGE)
    if username == VALID_USERNAME and password == VALID_PASSWORD:
        return LoginResult(ok=True, message=WELCOME_MESSAGE)
    return LoginResult(ok=False, message=INVALID_MESSAGE)


class LoginWindow(QWidget):
    """Username, password, remember-me, a login button and a status label."""

    def __init__(self) -> None:
        super().__init__()
        # No accessibleName here: it would replace the window title in UIA.
        self.setObjectName("loginWindow")
        self.setWindowTitle(WINDOW_TITLE)
        self.setMinimumWidth(360)

        # Input fields have no visible text, so an accessibleName is the only
        # way for them to get a meaningful UIA Name.
        self.username_input = QLineEdit()
        self.username_input.setObjectName("usernameInput")
        self.username_input.setAccessibleName("Username")

        self.password_input = QLineEdit()
        self.password_input.setObjectName("passwordInput")
        self.password_input.setAccessibleName("Password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)

        # The controls below already carry their own text, which Qt exposes as
        # the UIA Name; adding an accessibleName would only mask it.
        self.remember_me_checkbox = QCheckBox("Remember me")
        self.remember_me_checkbox.setObjectName("rememberMeCheckBox")

        self.login_button = QPushButton("Login")
        self.login_button.setObjectName("loginButton")

        self.status_label = QLabel("")
        self.status_label.setObjectName("statusLabel")

        username_label = QLabel("Username")
        username_label.setObjectName("usernameLabel")

        password_label = QLabel("Password")
        password_label.setObjectName("passwordLabel")

        form = QFormLayout()
        form.setObjectName("loginForm")
        form.addRow(username_label, self.username_input)
        form.addRow(password_label, self.password_input)

        layout = QVBoxLayout(self)
        layout.setObjectName("loginLayout")
        layout.addLayout(form)
        layout.addWidget(self.remember_me_checkbox)
        layout.addWidget(self.login_button)
        layout.addWidget(self.status_label)

        self.login_button.clicked.connect(self.on_login_clicked)
        self.username_input.returnPressed.connect(self.on_login_clicked)
        self.password_input.returnPressed.connect(self.on_login_clicked)

    def on_login_clicked(self) -> None:
        """Run the credential check and show its message in the status label."""
        result = authenticate(self.username_input.text(), self.password_input.text())
        self.status_label.setText(result.message)


def main() -> int:
    app = QApplication(sys.argv)
    window = LoginWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
