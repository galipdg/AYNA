"""Dump the sample app's UI Automation tree and check #33's criteria (Windows only).

This is both the dump and the acceptance check for issue #33, which asks for

1. at least **8 interactive controls** on each screen,
2. an **AutomationId on every control**,

so one command answers both, for every screen, and exits non-zero when a screen fails:

    .venv/Scripts/python.exe eval/apps/sample/uia_check.py             # all screens, summary
    .venv/Scripts/python.exe eval/apps/sample/uia_check.py --screen settings --table
    .venv/Scripts/python.exe eval/apps/sample/uia_check.py --json      # machine-readable
    .venv/Scripts/python.exe eval/apps/sample/uia_check.py --attach --screen main

`--json` is what `eval/nl/objects/sample.json` (#36) and the README's id table are built
from, so the ids in the documentation are always measured rather than assumed.

The name is `uia_check.py`, not `uia_dump.py` like the trial app's: the tests import it by
bare module name, and one module name may exist only once in the whole `eval/` tree -- two
files called `uia_dump.py` shadow each other for an entire `pytest eval` run (#199,
`memory-bank/learnings.md` 2026-11-08). The same rule is why the UIA tests here are
`tests/test_sample_uia.py`. `app.py` keeps its name because it is only ever *run*, never
imported.

Two Windows details, both learned on the trial app (`memory-bank/learnings.md`):

* A venv's `python.exe` is a launcher that runs the real interpreter as a **child**
  process, and the window belongs to that child. So the app is started with `subprocess`
  and found by its UIA ClassName, not with pywinauto's `Application.start()`, which would
  watch the launcher's PID and never see the window. Cleanup kills the whole tree.
* The window frame contributes Minimize/Maximize/Close buttons that legitimately have no
  AutomationId, and a grid's cells, headers and tab items are not widgets at all. Both are
  excluded by looking only at controls whose UIA ClassName starts with `Q`.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

APP_PATH = Path(__file__).resolve().parent / "app.py"

#: Qt exposes the Python class name as the UIA ClassName, which is how each screen's window
#: is found. The keys are `app.py --screen` values.
WINDOW_CLASSES: dict[str, str] = {
    "login": "LoginWindow",
    "main": "MainWindow",
    "detail": "DetailWindow",
    "settings": "SettingsWindow",
    "wizard": "WizardWindow",
}

#: Control types that count towards "at least 8 interactive controls". A `Table` counts once
#: as the grid itself; its cells are data, not controls.
INTERACTIVE_TYPES = (
    "Button",
    "CheckBox",
    "ComboBox",
    "Document",
    "Edit",
    "List",
    "RadioButton",
    "Spinner",
    "Tab",
    "TabItem",
    "Table",
)

#: Control types that must carry an AutomationId. Text is in here because the scenarios
#: check labels (`login.statusLabel`, `wizard.summaryLabel`) and a label without an id could
#: only be found by its own text, which is what those checks are about to change.
REQUIRED_TYPES = INTERACTIVE_TYPES + ("Text",)

#: #33's first criterion.
MIN_INTERACTIVE = 8

READY_TIMEOUT = 30.0


def launch_app(screen: str = "login", delay_ms: int = 0) -> subprocess.Popen[bytes]:
    """Start `app.py` on one screen as a separate process.

    The search delay defaults to 0 here: the dump reads a window, it does not wait for a
    grid, and three seconds per screen of dumping is three seconds wasted.
    """
    # A child inherits QT_QPA_PLATFORM, and a value such as `offscreen` would start the app
    # with no real window, so UI Automation would never find it and every lookup here would
    # time out (measured 2026-11-12, when `tests/test_screens.py` still set that variable to
    # run without a display). The app under test always gets the native platform plugin.
    env = dict(os.environ)
    env.pop("QT_QPA_PLATFORM", None)
    return subprocess.Popen(
        [
            sys.executable,
            str(APP_PATH),
            "--screen",
            screen,
            "--search-delay-ms",
            str(delay_ms),
        ],
        env=env,
    )


def kill_process_tree(proc: subprocess.Popen[bytes]) -> None:
    """Kill the launcher and the interpreter child that owns the window."""
    subprocess.run(
        ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
        capture_output=True,
        check=False,
    )


def find_window(screen: str, timeout: float = READY_TIMEOUT):
    """The screen's top-level window, waited for until it is ready."""
    from pywinauto import Desktop

    window = Desktop(backend="uia").window(class_name=WINDOW_CLASSES[screen])
    window.wait("visible ready", timeout=timeout)
    return window


