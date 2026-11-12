"""AYNA sample app v1.0 -- the main application under test (#33).

Six screens in six windows: login, the customer list with a grid, the detail form, the
tabbed settings, the three-page wizard and the yes/no dialogs. It exists to be *tested*,
not to be used: every control carries an AutomationId, the version is in every window
title, and the behaviour the reference scenarios depend on (`docs/rs/scenarios.md` §C.2)
is implemented deliberately -- a control that becomes ready late (SC-18), a required field
(SC-34), a modal dialog on leaving an edited form (SC-22), a combo box with Turkish items
(SC-20).

Run it from the repository root, on any platform:

    .venv/Scripts/python.exe eval/apps/sample/sample_app.py          # Windows
    .venv/bin/python eval/apps/sample/sample_app.py                  # macOS, Linux

The one option worth knowing is the search delay, which SC-18 is built on:

    .venv/Scripts/python.exe eval/apps/sample/sample_app.py --search-delay-ms 0

The rules live in `model.py` (no Qt, so they are tested anywhere), every visible string in
`texts.py`, and the screens in `windows.py`.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Run as a script (`python eval/apps/sample/sample_app.py`), so the app's own modules are imported
# by name; this makes that work from any working directory, and the tests do the same thing
# in their conftest.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PySide6.QtWidgets import QApplication

import texts
from windows import DEFAULT_SEARCH_DELAY_MS, LoginWindow

SCREENS = ("login", "main", "detail", "settings", "wizard")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="ayna-sample",
        description=f"{texts.APP_NAME} {texts.VERSION} -- AYNA sample app under test",
    )
    parser.add_argument(
        "--search-delay-ms",
        type=int,
        default=DEFAULT_SEARCH_DELAY_MS,
        metavar="MS",
        help=(
            "how long after a search the grid fills and the Open button becomes enabled "
            f"(default: {DEFAULT_SEARCH_DELAY_MS}); 0 fills it at once"
        ),
    )
    parser.add_argument(
        "--screen",
        choices=SCREENS,
        default="login",
        help="which screen to open first (default: login)",
    )
    parser.add_argument(
        "--version", action="version", version=f"{texts.APP_NAME} {texts.VERSION}"
    )
    return parser.parse_args(argv)


def open_screen(name: str, delay_ms: int):
    """The first window to show. Every screen can be opened on its own, which is what the
    UIA tests and a tester measuring one window want -- going through the login first would
    make a snapshot of the settings screen a four-click affair."""
    from windows import (
        DetailWindow,
        MainWindow,
        SettingsWindow,
        WizardWindow,
    )

    if name == "login":
        return LoginWindow(delay_ms=delay_ms)
    if name == "main":
        return MainWindow(delay_ms=delay_ms)
    if name == "detail":
        return DetailWindow()
    if name == "settings":
        return SettingsWindow()
    return WizardWindow()


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    app = QApplication([sys.argv[0]])
    window = open_screen(args.screen, args.search_delay_ms)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
