"""Bisect the cost of a UI Automation walk over one window (#161).

`uia_tree_dump.py` measured a property-complete walk of one KeePass 2 (WinForms) window at
278.5 s for 106 elements, against 0.47 s for Qt's 84 and 1.97 s for WPF's 149 (#6,
finding 7). This script answers *what that time is spent on* by walking the same window
once per cost centre and timing every element separately:

    navigate    tree traversal only, no property read
    properties  traversal + the 15 plain properties the dump reads
    patterns    traversal + the 10 pattern-availability probes
    labeledby   traversal + CurrentLabeledBy and the label's name
    full        all of the above: the work `uia_tree_dump.py dump` does
    cached      one FindAll(subtree) with a cache request, then reads from the cache

Totals alone hide the shape of the problem, so each mode also reports the per-element
distribution and the slowest elements by name: 2.6 s per element on average is equally
consistent with every element being slow and with three elements taking a minute each.

Element counts are deduplicated by window handle like `uia_tree_dump.py`'s, so a dialog that is
also a child of its owner is walked once, and the roots are ordered owner-first so that the
depths are the real ones.

Usage (Windows only):

    python uia_probe.py --process KeePass.exe                 # every visible window
    python uia_probe.py --process KeePass.exe --title "Add Entry"
    python uia_probe.py --handle 1444030 --handle 1508968
    python uia_probe.py --process KeePass.exe --modes navigate,properties --repeat 3
    python uia_probe.py ... --json eval/spikes/uia-probe-keepass2.json

The pure parts (percentiles, the summary table, mode selection) are tested in
`test_uia_probe.py` and run on any OS.
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from uia_tree_dump import MAX_DEPTH, MAX_NODES, PATTERNS, find_windows, window_dpi

HERE = Path(__file__).resolve().parent
FORMAT = "ayna-uia-probe/0"

# The plain properties `uia_tree_dump.py` reads per element, in its order. LabeledBy is not here:
# it dereferences another element, so it is its own cost centre.
PLAIN_PROPERTIES = (
    "CurrentControlType", "CurrentBoundingRectangle", "CurrentAutomationId", "CurrentName",
    "CurrentClassName", "CurrentFrameworkId", "CurrentLocalizedControlType", "CurrentHelpText",
    "CurrentAccessKey", "CurrentAcceleratorKey", "CurrentIsEnabled", "CurrentIsOffscreen",
    "CurrentIsKeyboardFocusable", "CurrentIsPassword", "CurrentIsControlElement",
    "CurrentIsContentElement", "CurrentNativeWindowHandle",
)

MODES = ("navigate", "properties", "patterns", "labeledby", "full", "cached")


def percentiles(values: list[float], points: tuple[int, ...] = (50, 90, 99)) -> dict[str, float]:
    """Nearest-rank percentiles, plus min and max. Empty input gives an empty dict."""
    if not values:
        return {}
    ordered = sorted(values)
    out = {"min": ordered[0], "max": ordered[-1]}
    for point in points:
        rank = max(1, -(-point * len(ordered) // 100))     # ceil(point/100 * n)
        out[f"p{point}"] = ordered[rank - 1]
    return out


def share(part: float, whole: float) -> str:
    return "—" if not whole else f"{100 * part / whole:.0f}%"


def summary_table(result: dict) -> str:
    """One row per mode: total, per element, and the distribution of per-element times."""
    rows = [("Mode", "Elements", "Total s", "Mean ms", "p50 ms", "p90 ms", "p99 ms", "Max ms",
             "Share of full")]
    full_total = next((m["total_s"] for m in result["modes"] if m["mode"] == "full"), 0.0)
    for mode in result["modes"]:
        stats = mode["per_element_ms"]
        count = mode["elements"]
        rows.append((
            mode["mode"],
            str(count),
            f"{mode['total_s']:.2f}",
            f"{1000 * mode['total_s'] / count:.2f}" if count else "—",
            f"{stats.get('p50', 0):.2f}" if stats else "—",
            f"{stats.get('p90', 0):.2f}" if stats else "—",
            f"{stats.get('p99', 0):.2f}" if stats else "—",
            f"{stats.get('max', 0):.2f}" if stats else "—",
            share(mode["total_s"], full_total),
        ))
    widths = [max(len(r[i]) for r in rows) for i in range(len(rows[0]))]
    lines = ["| " + " | ".join(c.ljust(w) for c, w in zip(row, widths)) + " |" for row in rows]
    lines.insert(1, "|" + "|".join("-" * (w + 2) for w in widths) + "|")
    return "\n".join(lines)


def slowest_table(mode: dict, limit: int = 10) -> str:
    rows = [("ms", "ControlType", "Name", "AutomationId", "ClassName", "Depth")]
    for el in mode["slowest"][:limit]:
        rows.append((
            f"{el['ms']:.1f}", str(el["control_type"]), (el["name"] or "")[:28],
            (el["automation_id"] or "")[:24], (el["class_name"] or "")[:30], str(el["depth"]),
        ))
    widths = [max(len(r[i]) for r in rows) for i in range(len(rows[0]))]
    lines = ["| " + " | ".join(c.ljust(w) for c, w in zip(row, widths)) + " |" for row in rows]
    lines.insert(1, "|" + "|".join("-" * (w + 2) for w in widths) + "|")
    return "\n".join(lines)


def nesting_order(handles: list[int], ancestors: dict[int, set[int]]) -> list[int]:
    """The same handles, an owner window always before a window nested inside it.

    `ancestors[handle]` is the set of handles above that window in the UIA tree. KeePass's
    `Add Entry` is both a top-level window and a child of the main form, so whichever of the
    two is walked first decides the depths the other one's elements get. Walking the owner
    first makes every depth the real one (#170 review); the walk itself then skips the
    nested root because its handle has already been seen.
    """
    roots = set(handles)
    indexed = list(enumerate(handles))
    indexed.sort(key=lambda pair: (len(ancestors.get(pair[1], frozenset()) & roots), pair[0]))
    return [handle for _, handle in indexed]


def selected_modes(value: str | None) -> list[str]:
    if not value:
        return list(MODES)
    chosen = [m.strip() for m in value.split(",") if m.strip()]
    unknown = [m for m in chosen if m not in MODES]
    if unknown:
        raise ValueError(f"unknown mode(s): {', '.join(unknown)}; known: {', '.join(MODES)}")
    return chosen


# --- measurement (Windows only below this line) --------------------------------------------


class Probe:
    """Walks a window once per cost centre, timing each element on its own."""

    def __init__(self, pattern_ids: list[tuple[str, int]], type_names: dict[int, str]) -> None:
        self.pattern_ids = pattern_ids
        self.type_names = type_names
        self.errors = 0

    def safe(self, call: Callable[[], Any]) -> Any:
        try:
            return call()
        except Exception:
            self.errors += 1
            return None

    def identity(self, info: Any) -> dict:
        """Cheap identity of an element, read *outside* the timed section."""
        el = info.element
        type_id = self.safe(lambda: el.CurrentControlType)
        return {
            "control_type": self.type_names.get(type_id, type_id),
            "name": self.safe(lambda: el.CurrentName),
            "automation_id": self.safe(lambda: el.CurrentAutomationId),
            "class_name": self.safe(lambda: el.CurrentClassName),
        }

    def read_plain(self, el: Any) -> None:
        for prop in PLAIN_PROPERTIES:
            self.safe(lambda p=prop: getattr(el, p))

    def read_patterns(self, el: Any) -> None:
        for _name, pid in self.pattern_ids:
            self.safe(lambda p=pid: el.GetCurrentPropertyValue(p))

    def read_labeled_by(self, el: Any) -> None:
        label = self.safe(lambda: el.CurrentLabeledBy)
        if label:
            self.safe(lambda: label.CurrentName)

    def work_for(self, mode: str) -> Callable[[Any], None]:
        def nothing(_el: Any) -> None:
            return None

        def plain(el: Any) -> None:
            self.read_plain(el)

        def patterns(el: Any) -> None:
            self.read_patterns(el)

        def labeled(el: Any) -> None:
            self.read_labeled_by(el)

        def full(el: Any) -> None:
            self.read_plain(el)
            self.read_labeled_by(el)
            self.read_patterns(el)

        return {"navigate": nothing, "properties": plain, "patterns": patterns,
                "labeledby": labeled, "full": full}[mode]

    def run(self, roots: list, mode: str) -> dict:
        """Walk every root in pre-order, timing the per-element work of `mode`.

        Traversal time (asking for the children) is charged to the element whose children
        they are, so `navigate` is the cost of the walk itself with no property read.

        Elements are deduplicated by window handle, exactly as `uia_tree_dump.walk` does: a dialog
        that is both a top-level window and a child of its owner would otherwise be walked
        twice, once as a root and once as a descendant, and every count for that subtree
        would double (#170 review — KeePass's `Add Entry` did). The first visit wins, its
        subtree included. The handle is read *outside* the timed section, so it costs no mode
        any time it did not already spend; elements without a handle are never skipped.
        """
        work = self.work_for(mode)
        timings: list[dict] = []
        seen: set[int] = set()
        duplicates = 0
        started = time.perf_counter()
        stack = [(root, 0) for root in reversed(roots)]
        while stack and len(timings) < MAX_NODES:
            info, depth = stack.pop()
            handle = self.safe(lambda i=info: i.handle)     # identity, not measured work
            if handle:
                if handle in seen:
                    duplicates += 1
                    continue
                seen.add(handle)
            element_started = time.perf_counter()
            work(info.element)
            children = self.safe(info.children) or []
            elapsed_ms = 1000 * (time.perf_counter() - element_started)
            entry = {"ms": elapsed_ms, "depth": depth}
            timings.append(entry)
            entry.update(self.identity(info))       # outside the timed section on purpose
            if depth < MAX_DEPTH:
                for child in reversed(children):
                    stack.append((child, depth + 1))
        total = time.perf_counter() - started
        per_element = [t["ms"] for t in timings]
        return {
            "mode": mode,
            "elements": len(timings),
            "total_s": total,
            "per_element_ms": percentiles(per_element),
            "slowest": sorted(timings, key=lambda t: -t["ms"])[:20],
            "read_errors": self.errors,
            "duplicates_skipped": duplicates,
        }

    def run_cached(self, roots: list) -> dict:
        """One FindAll per root with a cache request, then every read from the cache.

        This is the standard fix for a chatty provider: the properties of the whole subtree
        cross the process boundary in one call instead of one call per property.
        """
        from pywinauto.uia_defines import IUIA

        iuia = IUIA().iuia
        dll = IUIA().UIA_dll
        request = iuia.CreateCacheRequest()
        request.TreeScope = 4 + 1                      # Subtree = Element | Children | Descendants
        for prop in ("UIA_ControlTypePropertyId", "UIA_NamePropertyId",
                     "UIA_AutomationIdPropertyId", "UIA_ClassNamePropertyId",
                     "UIA_FrameworkIdPropertyId", "UIA_BoundingRectanglePropertyId",
                     "UIA_HelpTextPropertyId", "UIA_AccessKeyPropertyId",
                     "UIA_AcceleratorKeyPropertyId", "UIA_IsEnabledPropertyId",
                     "UIA_IsOffscreenPropertyId", "UIA_IsKeyboardFocusablePropertyId",
                     "UIA_IsPasswordPropertyId", "UIA_IsControlElementPropertyId",
                     "UIA_IsContentElementPropertyId", "UIA_NativeWindowHandlePropertyId",
                     "UIA_LocalizedControlTypePropertyId"):
            pid = getattr(dll, prop, None)
            if pid is not None:
                self.safe(lambda p=pid: request.AddProperty(p))

        condition = iuia.CreateTrueCondition()
        started = time.perf_counter()
        count = 0
        find_s = 0.0
        seen: set[int] = set()
        duplicates = 0
        for root in roots:
            # A nested dialog's whole subtree comes back inside its owner's result, and a flat
            # FindAll gives no way to skip it element by element, so the nested *root* is
            # skipped instead — which is why the roots are ordered owner-first (#170 review).
            handle = self.safe(lambda r=root: r.handle)
            if handle and handle in seen:
                duplicates += 1
                continue
            find_started = time.perf_counter()
            found = self.safe(lambda r=root: r.element.FindAllBuildCache(4, condition, request))
            find_s += time.perf_counter() - find_started
            if found is None:
                continue
            for i in range(found.Length):
                el = found.GetElement(i)
                count += 1
                for cached in ("CachedControlType", "CachedName", "CachedAutomationId",
                               "CachedClassName", "CachedBoundingRectangle", "CachedIsEnabled",
                               "CachedIsOffscreen", "CachedNativeWindowHandle"):
                    self.safe(lambda c=cached, e=el: getattr(e, c))
                child_handle = self.safe(lambda e=el: e.CachedNativeWindowHandle)
                if child_handle:
                    seen.add(child_handle)
        total = time.perf_counter() - started
        return {
            "mode": "cached",
            "elements": count,
            "total_s": total,
            "find_all_s": find_s,
            "per_element_ms": {},
            "slowest": [],
            "read_errors": self.errors,
            "duplicates_skipped": duplicates,
        }


def build_probe() -> Probe:
    from pywinauto.uia_defines import IUIA

    iuia = IUIA()
    ids = [(p, getattr(iuia.UIA_dll, f"UIA_Is{p}PatternAvailablePropertyId", None))
           for p in PATTERNS]
    return Probe([(p, pid) for p, pid in ids if pid is not None],
                 dict(iuia.known_control_type_ids))


def owner_first(roots: list) -> list:
    """`roots` with every owner window before the dialogs nested inside it.

    The ancestors of each root are read through the UIA parent chain, which costs a handful
    of cross-process calls per root; it is only worth doing when there is more than one root
    and it happens before the clock starts.
    """
    ancestors: dict[int, set[int]] = {}
    for root in roots:
        chain: set[int] = set()
        node = root
        for _ in range(MAX_DEPTH):
            try:
                node = node.parent
            except Exception:
                break
            if node is None:
                break
            try:
                chain.add(node.handle)
            except Exception:
                break
        ancestors[root.handle] = chain
    by_handle = {root.handle: root for root in roots}
    return [by_handle[h] for h in nesting_order([r.handle for r in roots], ancestors)]


def roots_from_args(args: argparse.Namespace) -> list:
    from pywinauto.uia_element_info import UIAElementInfo

    if args.handle:
        return [UIAElementInfo(h) for h in args.handle]
    return find_windows(args.process, args.title)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--process", help="exe file name, e.g. KeePass.exe")
    parser.add_argument("--title", help="regular expression against the window title")
    parser.add_argument("--handle", type=int, action="append",
                        help="window handle; repeatable, overrides --process/--title")
    parser.add_argument("--modes", help=f"comma-separated subset of: {', '.join(MODES)}")
    parser.add_argument("--repeat", type=int, default=1,
                        help="run every mode N times and keep each run (default 1)")
    parser.add_argument("--slowest", type=int, default=10, help="rows in the slowest table")
    parser.add_argument("--json", type=Path, help="write the full result to this file")
    args = parser.parse_args(argv)

    try:
        modes = selected_modes(args.modes)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 2

    if sys.platform != "win32":
        print("uia_probe.py measures UI Automation and only runs on Windows.", file=sys.stderr)
        return 2
    if not args.handle and not args.process:
        print("give --process or --handle", file=sys.stderr)
        return 2

    import pywinauto

    roots = roots_from_args(args)
    if not roots:
        print("no matching window", file=sys.stderr)
        return 1
    if len(roots) > 1:
        roots = owner_first(roots)

    windows = [{"handle": r.handle, "title": r.name, "class_name": r.class_name,
                "dpi": window_dpi(r.handle)} for r in roots]
    print("Windows under probe:")
    for w in windows:
        print(f"  handle={w['handle']} dpi={w['dpi']} {w['title']!r} ({w['class_name']})")

    result: dict[str, Any] = {
        "format": FORMAT,
        "measured_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "pywinauto": pywinauto.__version__,
        "windows": windows,
        "modes": [],
    }

    for run in range(args.repeat):
        for mode in modes:
            probe = build_probe()
            print(f"  running {mode} (run {run + 1}/{args.repeat}) …", flush=True)
            measured = probe.run_cached(roots) if mode == "cached" else probe.run(roots, mode)
            measured["run"] = run + 1
            result["modes"].append(measured)
            print(f"    {measured['elements']} elements in {measured['total_s']:.2f} s"
                  f" ({measured['read_errors']} read errors,"
                  f" {measured['duplicates_skipped']} duplicates skipped)")

    print()
    print(summary_table(result))
    full = [m for m in result["modes"] if m["mode"] == "full"]
    if full and full[0]["slowest"]:
        print()
        print(f"Slowest elements of the full walk (run {full[0]['run']}):")
        print(slowest_table(full[0], args.slowest))

    if args.json:
        args.json.write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n",
                             encoding="utf-8")
        print(f"\nwritten: {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
