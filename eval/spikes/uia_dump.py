"""UIA tree dump spike (#6): how much identifying information do candidate pilot apps expose?

dump  (Windows only) walks the raw UI Automation view of every visible top-level window of a
      target process with pywinauto's uia backend and writes eval/spikes/uia-dumps/<id>.json.
stats (any OS) reads dump files and prints the property-richness tables for uia-dump.md.

Usage on Windows, in a venv with `pip install pywinauto==0.6.9`, target apps open:
    python eval\\spikes\\uia_dump.py dump
    python eval\\spikes\\uia_dump.py dump --only keepass2 --only keepassxc
    python eval\\spikes\\uia_dump.py dump --id calc --process CalculatorApp.exe --technology UWP

Usage on any OS:
    python3 eval/spikes/uia_dump.py stats
    python3 eval/spikes/uia_dump.py stats --by-type eval/spikes/uia-dumps/keepass2.json
"""

from __future__ import annotations

import argparse
import json
import ntpath
import platform
import re
import sys
import time
from collections import Counter
from collections.abc import Callable, Iterable
from datetime import datetime
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
TARGETS = HERE / "uia-targets.json"
DUMPS = HERE / "uia-dumps"
FORMAT = "ayna-uia-dump/0"
MAX_NODES = 20_000
MAX_DEPTH = 64
MAX_TEXT = 200

# Control types a test step acts on. Containers (List, Tree, Tab, Table, ToolBar…) and labels
# (Text) are left out: their items and the controls they label are what tests address.
INTERACTIVE_TYPES = frozenset({
    "Button", "CheckBox", "ComboBox", "DataItem", "Document", "Edit", "Hyperlink", "ListItem",
    "MenuItem", "RadioButton", "Slider", "Spinner", "SplitButton", "TabItem", "TreeItem",
})

# Patterns recorded per element, read as UIA_Is<Name>PatternAvailablePropertyId.
PATTERNS = (
    "Invoke", "Value", "Toggle", "SelectionItem", "ExpandCollapse", "RangeValue", "Text",
    "Scroll", "Window", "LegacyIAccessible",
)

# AutomationIds that a framework generated rather than a developer chose: Win32 control ids
# ("1001") and GUIDs. They identify an element but say nothing about it.
GENERATED_ID = re.compile(r"\d+|[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}")


def clip(text: str | None) -> str | None:
    """Cut long strings (list rows, document text) so dumps stay small and leak little."""
    if text is None or len(text) <= MAX_TEXT:
        return text
    return text[:MAX_TEXT] + "…"


def walk(
    roots: Iterable[Any],
    read: Callable[[Any], dict],
    children: Callable[[Any], list],
    max_nodes: int = MAX_NODES,
    max_depth: int = MAX_DEPTH,
) -> tuple[list[dict], bool]:
    """Flatten the trees under `roots` in pre-order.

    Each element gets its id (position in the list), its parent's id, its depth and its index
    among its siblings, followed by whatever `read` returns. The flag is True when `max_nodes`
    or `max_depth` cut the walk short.
    """
    elements: list[dict] = []
    truncated = False
    stack = [(root, None, 0, i) for i, root in reversed(list(enumerate(roots)))]
    while stack:
        if len(elements) >= max_nodes:
            return elements, True
        node, parent, depth, index = stack.pop()
        element = {"id": len(elements), "parent": parent, "depth": depth, "index": index}
        element.update(read(node))
        elements.append(element)
        kids = children(node)
        if kids and depth >= max_depth:
            truncated = True
            continue
        for i, kid in reversed(list(enumerate(kids))):
            stack.append((kid, element["id"], depth + 1, i))
    return elements, truncated


