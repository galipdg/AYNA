r"""What UI Automation reports for a grid or a list, and where a cell's text lives.

Written for the step schema v0.2 review (#147, PR #150): the ADR's cell-text rule reads a
cell as "its ValuePattern value when that value is non-empty, else its UI Automation Name",
and the row rules map onto GridPattern and TablePattern. Both claims are about what the
provider actually exposes, so they are measured here rather than argued from the docs.

Two targets, because the two frameworks behave differently:

    python grid_probe.py qt              # launches its own PySide6 grid window and probes it
    python grid_probe.py handle 393752   # probes a grid or list in a window already open
    python grid_probe.py handle 393752 --automation-id m_lvEntries

`qt` needs PySide6 (`pip install -e "eval[dev]"` from the repo root installs it). The
`handle` mode needs nothing but the window: for KeePass 2, `kp_state.py main` prints the
handle of a window with its database open.

What it prints, per target: the patterns the container supports, GridPattern's row and
column counts, TablePattern's column headers, every ControlView child with its Name and its
ValuePattern value, the children of each row, and what the v0.2 rule would read for each.
`GetItem(row, col)` is probed only when the container has a Grid pattern.

Findings are written up in `grid-probes.md` next to this file. Windows only: UI Automation
is a Windows API.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

PROBE_APP = Path(__file__).resolve().parent / "grid_probe_app.py"
#: The Qt window waits for its own title; a cold PySide6 import is the slow part.
QT_START_TIMEOUT = 30.0
QT_TITLE = "AYNA Grid Probe"

#: Every pattern worth knowing about for a grid, a list or one of their cells.
PATTERNS = (
    "Grid",
    "GridItem",
    "Table",
    "TableItem",
    "Selection",
    "SelectionItem",
    "Value",
    "LegacyIAccessible",
    "Invoke",
    "ItemContainer",
    "VirtualizedItem",
    "ScrollItem",
)


def uia():
    """pywinauto's UI Automation singleton, imported late so `--help` works anywhere."""
    from pywinauto.uia_defines import IUIA

    return IUIA()


def pattern(element: Any, name: str) -> Any | None:
    """The pattern interface, or None when the element does not support it."""
    from pywinauto.uia_defines import get_elem_interface

    try:
        return get_elem_interface(element, name)
    except Exception:
        # pywinauto raises NoPatternInterfaceError; a provider that died mid-read raises a
        # COMError. Neither means anything but "not available", and a probe must not stop.
        return None


def supported(element: Any) -> list[str]:
    return [name for name in PATTERNS if pattern(element, name) is not None]


def props(element: Any, types: dict[int, str]) -> dict[str, Any]:
    def read(get):
        try:
            return get()
        except Exception as exc:
            return f"<{type(exc).__name__}>"

    return {
        "name": read(lambda: element.CurrentName),
        "automationId": read(lambda: element.CurrentAutomationId),
        "className": read(lambda: element.CurrentClassName),
        "controlType": read(
            lambda: types.get(element.CurrentControlType, element.CurrentControlType)
        ),
    }


def cell_text(element: Any, types: dict[int, str]) -> tuple[Any, Any, Any]:
    """(ValuePattern value, Name, what the v0.2 rule reads) for one cell or row."""
    value_pattern = pattern(element, "Value")
    value = None
    if value_pattern is not None:
        try:
            value = value_pattern.CurrentValue
        except Exception as exc:
            value = f"<{type(exc).__name__}>"
    name = props(element, types)["name"]
    # ADR 2026-10-28-step-schema-v0-2-rows: non-empty ValuePattern value, else Name.
    chosen = value if isinstance(value, str) and value != "" else name
    return value, name, chosen


def children(element: Any, walker: Any) -> list[Any]:
    found = []
    child = walker.GetFirstChildElement(element)
    while child:
        found.append(child)
        child = walker.GetNextSiblingElement(child)
    return found


