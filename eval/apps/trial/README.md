# eval/apps/trial — one-screen login trial app

A deliberately small PySide6 window (username, password, remember-me, login
button, status label) used as the first target for AYNA's recognition and
playback work. Issue: [#9](https://github.com/galipdg/AYNA/issues/9).

Beyond being a click target, this app is the spike that established **how Qt
actually exposes itself to UI Automation** — measured on PySide6 6.12.0,
Python 3.13, Windows 11. Those findings drive D1 (#21) and the sample app
(#33); the short version is in `memory-bank/learnings.md`.

## What Qt exposes

| Qt side | UIA property | Note |
|---|---|---|
| `objectName` | **AutomationId** | Dotted path over the whole object chain, not the bare name |
| `accessibleName` | **Name** | *Replaces* the Name the control would otherwise have |
| Python class name | **ClassName** | `LoginWindow` — a stable handle for finding the window |

So the controls look like this:

| Control | AutomationId | UIA Name | ClassName |
|---|---|---|---|
| Window | `QApplication.loginWindow` | `AYNA Trial - Login` (title) | `LoginWindow` |
| Username field | `QApplication.loginWindow.usernameInput` | `Username` (accessibleName) | `QLineEdit` |
| Password field | `QApplication.loginWindow.passwordInput` | `Password` (accessibleName) | `QLineEdit` |
| Remember-me box | `QApplication.loginWindow.rememberMeCheckBox` | `Remember me` (own text) | `QCheckBox` |
| Login button | `QApplication.loginWindow.loginButton` | `Login` (own text) | `QPushButton` |
| Status label | `QApplication.loginWindow.statusLabel` | its current text | `QLabel` |

**The accessibleName rule this app follows:** set it only on controls with no
useful visible text — here just the two input fields. Setting it on the window
hides the window title, and setting it on a label hides the label's text, from
every UIA client including our own checkpoints. The window frame's
Minimize/Maximize/Close buttons have no AutomationId at all; that is Windows,
not the app, so checks must look only at the app's own `Q*` widgets.

Credentials: `admin` / `admin` shows `Welcome, admin!`; anything else shows
`Invalid username or password`; an empty field shows
`Username and password are required`.

## Setup (once)

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r eval/apps/trial/requirements.txt
```

## Run the app

```powershell
.venv/Scripts/python.exe eval/apps/trial/app.py
```

## Dump the UIA tree (Windows only)

Prints every control with its AutomationId and exits non-zero if one of the
app's own inputs, buttons or checkboxes has none:

```powershell
.venv/Scripts/python.exe eval/apps/trial/uia_dump.py
.venv/Scripts/python.exe eval/apps/trial/uia_dump.py --tree    # full pywinauto tree
.venv/Scripts/python.exe eval/apps/trial/uia_dump.py --json    # machine-readable
.venv/Scripts/python.exe eval/apps/trial/uia_dump.py --attach  # use a running app
```

## Tests

```powershell
.venv/Scripts/python.exe -m pytest eval/apps/trial/tests -v
```

`tests/test_authenticate.py` runs anywhere. `tests/test_uia.py` is marked
`@pytest.mark.windows`: it launches the real window and checks the
AutomationIds and the login flow, and is skipped automatically off Windows, so
the suite stays green on macOS.