class UiaReader:
    """Reads elements from the raw IUIAutomationElement behind pywinauto's UIAElementInfo.

    pywinauto's own properties turn COM errors into None or "", which hides them, so every
    property is read here on its own: a failing call (an element that vanished, a provider that
    does not implement a property) costs only that value, and `errors` counts it.
    Value-pattern contents are never read.
    """

    def __init__(self, type_names: dict[int, str], pattern_ids: list[tuple[str, int]]) -> None:
        self.type_names = type_names
        self.pattern_ids = pattern_ids
        self.errors = 0

    def get(self, getter: Callable[[], Any]) -> Any:
        try:
            return getter()
        except Exception:  # comtypes COMError, or pywinauto failing on an odd provider
            self.errors += 1
            return None

    def children(self, info: Any) -> list:
        # pywinauto skips children that fail and returns [] when the whole call fails.
        return self.get(info.children) or []

    def read(self, info: Any) -> dict:
        el = info.element
        type_id = self.get(lambda: el.CurrentControlType)
        rect = self.get(lambda: el.CurrentBoundingRectangle)
        labeled_by = self.get(lambda: el.CurrentLabeledBy)
        element = {
            "control_type": self.type_names.get(type_id, type_id),
            "automation_id": clip(self.get(lambda: el.CurrentAutomationId)),
            "name": clip(self.get(lambda: el.CurrentName)),
            "class_name": self.get(lambda: el.CurrentClassName),
            "framework_id": self.get(lambda: el.CurrentFrameworkId),
            "localized_control_type": self.get(lambda: el.CurrentLocalizedControlType),
            "help_text": clip(self.get(lambda: el.CurrentHelpText)),
            "access_key": self.get(lambda: el.CurrentAccessKey),
            "accelerator_key": self.get(lambda: el.CurrentAcceleratorKey),
            # A NULL COM pointer is falsy: most elements have no LabeledBy.
            "labeled_by": clip(self.get(lambda: labeled_by.CurrentName)) if labeled_by else None,
            "enabled": self.get(lambda: bool(el.CurrentIsEnabled)),
            "offscreen": self.get(lambda: bool(el.CurrentIsOffscreen)),
            "keyboard_focusable": self.get(lambda: bool(el.CurrentIsKeyboardFocusable)),
            "is_password": self.get(lambda: bool(el.CurrentIsPassword)),
            "is_control_element": self.get(lambda: bool(el.CurrentIsControlElement)),
            "is_content_element": self.get(lambda: bool(el.CurrentIsContentElement)),
            "has_hwnd": self.get(lambda: bool(el.CurrentNativeWindowHandle)),
            "bounds": None if rect is None else [rect.left, rect.top, rect.right, rect.bottom],
        }
        if self.pattern_ids:
            element["patterns"] = [
                name for name, pid in self.pattern_ids
                if self.get(lambda: el.GetCurrentPropertyValue(pid))
            ]
        return element


def uia_reader(patterns: bool) -> UiaReader:
    from pywinauto.uia_defines import IUIA

    iuia = IUIA()
    ids = [(p, getattr(iuia.UIA_dll, f"UIA_Is{p}PatternAvailablePropertyId", None)) for p in PATTERNS]
    pattern_ids = [(p, pid) for p, pid in ids if pid is not None] if patterns else []
    return UiaReader(dict(iuia.known_control_type_ids), pattern_ids)


def find_windows(process: str | None, title_re: str | None) -> list:
    """Visible top-level windows whose exe name is `process` and whose title matches `title_re`.

    Owned dialogs usually appear under their owner in the UIA tree; if one is top-level
    instead, the process filter still picks it up as an extra root.
    """
    from pywinauto import Desktop
    from pywinauto.application import process_module

    found = []
    for window in Desktop(backend="uia").windows(visible_only=True):  # the default is False
        info = window.element_info
        if title_re and not re.search(title_re, info.name or ""):
            continue
        if process:
            try:
                exe = process_module(info.process_id)
            except Exception:  # access denied (elevated process) or the process just exited
                continue
            if ntpath.basename(exe).lower() != process.lower():
                continue
        found.append(info)
    return found


def exe_info(process_id: int) -> dict:
    """Exe file name and file version (a.b.c.d). The full path is left out: it names the user."""
    import win32api
    from pywinauto.application import process_module

    try:
        path = process_module(process_id)
    except Exception:
        return {"exe": None, "file_version": None}
    try:
        info = win32api.GetFileVersionInfo(path, "\\")
        ms, ls = info["FileVersionMS"], info["FileVersionLS"]
        version = f"{ms >> 16}.{ms & 0xFFFF}.{ls >> 16}.{ls & 0xFFFF}"
    except Exception:  # pywintypes.error: the exe has no version resource
        version = None
    return {"exe": ntpath.basename(path), "file_version": version}


def window_dpi(handle: int) -> int | None:
    """DPI the window renders at; 96 on a scaled display means the app is not DPI-aware."""
    import ctypes

    try:
        return ctypes.windll.user32.GetDpiForWindow(handle) or None
    except (AttributeError, OSError):  # GetDpiForWindow needs Windows 10 1607+
        return None