def find(root: Any, walker: Any, types: dict[int, str], *, automation_id, control_types):
    """Depth-first search for the first element matching the id, or any of the types."""
    stack = [(root, 0)]
    while stack:
        element, depth = stack.pop()
        found = props(element, types)
        if automation_id is not None:
            if found["automationId"] == automation_id:
                return element, depth
        elif found["controlType"] in control_types:
            return element, depth
        if depth >= 8:
            continue
        stack.extend(reversed([(c, depth + 1) for c in children(element, walker)]))
    return None, -1


def report(container: Any, walker: Any, types: dict[int, str], depth: int) -> None:
    found = props(container, types)
    print(f"found at depth {depth}: {found}")
    print(f"  patterns: {supported(container)}")

    grid = pattern(container, "Grid")
    table = pattern(container, "Table")
    print(f"  Grid pattern:  {'yes' if grid else 'NO'}")
    print(f"  Table pattern: {'yes' if table else 'NO'}")

    if grid:
        try:
            print(f"    RowCount={grid.CurrentRowCount} ColumnCount={grid.CurrentColumnCount}")
        except Exception as exc:
            print(f"    RowCount/ColumnCount: <{type(exc).__name__}>")
    if table:
        for label, method in (
            ("ColumnHeaders", "GetCurrentColumnHeaders"),
            ("RowHeaders", "GetCurrentRowHeaders"),
        ):
            try:
                array = getattr(table, method)()
                texts = [props(array.GetElement(i), types)["name"] for i in range(array.Length)]
                print(f"    {label}: {texts}")
            except Exception as exc:
                print(f"    {label}: <{type(exc).__name__}>")

    rows = children(container, walker)
    print(f"\n  {len(rows)} ControlView children:")
    for index, row in enumerate(rows):
        found = props(row, types)
        value, name, chosen = cell_text(row, types)
        print(f"  [{index}] {found['controlType']} class={found['className']!r} "
              f"id={found['automationId']!r}")
        print(f"       Name={name!r} Value={value!r} -> the rule reads {chosen!r}")
        print(f"       patterns: {supported(row)}")
        cells = children(row, walker)
        if cells:
            print(f"       {len(cells)} children:")
            for position, cell in enumerate(cells):
                cell_props = props(cell, types)
                value, name, chosen = cell_text(cell, types)
                print(f"         ({position}) {cell_props['controlType']} "
                      f"id={cell_props['automationId']!r} Name={name!r} Value={value!r} "
                      f"-> {chosen!r}")

    if grid:
        print("\n  Grid.GetItem probes:")
        for row_index, column in ((0, 0), (0, 1), (1, 0), (1, 2)):
            try:
                item = grid.GetItem(row_index, column)
            except Exception as exc:
                print(f"    GetItem({row_index},{column}): <{type(exc).__name__}> {exc}")
                continue
            item_props = props(item, types)
            value, name, chosen = cell_text(item, types)
            position = ""
            grid_item = pattern(item, "GridItem")
            if grid_item is not None:
                try:
                    position = (f" gridItem=(row={grid_item.CurrentRow},"
                                f"col={grid_item.CurrentColumn})")
                except Exception:
                    position = " gridItem=<unreadable>"
            print(f"    GetItem({row_index},{column}): {item_props['controlType']} "
                  f"Name={name!r} Value={value!r} -> the rule reads {chosen!r}{position}")


