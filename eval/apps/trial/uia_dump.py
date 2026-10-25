"""Dump the UI Automation tree of the trial app and check its AutomationIds.

Acceptance criterion 2 of issue #9 is "UIA dump shows an AutomationId for every
input and button", so this script is both the dump and the check: it exits 1
when one of the app's own inputs, buttons or checkboxes has no AutomationId.

Two Windows details this had to work around (details in
`memory-bank/learnings.md`):

* A venv's ``python.exe`` is a launcher that runs the real interpreter as a
  **child** process, and the window belongs to that child. So the app is
  started with ``subprocess`` and found by its UIA ClassName rather than by
  pywinauto's ``Application.start()``, which would watch the launcher's PID and
  never see the window. Cleanup has to kill the whole process tree.
* The window frame contributes Minimize/Maximize/Close buttons and a menu bar
  that legitimately have no AutomationId, so the check only looks at the app's
  own Qt widgets (UIA ClassName starting with ``Q``).

Run it with (Windows only):
    .venv/Scripts/python.exe eval/apps/trial/uia_dump.py
    .venv/Scripts/python.exe eval/apps/trial/uia_dump.py --tree
    .venv/Scripts/python.exe eval/apps/trial/uia_dump.py --json
    .venv/Scripts/python.exe eval/apps/trial/uia_dump.py --attach
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

APP_PATH = Path(__file__).resolve().parent / "app.py"

# Qt exposes the Python class name as the UIA ClassName; it is stable and
# unique enough to find the window with.
WINDOW_CLASS = "LoginWindow"

# Control types that must carry an AutomationId for the criterion to hold.
REQUIRED_TYPES = ("Edit", "Button", "CheckBox")

READY_TIMEOUT = 30.0


def launch_app() -> subprocess.Popen[bytes]:
    """Start app.py as a separate process."""
    return subprocess.Popen([sys.executable, str(APP_PATH)])


def kill_process_tree(proc: subprocess.Popen[bytes]) -> None:
    """Kill the launcher and the interpreter child that owns the window."""
    subprocess.run(
        ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
        capture_output=True,
        check=False,
    )


def find_window(timeout: float = READY_TIMEOUT):
    """Return the trial app's top-level window, waiting for it to be ready."""
    from pywinauto import Desktop

    window = Desktop(backend="uia").window(class_name=WINDOW_CLASS)
    window.wait("visible ready", timeout=timeout)
    return window


def collect_controls(window) -> list[dict[str, str]]:
    """Flatten the window and its descendants into AutomationId rows."""
    rows: list[dict[str, str]] = []
    for control in [window] + window.descendants():
        info = control.element_info
        rows.append(
            {
                "control_type": info.control_type or "",
                "automation_id": info.automation_id or "",
                "name": info.name or "",
                "class_name": info.class_name or "",
            }
        )
    return rows


def is_app_widget(row: dict[str, str]) -> bool:
    """True for the app's own Qt widgets, false for the window frame."""
    return row["class_name"].startswith("Q")


def required_widgets(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """The app's own inputs, buttons and checkboxes."""
    return [
        row
        for row in rows
        if is_app_widget(row) and row["control_type"] in REQUIRED_TYPES
    ]


def missing_automation_ids(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Required widgets that have no AutomationId."""
    return [row for row in required_widgets(rows) if not row["automation_id"]]


def print_table(rows: list[dict[str, str]]) -> None:
    header = f"{'ControlType':<13} {'AutomationId':<46} {'Name':<26} ClassName"
    print(header)
    print("-" * len(header))
    for row in rows:
        print(
            f"{row['control_type']:<13} "
            f"{row['automation_id'] or '(none)':<46} "
            f"{row['name'] or '(none)':<26} "
            f"{row['class_name'] or '(none)'}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Dump the trial app's UIA tree.")
    parser.add_argument(
        "--attach",
        action="store_true",
        help="use an already running trial app instead of starting one",
    )
    parser.add_argument(
        "--tree",
        action="store_true",
        help="also print pywinauto's full control identifiers tree",
    )
    parser.add_argument("--json", action="store_true", help="print rows as JSON")
    args = parser.parse_args(argv)

    if sys.platform != "win32":
        print("uia_dump.py needs a real Windows UI session.", file=sys.stderr)
        return 2

    proc = None if args.attach else launch_app()
    try:
        window = find_window()
        rows = collect_controls(window)

        if args.json:
            print(json.dumps(rows, indent=2, ensure_ascii=False))
        else:
            print_table(rows)
        if args.tree:
            print()
            window.print_control_identifiers()

        missing = missing_automation_ids(rows)
        if missing:
            print(file=sys.stderr)
            for row in missing:
                print(
                    f"MISSING AutomationId: {row['control_type']} "
                    f"name={row['name']!r} class={row['class_name']!r}",
                    file=sys.stderr,
                )
            return 1

        checked = required_widgets(rows)
        print(
            f"\nOK: {len(checked)} inputs/buttons/checkboxes, "
            "each with an AutomationId."
        )
        return 0
    finally:
        if proc is not None:
            kill_process_tree(proc)


if __name__ == "__main__":
    sys.exit(main())