def dump_target(target: dict, out_dir: Path, args: argparse.Namespace) -> Path | None:
    import pywinauto

    windows = find_windows(target.get("process"), target.get("title_re"))
    if not windows:
        print(f"{target['id']}: no visible window found, skipped", file=sys.stderr)
        return None
    reader = uia_reader(not args.no_patterns)
    start = time.perf_counter()
    elements, truncated = walk(windows, reader.read, reader.children, args.max_nodes, args.max_depth)
    seconds = time.perf_counter() - start
    doc = {
        "format": FORMAT,
        "target": target,
        "captured_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "machine": {
            "os": platform.platform(),
            "python": platform.python_version(),
            "pywinauto": pywinauto.__version__,
        },
        "app": exe_info(windows[0].process_id),
        "windows": [
            {
                "title": clip(reader.get(lambda: w.name)),
                "class_name": reader.get(lambda: w.class_name),
                "dpi": window_dpi(reader.get(lambda: w.handle) or 0),
            }
            for w in windows
        ],
        "walk": {
            "seconds": round(seconds, 2),
            "elements": len(elements),
            "truncated": truncated,
            "read_errors": reader.errors,
            "max_nodes": args.max_nodes,
            "max_depth": args.max_depth,
            "patterns": not args.no_patterns,
        },
        "elements": elements,
    }
    path = out_dir / f"{target['id']}.json"
    write_dump(doc, path)
    note = " (truncated)" if truncated else ""
    print(f"{target['id']}: {len(elements)} elements{note} in {seconds:.1f} s -> {path}")
    return path


def write_dump(doc: dict, path: Path) -> None:
    """Write `doc` as JSON with one element per line, so dumps stay readable and diff well."""
    head = json.dumps({k: v for k, v in doc.items() if k != "elements"}, ensure_ascii=False, indent=2)
    rows = ",\n".join("    " + json.dumps(e, ensure_ascii=False) for e in doc["elements"])
    # head ends with "\n}": reopen it, append the element list, close it again.
    path.write_text(f'{head[:-2]},\n  "elements": [\n{rows}\n  ]\n}}\n', encoding="utf-8")


def has_text(value: Any) -> bool:
    return isinstance(value, str) and value.strip() != ""


def richness(doc: dict) -> dict:
    """Counts over all elements of a dump and over its interactive ones.

    Elements inside a TitleBar (system menu, minimise/maximise/close) belong to the Windows
    frame, not the app, and never have an AutomationId (#9), so they are not interactive here.
    """
    elements = doc["elements"]
    root: dict[int, int] = {}
    frame: set[int] = set()
    for e in elements:  # pre-order: a parent always comes before its children
        parent = e["parent"]
        root[e["id"]] = e["id"] if parent is None else root[parent]
        if e.get("control_type") == "TitleBar" or parent in frame:
            frame.add(e["id"])
    ids_per_window = Counter(
        (root[e["id"]], e["automation_id"].strip())
        for e in elements if has_text(e.get("automation_id"))
    )
    interactive = [
        e for e in elements
        if e.get("control_type") in INTERACTIVE_TYPES and e["id"] not in frame
    ]
    with_id = [e for e in interactive if has_text(e.get("automation_id"))]
    by_type: dict[str, Counter] = {}
    for e in elements:
        row = by_type.setdefault(str(e.get("control_type") or "?"), Counter())
        row["count"] += 1
        row["automation_id"] += has_text(e.get("automation_id"))
        row["name"] += has_text(e.get("name"))
    return {
        "elements": len(elements),
        "frame": len(frame),
        "interactive": len(interactive),
        "automation_id": len(with_id),
        "automation_id_generated": sum(
            bool(GENERATED_ID.fullmatch(e["automation_id"].strip())) for e in with_id
        ),
        "automation_id_unique": sum(
            ids_per_window[(root[e["id"]], e["automation_id"].strip())] == 1 for e in with_id
        ),
        "name": sum(has_text(e.get("name")) for e in interactive),
        "either": sum(
            has_text(e.get("automation_id")) or has_text(e.get("name")) for e in interactive
        ),
        "by_type": by_type,
    }


def pct(part: int, whole: int) -> str:
    return f"{100 * part / whole:.0f}% ({part}/{whole})" if whole else "–"


