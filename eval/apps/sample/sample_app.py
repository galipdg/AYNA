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

Three options are worth knowing: the search delay, which SC-18 is built on; the change version
(#46), which runs the same app with one kind of UI change applied; and the bug version (#47),
which runs it with one functional bug a correct test must catch:

    .venv/Scripts/python.exe eval/apps/sample/sample_app.py --search-delay-ms 0
    .venv/Scripts/python.exe eval/apps/sample/sample_app.py --variant v2a --screen main
    .venv/Scripts/python.exe eval/apps/sample/sample_app.py --bug bug2 --screen detail

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

import bug_patch
import texts
import variant_patch
from bugs import BUG_CHOICES, NO_BUG
from variants import BASELINE, VARIANT_CHOICES
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
        "--variant",
        choices=VARIANT_CHOICES,
        default=BASELINE,
        help=(
            "which of #46's controlled change versions to run (default: v1, the unchanged "
            "app); the version is in every window title and the changes are in "
            "eval/apps/sample/variants.md"
        ),
    )
    parser.add_argument(
        "--bug",
        choices=BUG_CHOICES,
        default=NO_BUG,
        help=(
            "run one of #47's bug-injected versions instead of the correct app (default: "
            "none); each has one functional bug and names the reference scenario that must "
            "fail -- eval/apps/sample/bugs.md"
        ),
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
    # Before the first window: every window's `__init__` applies the active version itself,
    # so the screens this one opens later are changed too.
    variant_patch.set_active(args.variant)
    # A bug version patches module globals and class methods, so it goes in before the first
    # window exists: a slot Qt has already connected would otherwise keep the correct method.
    bug_patch.install(args.bug)
    window = open_screen(args.screen, args.search_delay_ms)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
