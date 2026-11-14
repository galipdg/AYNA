r"""Does the win32 backend expose identity that UI Automation does not? (#23)

The issue asks for a fallback: "when UIA exposes no usable identifying property, query the
win32 backend for the same element". It is titled a **trial**, and two things already in the
agent decide most of it, so this measures before anything is built:

* ``model.NEVER_MATCH`` says ``native_window_handle`` is "session-scoped: a new handle every
  run". A fallback that merely *finds* the element by HWND therefore gains nothing for
  identification -- whatever win32 contributes has to survive a restart to count.
* ``model._GENERATED_ID`` already rejects a bare number as an AutomationId, and "a Win32
  control id (1001)" is its own first example. For a Win32/WinForms control UIA's AutomationId
  usually *is* the control id, so ``GetDlgCtrlID`` would hand back the number the model
  deliberately throws away.

So the decisive question is not "can win32 see this element" but **"is what it says stable
across runs?"**, which is why `compare` takes two runs of the same screen from two separate
launches of the application.

The UIA side is the agent's own walk (`recognition.UiaDesktop`), so the descriptors and the
`nativeWindowHandle` are the product's, not a second implementation. The win32 side is
pywinauto's `HwndWrapper` on that same handle -- the HWND is the one identifier both views of
an element certainly share, so it is the join key. Geometry is not, which is the lesson #22
settled: identity decides, geometry only locates.

Usage (Windows only, from the repository root, on the **agent's** venv because the recognition
backend reaches `ayna_agent.rpc` for its exception types):

    agent/.venv/Scripts/python.exe eval/spikes/win32_probe.py probe --process KeePass.exe \
        --json eval/spikes/win32-keepass2-run1.json
    agent/.venv/Scripts/python.exe eval/spikes/win32_probe.py compare \
        eval/spikes/win32-keepass2-run1.json eval/spikes/win32-keepass2-run2.json

The pure parts -- the per-control-type table, the gain rule and the cross-run comparison -- are
tested in `test_win32_probe.py` and run on any OS.
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]

# By repository layout, as `eval/rq1/measure.py` does: `eval` installs no packages and does not
# depend on the agent. `model` is UIA-free, so the pure half of this imports anywhere.
if str(REPO / "agent") not in sys.path:
    sys.path.insert(0, str(REPO / "agent"))

from ayna_agent.model import Element, is_generated_id


@dataclass(frozen=True)
class Seen:
    """One element as the two backends describe it."""

    element_id: str
    control_type: str
    #: UIA's view, from the agent's own walk.
    automation_id: str | None
    name: str | None
    class_name: str | None
    native_window_handle: int | None
    #: win32's view of the same HWND; None when the element has no window of its own.
    win32: dict[str, Any] | None = None

    @property
    def has_hwnd(self) -> bool:
        return bool(self.native_window_handle)

    @property
    def uia_id_usable(self) -> bool:
        """Whether UIA's AutomationId can identify this element at all, by the model's rule."""
        return bool(self.automation_id) and not is_generated_id(self.automation_id)

    @property
    def win32_control_id(self) -> int | None:
        """The raw `GetDlgCtrlID`, including a zero: the saved run keeps what was read."""
        value = (self.win32 or {}).get("control_id")
        return value if isinstance(value, int) else None

    @property
    def usable_control_id(self) -> int | None:
        """The control id only when it could identify anything.

        Zero is Windows' "this window has no control id" and WinForms leaves it at zero for
        the controls it creates itself, so counting it as present would make the cross-run
        comparison report "the control id is stable" about elements that have none -- which
        is the one way this trial could flatter the fallback it is meant to judge.
        """
        return self.win32_control_id or None

    @property
    def win32_adds_a_number(self) -> bool:
        """Whether win32 offers a non-zero control id that UIA's AutomationId did not.

        A zero control id is Windows' "this window has none", which WinForms leaves at zero for
        controls it creates itself, so it identifies nothing. And a control id equal to the
        AutomationId is not an addition: it is the same number arriving by another road.
        """
        number = self.usable_control_id
        if number is None:
            return False
        return str(number) != (self.automation_id or "")

    def to_dict(self) -> dict[str, Any]:
        return {
            "elementId": self.element_id,
            "controlType": self.control_type,
            "automationId": self.automation_id,
            "name": self.name,
            "className": self.class_name,
            "nativeWindowHandle": self.native_window_handle,
            "uiaIdUsable": self.uia_id_usable,
            "win32": self.win32,
        }


def from_dict(row: Mapping[str, Any]) -> Seen:
    return Seen(
        element_id=str(row["elementId"]),
        control_type=str(row.get("controlType") or ""),
        automation_id=row.get("automationId"),
        name=row.get("name"),
        class_name=row.get("className"),
        native_window_handle=row.get("nativeWindowHandle"),
        win32=row.get("win32"),
    )


# ------------------------------------------------------------------------------- the report

#: The row that sums every control type.
TOTAL = "TOTAL"


@dataclass
class TypeRow:
    """What one control type gains, or does not."""

    control_type: str
    total: int = 0
    uia_identified: int = 0
    with_hwnd: int = 0
    win32_adds: int = 0
    #: element ids where UIA has no usable id and win32 offers a number: the gain, if any.
    gained: list[str] = field(default_factory=list)

    @property
    def uia_blind(self) -> int:
        """Elements UIA cannot identify by AutomationId -- the ones the issue is about."""
        return self.total - self.uia_identified


def by_control_type(seen: Sequence[Seen]) -> list[TypeRow]:
    """One row per control type, plus a TOTAL, in descending size then name."""
    rows: dict[str, TypeRow] = {}
    for item in seen:
        row = rows.setdefault(item.control_type, TypeRow(item.control_type))
        total = rows.setdefault(TOTAL, TypeRow(TOTAL))
        for target in (row, total):
            target.total += 1
            target.uia_identified += item.uia_id_usable
            target.with_hwnd += item.has_hwnd
            if item.win32_adds_a_number:
                target.win32_adds += 1
                if not item.uia_id_usable:
                    target.gained.append(item.element_id)
    ordered = sorted(
        (row for name, row in rows.items() if name != TOTAL),
        key=lambda row: (-row.total, row.control_type),
    )
    return [*ordered, rows[TOTAL]] if TOTAL in rows else ordered


def table(rows: Sequence[TypeRow]) -> list[str]:
    """A markdown table ready to paste into the issue."""
    lines = [
        "| control type | elements | UIA identifies | has an HWND | win32 adds a number |",
        "|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {'**' + row.control_type + '**' if row.control_type == TOTAL else row.control_type} "
            f"| {row.total} | {row.uia_identified} | {row.with_hwnd} | {row.win32_adds} |"
        )
    return lines


# ---------------------------------------------------------------------------- across runs


@dataclass(frozen=True)
class Drift:
    """Whether the numbers each backend offers survive a restart."""

    #: Elements matched between the two runs, by (controlType, name, className).
    matched: int
    automation_id_stable: int
    automation_id_changed: list[tuple[str, str | None, str | None]]
    control_id_stable: int
    control_id_changed: list[tuple[str, int | None, int | None]]
    #: Matched elements that had a window on at least one side and kept the same handle.
    handle_stable: int

    @property
    def verdict(self) -> str:
        """What the measurement says about building the fallback at all."""
        if self.control_id_changed:
            return (
                "win32's control id is NOT stable across runs, so a win32 fallback cannot "
                "identify anything UIA cannot: it would store a number that is wrong on the "
                "next launch."
            )
        if not self.control_id_stable:
            return (
                "no element offered a win32 control id at all, so there is nothing for a "
                "fallback to fall back to."
            )
        if self.automation_id_changed:
            return (
                "win32's control id is stable while UIA's AutomationId is not, which is the "
                "one case where a win32 fallback pays for itself."
            )
        return (
            "win32's control id is stable, but so is UIA's AutomationId on the same elements, "
            "so the identity is already in the snapshot and the question is the model's "
            "generated-id rule, not a second backend."
        )


def key_of(item: Seen) -> tuple[str, str | None, str | None]:
    """How the same element is recognised across two runs.

    Deliberately **not** the element id (a position in one walk), the HWND (session-scoped by
    `NEVER_MATCH`) or the AutomationId (the very thing under test). Name and class name are what
    is left, which is why an element with neither cannot take part in the comparison -- and
    those are exactly the elements #23 is about, so the probe says how many it had to drop.
    """
    return (item.control_type, item.name, item.class_name)


def compare_runs(first: Sequence[Seen], second: Sequence[Seen]) -> Drift:
    """Match two runs of the same screen and report what moved."""
    # Only keys that occur exactly once on each side can be matched without guessing.
    left = _unique_by_key(first)
    right = _unique_by_key(second)
    # A key holds Nones (a nameless element is the whole point of #23), and None does not
    # compare with str, so sort on a coerced copy rather than on the key itself.
    shared = sorted(set(left) & set(right), key=lambda key: tuple(part or "" for part in key))
    id_stable, id_changed = 0, []
    control_stable, control_changed = 0, []
    handle_stable = 0
    for key in shared:
        a, b = left[key], right[key]
        if a.automation_id == b.automation_id:
            id_stable += 1
        else:
            id_changed.append((a.element_id, a.automation_id, b.automation_id))
        if a.usable_control_id is not None or b.usable_control_id is not None:
            if a.usable_control_id == b.usable_control_id:
                control_stable += 1
            else:
                control_changed.append(
                    (a.element_id, a.usable_control_id, b.usable_control_id)
                )
        # Only elements that actually have a window: 58 of KeePass 2's 74 have none, and
        # counting None == None as "the handle did not move" read as evidence against
        # `NEVER_MATCH`'s session-scoped claim when it was really 49 absent handles.
        if (a.has_hwnd or b.has_hwnd) and a.native_window_handle == b.native_window_handle:
            handle_stable += 1
    return Drift(
        matched=len(shared),
        automation_id_stable=id_stable,
        automation_id_changed=id_changed,
        control_id_stable=control_stable,
        control_id_changed=control_changed,
        handle_stable=handle_stable,
    )


def _unique_by_key(items: Sequence[Seen]) -> dict[tuple[str, str | None, str | None], Seen]:
    counts = Counter(key_of(item) for item in items)
    return {key_of(item): item for item in items if counts[key_of(item)] == 1}


# -------------------------------------------------------------------------------- probing


def win32_view(handle: int) -> dict[str, Any]:
    """What pywinauto's win32 backend says about the window `handle`."""
    from pywinauto.controls.hwndwrapper import HwndWrapper

    wrapper = HwndWrapper(handle)

    def read(call) -> Any:
        try:
            return call()
        except Exception as error:  # a control can go stale mid-walk, as #161 measured
            return f"<{type(error).__name__}: {error}>"

    rectangle = read(wrapper.rectangle)
    return {
        "className": read(wrapper.class_name),
        "control_id": read(wrapper.control_id),
        "text": read(wrapper.window_text),
        "friendlyClassName": read(wrapper.friendly_class_name),
        "bounds": None
        if isinstance(rectangle, str)
        else [rectangle.left, rectangle.top, rectangle.right, rectangle.bottom],
    }