def stats_table(docs: list[dict]) -> str:
    lines = [
        "| Dump | App | Technology | Version | Walk | Elements | Interactive | AutomationId "
        "| … generated | … unique in window | Name | AutomationId or Name |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for doc in docs:
        r = richness(doc)
        target, app, walk_info = doc["target"], doc.get("app", {}), doc.get("walk", {})
        version = target.get("version") or app.get("file_version") or "?"
        seconds = walk_info.get("seconds")
        lines.append(
            f"| {target['id']} | {target.get('app', '?')} | {target.get('technology', '?')} "
            f"| {version} | {'?' if seconds is None else f'{seconds} s'} | {r['elements']} "
            f"| {r['interactive']} | {pct(r['automation_id'], r['interactive'])} "
            f"| {pct(r['automation_id_generated'], r['automation_id'])} "
            f"| {pct(r['automation_id_unique'], r['automation_id'])} "
            f"| {pct(r['name'], r['interactive'])} | {pct(r['either'], r['interactive'])} |"
        )
    lines += [
        "",
        "Interactive = control types " + ", ".join(sorted(INTERACTIVE_TYPES)) + ", "
        "outside the window frame (TitleBar). AutomationId and Name count when non-blank. *… generated* (numeric or GUID) and "
        "*… unique in window* are shares of the interactive elements that have an AutomationId.",
    ]
    return "\n".join(lines)


def by_type_table(doc: dict) -> str:
    target = doc["target"]
    lines = [
        f"### {target['id']}: {target.get('app', '?')} ({target.get('technology', '?')})",
        "",
        "| Control type | Interactive | Count | AutomationId | Name |",
        "|---|---|---|---|---|",
    ]
    rows = sorted(richness(doc)["by_type"].items(), key=lambda item: (-item[1]["count"], item[0]))
    for control_type, row in rows:
        lines.append(
            f"| {control_type} | {'yes' if control_type in INTERACTIVE_TYPES else ''} "
            f"| {row['count']} | {pct(row['automation_id'], row['count'])} "
            f"| {pct(row['name'], row['count'])} |"
        )
    return "\n".join(lines)


def load_dumps(paths: list[Path]) -> list[dict]:
    files: list[Path] = []
    for path in paths:
        files += sorted(path.glob("*.json")) if path.is_dir() else [path]
    return [json.loads(f.read_text(encoding="utf-8")) for f in files]


def select_targets(args: argparse.Namespace) -> list[dict]:
    if args.id:
        if not (args.process or args.title_re):
            sys.exit("--id needs --process and/or --title-re")
        return [{
            "id": args.id, "app": args.app or args.id, "technology": args.technology,
            "process": args.process, "title_re": args.title_re, "state": args.state,
        }]
    targets = json.loads((args.targets or TARGETS).read_text(encoding="utf-8"))
    unknown = set(args.only) - {t["id"] for t in targets}
    if unknown:
        sys.exit(f"Unknown target id(s): {', '.join(sorted(unknown))}")
    return [t for t in targets if not args.only or t["id"] in args.only]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    dump = sub.add_parser("dump", help="dump UIA trees of running apps (Windows only)")
    dump.add_argument("--targets", type=Path, help=f"JSON target list (default: {TARGETS.name})")
    dump.add_argument("--only", action="append", default=[], metavar="ID", help="repeatable")
    dump.add_argument("--id", help="one-off target instead of the list; also the file name")
    dump.add_argument("--process", help="exe name of a one-off target, e.g. KeePass.exe")
    dump.add_argument("--title-re", help="regex searched in the window title of a one-off target")
    dump.add_argument("--app", help="app name of a one-off target")
    dump.add_argument("--technology", help="UI technology of a one-off target, e.g. WPF")
    dump.add_argument("--state", help="what was on screen for a one-off target")
    dump.add_argument("--out", type=Path, default=DUMPS)
    dump.add_argument("--max-nodes", type=int, default=MAX_NODES)
    dump.add_argument("--max-depth", type=int, default=MAX_DEPTH)
    dump.add_argument("--no-patterns", action="store_true", help="skip pattern checks (faster)")
    stats = sub.add_parser("stats", help="property-richness tables from dumps (any OS)")
    stats.add_argument("dumps", nargs="*", type=Path, default=[DUMPS], help="files or folders")
    stats.add_argument("--by-type", action="store_true", help="add a table per control type")
    args = parser.parse_args(argv)

    if args.command == "stats":
        docs = load_dumps(args.dumps)
        if not docs:
            sys.exit("No dump files found.")
        print(stats_table(docs))
        if args.by_type:
            for doc in docs:
                print("\n" + by_type_table(doc))
        return 0

    if sys.platform != "win32":
        sys.exit("dump needs Windows (UI Automation); stats runs anywhere.")
    targets = select_targets(args)
    args.out.mkdir(parents=True, exist_ok=True)
    written = [p for p in (dump_target(t, args.out, args) for t in targets) if p]
    print(f"\nDumped {len(written)} of {len(targets)} targets.")
    if written:
        print("\n" + stats_table(load_dumps(written)))
    return 0 if written else 1


if __name__ == "__main__":
    sys.exit(main())