def collect_controls(window) -> list[dict[str, str]]:
    """Flatten the window and its descendants into rows."""
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
    """True for the app's own Qt widgets, false for the window frame and for grid cells."""
    return row["class_name"].startswith("Q")


def interactive(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        row
        for row in rows
        if is_app_widget(row) and row["control_type"] in INTERACTIVE_TYPES
    ]


def required_widgets(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        row
        for row in rows
        if is_app_widget(row) and row["control_type"] in REQUIRED_TYPES
    ]


def missing_automation_ids(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [row for row in required_widgets(rows) if not row["automation_id"]]


def print_table(rows: list[dict[str, str]]) -> None:
    header = f"{'ControlType':<13} {'AutomationId':<52} {'Name':<30} ClassName"
    print(header)
    print("-" * len(header))
    for row in rows:
        print(
            f"{row['control_type']:<13} "
            f"{row['automation_id'] or '(none)':<52} "
            f"{row['name'] or '(none)':<30} "
            f"{row['class_name'] or '(none)'}"
        )


def dump_screen(screen: str, attach: bool = False) -> list[dict[str, str]]:
    """Start the screen (unless attaching), read its tree, close it again."""
    proc = None if attach else launch_app(screen)
    try:
        return collect_controls(find_window(screen))
    finally:
        if proc is not None:
            kill_process_tree(proc)


def report(screen: str, rows: list[dict[str, str]], show_table: bool) -> bool:
    """Print one screen's result and say whether it meets both criteria."""
    missing = missing_automation_ids(rows)
    controls = interactive(rows)
    if show_table:
        print(f"\n=== {screen} ({WINDOW_CLASSES[screen]}) ===")
        print_table(rows)
        print()
    ok = not missing and len(controls) >= MIN_INTERACTIVE
    print(
        f"{'OK ' if ok else 'FAIL'} {screen:<9} "
        f"{len(controls):>3} interactive, {len(rows):>3} elements, "
        f"{len(missing)} without an AutomationId"
    )
    for row in missing:
        print(
            f"     MISSING AutomationId: {row['control_type']} "
            f"name={row['name']!r} class={row['class_name']!r}",
            file=sys.stderr,
        )
    if len(controls) < MIN_INTERACTIVE:
        print(
            f"     TOO FEW interactive controls: {len(controls)} < {MIN_INTERACTIVE}",
            file=sys.stderr,
        )
    return ok


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Dump the sample app's UIA tree.")
    parser.add_argument(
        "--screen",
        choices=(*WINDOW_CLASSES, "all"),
        default="all",
        help="which screen to dump (default: all five)",
    )
    parser.add_argument(
        "--attach",
        action="store_true",
        help="use an already running app instead of starting one (one screen only)",
    )
    parser.add_argument("--table", action="store_true", help="print every control")
    parser.add_argument("--json", action="store_true", help="print rows as JSON")
    args = parser.parse_args(argv)

    # Every Name on these screens is Turkish, and a redirected stdout on a Turkish Windows
    # console is cp1254: without this, `--json > file` dies on the first "ö".
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if sys.platform != "win32":
        print("uia_check.py needs a real Windows UI session.", file=sys.stderr)
        return 2
    if args.attach and args.screen == "all":
        parser.error("--attach dumps one running screen; name it with --screen")

    screens = list(WINDOW_CLASSES) if args.screen == "all" else [args.screen]
    dumps = {screen: dump_screen(screen, args.attach) for screen in screens}

    if args.json:
        print(json.dumps(dumps, indent=2, ensure_ascii=False))
        return 0

    results = [
        report(screen, rows, args.table or args.screen != "all")
        for screen, rows in dumps.items()
    ]
    total = sum(len(interactive(rows)) for rows in dumps.values())
    print(f"\n{len(screens)} screen(s), {total} interactive controls in total.")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