def selection_probe(container: Any, walker: Any, types: dict[int, str]) -> None:
    """Does selecting a row's first cell select the whole row? (v0.2 `SelectRow`.)"""
    grid = pattern(container, "Grid")
    if grid is None:
        print("\n  SelectRow probe skipped: no Grid pattern, so rows are the children "
              "themselves and selecting one is selecting the row.")
        return
    try:
        first = grid.GetItem(1, 0)
    except Exception as exc:
        print(f"\n  SelectRow probe skipped: GetItem(1,0) raised <{type(exc).__name__}>")
        return
    item = pattern(first, "SelectionItem")
    if item is None:
        print("\n  SelectRow probe skipped: the cell has no SelectionItem pattern.")
        return
    item.Select()
    time.sleep(0.2)
    print("\n  SelectRow probe: Select() on row 1, column 0")
    for row_index in (0, 1):
        states = []
        for column in range(grid.CurrentColumnCount):
            cell = grid.GetItem(row_index, column)
            selection = pattern(cell, "SelectionItem")
            states.append(bool(selection.CurrentIsSelected) if selection else None)
        print(f"    row {row_index}: IsSelected per cell = {states}")
    selection = pattern(container, "Selection")
    if selection is not None:
        array = selection.GetCurrentSelection()
        texts = [props(array.GetElement(i), types)["name"] for i in range(array.Length)]
        print(f"    container Selection: {array.Length} selected {texts}")
        print(f"    CanSelectMultiple={selection.CurrentCanSelectMultiple} "
              f"IsSelectionRequired={selection.CurrentIsSelectionRequired}")


def window_by_handle(handle: int):
    from pywinauto import Desktop

    return Desktop(backend="uia").window(handle=handle).element_info.element


def window_by_title(title: str, deadline: float):
    from pywinauto import Desktop

    while time.monotonic() < deadline:
        try:
            window = Desktop(backend="uia").window(title=title)
            return window.element_info.element
        except Exception:
            time.sleep(0.3)
    raise TimeoutError(f"no window titled {title!r} within the start timeout")


def probe_qt() -> int:
    """Launch the probe app, measure its table and its list, then close it."""
    app = subprocess.Popen([sys.executable, str(PROBE_APP)])
    try:
        root = window_by_title(QT_TITLE, time.monotonic() + QT_START_TIMEOUT)
        instance = uia()
        types = {v: k for k, v in instance.known_control_types.items()}
        walker = instance.iuia.ControlViewWalker
        for label, control_types in (
            ("the QTableWidget", {"Table", "DataGrid"}),
            ("the QListWidget", {"List"}),
        ):
            print(f"\n=== {label} ===")
            container, depth = find(
                root, walker, types, automation_id=None, control_types=control_types
            )
            if container is None:
                print(f"not found (control types {sorted(control_types)})")
                continue
            report(container, walker, types, depth)
            selection_probe(container, walker, types)
        return 0
    finally:
        app.terminate()
        app.wait(timeout=10)


def probe_handle(handle: int, automation_id: str | None) -> int:
    root = window_by_handle(handle)
    instance = uia()
    types = {v: k for k, v in instance.known_control_types.items()}
    walker = instance.iuia.ControlViewWalker
    container, depth = find(
        root,
        walker,
        types,
        automation_id=automation_id,
        control_types={"Table", "DataGrid", "List"},
    )
    if container is None:
        what = f"automationId {automation_id!r}" if automation_id else "a grid or list"
        print(f"no {what} under window {handle}")
        return 1
    report(container, walker, types, depth)
    selection_probe(container, walker, types)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="target", required=True)
    sub.add_parser("qt", help="launch grid_probe_app.py and probe its table and list")
    by_handle = sub.add_parser("handle", help="probe a grid or list in an open window")
    by_handle.add_argument("handle", type=int)
    by_handle.add_argument(
        "--automation-id",
        help="pick the container by AutomationId instead of by control type",
    )
    args = parser.parse_args(argv)
    # Every value read here is Turkish text from a Turkish UI. The Windows console default
    # is a legacy code page, which turns "Ayşe" into "Ay?e" and makes the output useless as
    # evidence, so the probe insists on UTF-8 for its own output.
    sys.stdout.reconfigure(encoding="utf-8")
    if sys.platform != "win32":
        print("UI Automation is a Windows API; this probe only runs on Windows.")
        return 2
    if args.target == "qt":
        return probe_qt()
    return probe_handle(args.handle, args.automation_id)


if __name__ == "__main__":
    raise SystemExit(main())