def probe(document: Mapping[str, Any]) -> list[Seen]:
    """Describe every element of a snapshot document from both backends."""
    nodes = document.get("elements") or []
    seen: list[Seen] = []
    for entry, element in zip(nodes, _elements(nodes), strict=True):
        handle = element.native_window_handle
        seen.append(
            Seen(
                element_id=str(entry.get("id")),
                control_type=element.control_type or "",
                automation_id=element.automation_id,
                name=element.name,
                class_name=element.class_name,
                native_window_handle=handle,
                win32=win32_view(handle) if handle else None,
            )
        )
    return seen


def _elements(nodes: Sequence[Mapping[str, Any]]) -> list[Element]:
    """The descriptor of each node, as the agent wrote it into the snapshot."""
    return [Element.from_json(dict(entry.get("element") or {})) for entry in nodes]


def run_probe(args: argparse.Namespace) -> int:
    if platform.system() != "Windows":
        print("probing needs Windows; `compare` runs anywhere", file=sys.stderr)
        return 2
    from ayna_agent.recognition.uia import UiaDesktop

    desktop = UiaDesktop()
    # CoInitializeEx and the control-type table live in setup(); the server normally calls it
    # once on its worker thread, so a script has to do it itself.
    desktop.setup()
    try:
        windows = [
            window
            for window in desktop.list_windows()
            if args.process is None
            or str(window.get("processName") or "").lower() == args.process.lower()
        ]
        if args.title:
            windows = [
                w for w in windows if args.title.lower() in str(w.get("title") or "").lower()
            ]
        if not windows:
            print("no window matched", file=sys.stderr)
            return 1
        window = windows[0]
        print(f"window {window.get('title')!r} handle {window.get('handle')}")
        document = desktop.snapshot(int(window["handle"]), args.timeout_ms)
    finally:
        desktop.close()

    seen = probe(document)
    rows = by_control_type(seen)
    print("\n".join(table(rows)))
    gained = [item for row in rows if row.control_type != TOTAL for item in row.gained]
    print(
        f"\nelements: {len(seen)} · with an HWND: {sum(s.has_hwnd for s in seen)} · "
        f"UIA identifies: {sum(s.uia_id_usable for s in seen)} · "
        f"win32 adds a number UIA did not: {len(gained)}"
    )
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(
            json.dumps(
                {
                    "window": {
                        "title": window.get("title"),
                        "processName": window.get("processName"),
                    },
                    "capture": document.get("capture"),
                    "elements": [item.to_dict() for item in seen],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print(f"wrote {args.json}")
    return 0


def run_compare(args: argparse.Namespace) -> int:
    runs = []
    for path in (args.first, args.second):
        data = json.loads(path.read_text(encoding="utf-8"))
        runs.append([from_dict(row) for row in data["elements"]])
    drift = compare_runs(*runs)
    print(f"matched by (controlType, name, className): {drift.matched}")
    print(
        f"  AutomationId stable: {drift.automation_id_stable}, "
        f"changed: {len(drift.automation_id_changed)}"
    )
    print(
        f"  win32 control id stable: {drift.control_id_stable}, "
        f"changed: {len(drift.control_id_changed)}"
    )
    print(f"  nativeWindowHandle unchanged: {drift.handle_stable} (expected: 0)")
    for element_id, before, after in drift.automation_id_changed[:20]:
        print(f"    AutomationId {element_id}: {before!r} -> {after!r}")
    for element_id, before, after in drift.control_id_changed[:20]:
        print(f"    control id {element_id}: {before!r} -> {after!r}")
    print(f"\n{drift.verdict}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="win32 fallback trial (#23).")
    sub = parser.add_subparsers(dest="command", required=True)

    one = sub.add_parser("probe", help="describe a window from both backends (Windows only)")
    one.add_argument("--process", help="process name, e.g. KeePass.exe")
    one.add_argument("--title", help="substring of the window title")
    one.add_argument("--timeout-ms", type=int, default=None, help="walk budget")
    one.add_argument("--json", type=Path, help="write the elements here")
    one.set_defaults(run=run_probe)

    two = sub.add_parser("compare", help="two runs of the same screen: what moved")
    two.add_argument("first", type=Path)
    two.add_argument("second", type=Path)
    two.set_defaults(run=run_compare)

    args = parser.parse_args(argv)
    return int(args.run(args))


if __name__ == "__main__":
    raise SystemExit(main())
