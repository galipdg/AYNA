"""RQ1: how often AYNA identifies a control uniquely from its descriptor (#29, feeds #64).

The harness has two halves, split where the rest of the repository splits capture from rules.

**Capture** (``capture``) runs on Windows only and does nothing clever: it drives the agent's
own ``recognition.uia.UiaDesktop`` to snapshot the pilot app's windows and writes each
document to ``eval/rq1/snapshots/<app>/<screen>.json``. The operator opens the screens; nothing
here tries to navigate a pilot app, and nothing re-derives a descriptor.

**Measurement** (``measure``) is pure: it reads those snapshot documents and writes the CSVs.
That is why a number can be re-derived months later without the applications, and why every
rule below is unit-tested off Windows.

It measures **with the product's code, not a copy of it**. ``ayna_agent.model`` and
``ayna_agent.playback.resolve`` are both deliberately free of UI Automation, so they import on
any OS; the identification rule and the comparison are therefore the ones the Spy proposes with
and playback resolves with. A third copy of either in ``eval/`` would have made RQ1 measure the
harness instead of AYNA.

**Recognised** means what SDD §6.1 says, made exact: build the property set the Spy would
propose for the control (``suggestUses`` in ``client/src/shared/repository.ts``), then count the
elements of the *same window* that match it. Exactly one match is recognised; more is
ambiguous; a control with no usable property is unidentifiable. The window is the scope because
it is the scope the Spy counts in and the scope playback resolves in.

**A control** is #6's interactive set with the window frame excluded, kept identical to
``eval/spikes/uia_tree_dump.py`` on purpose so these numbers sit next to the D1 table in
``eval/spikes/uia-dump.md``.

The rate over the elements AYNA found is not the whole truth: a control the walk never produced
cannot appear in it. ``--labels`` adds the human denominator from the procedure in
``labelling.md``; see :func:`load_labels`.

Run it with (from the repository root):

    .venv/Scripts/python.exe eval/rq1/measure.py capture keepass2 --screen main
    .venv/Scripts/python.exe eval/rq1/measure.py measure
    .venv/Scripts/python.exe eval/rq1/measure.py measure keepass2 --labels
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]

# `eval/` installs no packages and does not depend on the agent, so this import is by
# repository layout. Both modules below are UIA-free by contract (their own docstrings say so),
# which is what lets this run and be tested off Windows. `tests/test_measure.py` pins it.
if str(REPO / "agent") not in sys.path:
    sys.path.insert(0, str(REPO / "agent"))

from ayna_agent.model import (
    JSON_NAMES,
    PRIMARY_PRIORITY,
    Element,
    is_generated_id,
)
from ayna_agent.playback.resolve import matches

#: Control types RQ1 counts, from #6's interactive set (`eval/spikes/uia_tree_dump.py`).
#: Identical on purpose: it is the set the D1 table counted, so the numbers compare.
INTERACTIVE_TYPES = frozenset(
    {
        "Button",
        "CheckBox",
        "ComboBox",
        "DataItem",
        "Document",
        "Edit",
        "Hyperlink",
        "ListItem",
        "MenuItem",
        "RadioButton",
        "Slider",
        "Spinner",
        "SplitButton",
        "TabItem",
        "TreeItem",
    }
)

#: Properties the Spy may put in a primary set, best first: the descriptor ADR's priority, then
#: `control_type`. That is `IDENTIFYING_FIELDS` sliced at `controlType` in
#: `client/src/shared/repository.ts`; the client's later fields (windowTitle, siblingIndex,
#: helpText, accessKey) are never primary. Derived from the agent's constant so the shared part
#: cannot drift, and a test checks the client's file still agrees.
PROPOSAL_FIELDS: tuple[str, ...] = (*PRIMARY_PRIORITY, "control_type")

#: Why a control is not recognised, or that it is.
UNIQUE = "unique"
AMBIGUOUS = "ambiguous"
NO_PROPERTY = "no identifying property"

#: What a label may say (`labelling.md`).
LABEL_CONTROL = "control"
LABEL_IGNORE = "ignore"
LABEL_MISSING = "missing"
LABELS = (LABEL_CONTROL, LABEL_IGNORE, LABEL_MISSING)

SNAPSHOTS = HERE / "snapshots"
RESULTS = HERE / "results"
LABEL_DIR = HERE / "labels"
APPS_FILE = HERE / "apps.json"


@dataclass(frozen=True, slots=True)
class Control:
    """One measured control: what it is, what the Spy would propose, and what that matched."""

    app: str
    screen: str
    snapshot_id: str
    element_id: str
    control_type: str
    descriptor: Element
    #: camelCase property -> value, in the order the Spy would add them.
    primary: dict[str, Any]
    match_count: int
    #: From a label file; empty when the screen is not labelled.
    label: str = ""
    note: str = ""

    @property
    def recognised(self) -> bool:
        return self.match_count == 1

    @property
    def reason(self) -> str:
        if not self.primary:
            return NO_PROPERTY
        return UNIQUE if self.match_count == 1 else AMBIGUOUS


@dataclass
class Screen:
    """One captured window and the controls measured in it."""

    app: str
    screen: str
    path: Path
    document: Mapping[str, Any]
    controls: list[Control] = field(default_factory=list)
    #: Controls a person saw that no element row carries (`missing` labels).
    missing: list[str] = field(default_factory=list)
    labelled: bool = False

    @property
    def window_title(self) -> str:
        window = self.document.get("window") or {}
        return str(window.get("title") or "")


# ---------------------------------------------------------------------------- the rules


def is_blank(value: Any) -> bool:
    """A property the descriptor does not have. Blank strings never reach a document."""
    return value is None or (isinstance(value, str) and not value.strip())


def frame_ids(elements: Sequence[Mapping[str, Any]]) -> set[str]:
    """Element ids belonging to the Windows frame: a ``TitleBar`` and its whole subtree.

    They are the system menu and the minimise/maximise/close buttons: they belong to the frame
    rather than to the application and carry no AutomationId in any toolkit (#9), so #6 left
    them out of the interactive set and so does RQ1.
    """
    frame: set[str] = set()
    for node in elements:  # pre-order, so a parent is always seen first
        element = node.get("element") or {}
        if element.get("controlType") == "TitleBar" or node.get("parentId") in frame:
            frame.add(str(node["id"]))
    return frame


def propose(
    descriptor: Element, window: Sequence[Element]
) -> tuple[dict[str, Any], int]:
    """The primary property set the Spy would suggest, and how many elements it matches.

    The rule is ``suggestUses`` in ``client/src/shared/repository.ts``: walk
    :data:`PROPOSAL_FIELDS` in order and keep a property when it is the first usable one, or
    while the set still matches more than one element and this property narrows it. A generated
    AutomationId is skipped -- it survives no release (#6 finding 4).
    """
    primary: dict[str, Any] = {}
    count = len(window)
    for name in PROPOSAL_FIELDS:
        value = getattr(descriptor, name, None)
        if is_blank(value):
            continue
        if name == "automation_id" and is_generated_id(value):
            continue
        candidate = {**primary, JSON_NAMES[name]: value}
        narrowed = sum(1 for other in window if matches(other, candidate))
        if not primary or (count > 1 and narrowed < count):
            primary = candidate
            count = narrowed
    return primary, count


def measure_screen(
    document: Mapping[str, Any], *, app: str, screen: str, path: Path
) -> Screen:
    """Measure every control of one snapshot document."""
    elements = list(document.get("elements") or [])
    descriptors = [Element.from_json(node.get("element") or {}) for node in elements]
    frame = frame_ids(elements)
    result = Screen(app=app, screen=screen, path=path, document=document)
    snapshot_id = str(document.get("snapshotId") or "")
    for node, descriptor in zip(elements, descriptors):
        element_id = str(node["id"])
        if element_id in frame or descriptor.control_type not in INTERACTIVE_TYPES:
            continue
        primary, count = propose(descriptor, descriptors)
        result.controls.append(
            Control(
                app=app,
                screen=screen,
                snapshot_id=snapshot_id,
                element_id=element_id,
                control_type=str(descriptor.control_type),
                descriptor=descriptor,
                primary=primary,
                match_count=count,
            )
        )
    return result


# ------------------------------------------------------------------------------- labels


def load_labels(path: Path) -> tuple[dict[str, tuple[str, str]], list[str]]:
    """Read a label file: ``{elementId: (label, note)}`` and the ``missing`` controls.

    The ground truth RQ1 needs is the **denominator**, and the denominator cannot come from
    AYNA's own walk: a control the walk never produced would simply not be counted, which
    would flatter the rate. So a person enumerates the screen's controls (procedure in
    ``labelling.md``) and records one row per element -- ``control`` for one a tester would
    target, ``ignore`` for an element that is not a control -- plus a ``missing`` row, with no
    element id, for every control they see that no row carries.
    """
    labels: dict[str, tuple[str, str]] = {}
    missing: list[str] = []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for line, row in enumerate(csv.DictReader(handle), start=2):
            label = (row.get("label") or "").strip()
            note = (row.get("note") or "").strip()
            element_id = (row.get("elementId") or "").strip()
            if not label:
                continue
            if label not in LABELS:
                raise ValueError(
                    f"{path}:{line}: label {label!r} is not one of {', '.join(LABELS)}"
                )
            if label == LABEL_MISSING:
                if not note:
                    raise ValueError(
                        f"{path}:{line}: a 'missing' row must name the control in `note`"
                    )
                missing.append(note)
                continue
            if not element_id:
                raise ValueError(f"{path}:{line}: label {label!r} needs an elementId")
            labels[element_id] = (label, note)
    return labels, missing


def apply_labels(screen: Screen, labels_file: Path) -> Screen:
    """`screen` with its labels applied. Raises when a label names an element it has not."""
    labels, missing = load_labels(labels_file)
    known = {control.element_id for control in screen.controls}
    unknown = sorted(set(labels) - known)
    if unknown:
        raise ValueError(
            f"{labels_file}: no measured control has element id {', '.join(unknown)}. "
            "A label file belongs to one snapshot and is void if the snapshot is recaptured."
        )
    screen.controls = [
        replace(
            control,
            label=labels.get(control.element_id, ("", ""))[0],
            note=labels.get(control.element_id, ("", ""))[1],
        )
        for control in screen.controls
    ]
    screen.missing = missing
    screen.labelled = True
    return screen


def counted(screen: Screen) -> list[Control]:
    """The controls that count towards the rate: all of them, or the labelled ones."""
    if not screen.labelled:
        return screen.controls
    return [control for control in screen.controls if control.label == LABEL_CONTROL]


# -------------------------------------------------------------------------------- rates


def by_column(name: str) -> str:
    """Column counting how often a property appears in a proposed set: `byAutomationId`."""
    camel = JSON_NAMES[name]
    return f"by{camel[0].upper()}{camel[1:]}"


#: Columns of the per-control-type CSV. `missing` is only ever non-zero on the TOTAL row of a
#: labelled app, since a control AYNA never saw has no control type to put it under. The
#: property columns are prefixed `by` so that `byControlType` cannot collide with the
#: `controlType` the row is about.
RATE_COLUMNS = (
    "controlType",
    "controls",
    "recognised",
    "recognisedShare",
    "ambiguous",
    "noProperty",
    "missing",
    *(by_column(name) for name in PROPOSAL_FIELDS),
    "propertiesPerControl",
)

TOTAL = "TOTAL"


def share(part: int, whole: int) -> str:
    """A percentage with one decimal, or an empty cell when there is nothing to divide."""
    return f"{100 * part / whole:.1f}" if whole else ""


def rate_rows(controls: Sequence[Control], missing: int = 0) -> list[dict[str, Any]]:
    """One row per control type, commonest first, then a TOTAL row.

    The property columns count how often each property appears in a proposed set, which is what
    says *why* a toolkit scores as it does: 90 % by AutomationId reads very differently from
    90 % by Name plus a parent path.
    """
    types = sorted({control.control_type for control in controls})
    rows = [
        _rate_row(control_type, [c for c in controls if c.control_type == control_type])
        for control_type in types
    ]
    rows.sort(key=lambda row: (-row["controls"], row["controlType"]))
    return [*rows, _rate_row(TOTAL, controls, missing=missing)]


def _rate_row(
    label: str, controls: Sequence[Control], missing: int = 0
) -> dict[str, Any]:
    denominator = len(controls) + missing
    recognised = sum(1 for control in controls if control.recognised)
    row: dict[str, Any] = {
        "controlType": label,
        "controls": denominator,
        "recognised": recognised,
        "recognisedShare": share(recognised, denominator),
        "ambiguous": sum(1 for c in controls if c.reason == AMBIGUOUS),
        "noProperty": sum(1 for c in controls if c.reason == NO_PROPERTY),
        "missing": missing,
    }
    for name in PROPOSAL_FIELDS:
        key = JSON_NAMES[name]
        row[by_column(name)] = sum(1 for control in controls if key in control.primary)
    sizes = [len(control.primary) for control in controls if control.primary]
    row["propertiesPerControl"] = f"{sum(sizes) / len(sizes):.2f}" if sizes else ""
    return row


CONTROL_COLUMNS = (
    "app",
    "screen",
    "windowTitle",
    "snapshotId",
    "elementId",
    "controlType",
    "automationId",
    "name",
    "nearestLabel",
    "nearestLabelSource",
    "className",
    "parentPath",
    "siblingIndex",
    "enabled",
    "offscreen",
    "primaryProperties",
    "primary",
    "matchCount",
    "recognised",
    "reason",
    "label",
    "note",
)


def control_rows(screens: Sequence[Screen]) -> list[dict[str, Any]]:
    """One row per control: the evidence behind every rate, and the sheet a person labels."""
    rows: list[dict[str, Any]] = []
    for screen in screens:
        for control in screen.controls:
            element = control.descriptor
            rows.append(
                {
                    "app": control.app,
                    "screen": control.screen,
                    "windowTitle": screen.window_title,
                    "snapshotId": control.snapshot_id,
                    "elementId": control.element_id,
                    "controlType": control.control_type,
                    "automationId": element.automation_id or "",
                    "name": element.name or "",
                    "nearestLabel": element.nearest_label or "",
                    "nearestLabelSource": element.nearest_label_source or "",
                    "className": element.class_name or "",
                    "parentPath": element.parent_path or "",
                    "siblingIndex": (
                        "" if element.sibling_index is None else element.sibling_index
                    ),
                    "enabled": _flag(element.enabled),
                    "offscreen": _flag(element.offscreen),
                    "primaryProperties": " ".join(control.primary),
                    "primary": json.dumps(control.primary, ensure_ascii=False),
                    "matchCount": control.match_count,
                    "recognised": "yes" if control.recognised else "no",
                    "reason": control.reason,
                    "label": control.label,
                    "note": control.note,
                }
            )
    return rows


def _flag(value: bool | None) -> str:
    return "" if value is None else ("yes" if value else "no")


def write_csv(
    path: Path, columns: Sequence[str], rows: Iterable[Mapping[str, Any]]
) -> Path:
    """Write a CSV that Excel on a Turkish Windows opens without a wizard.

    UTF-8 **with a BOM** and CRLF: without the BOM Excel reads `Şifre` as `Åifre`, and the team
    reads these files in Excel long before they reach the report.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), lineterminator="\r\n")
        writer.writeheader()
        writer.writerows(rows)
    return path


# --------------------------------------------------------------------------------- apps


def load_apps() -> dict[str, dict[str, Any]]:
    """The RQ1 app registry (`apps.json`), by id, in the file's order."""
    data = json.loads(APPS_FILE.read_text(encoding="utf-8"))
    return {entry["id"]: entry for entry in data}


def pilot_ids(apps: Mapping[str, Mapping[str, Any]]) -> list[str]:
    """The apps measured by default: the D1 pilots, in the ADR's order."""
    return [app_id for app_id, entry in apps.items() if entry.get("pilot")]


# ------------------------------------------------------------------------------ reading


def read_screens(app_id: str, *, labels: bool = False) -> list[Screen]:
    """Measure every snapshot of one app, by screen name."""
    folder = SNAPSHOTS / app_id
    screens: list[Screen] = []
    for path in sorted(folder.glob("*.json")) if folder.is_dir() else []:
        document = json.loads(path.read_text(encoding="utf-8"))
        screen = measure_screen(document, app=app_id, screen=path.stem, path=path)
        label_file = LABEL_DIR / f"{app_id}-{path.stem}.csv"
        if labels and label_file.is_file():
            screen = apply_labels(screen, label_file)
        screens.append(screen)
    return screens


# ------------------------------------------------------------------------------- report


def summary_table(app_id: str, screens: Sequence[Screen]) -> list[str]:
    """The lines printed for one app: a markdown table ready to paste into an issue."""
    rows = rate_rows(
        [control for screen in screens for control in counted(screen)],
        missing=sum(len(screen.missing) for screen in screens),
    )
    labelled = [screen for screen in screens if screen.labelled]
    total = rows[-1]
    denominator = (
        f"ground truth, {len(labelled)}/{len(screens)} screen(s) labelled"
        if labelled
        else "no labels: the denominator is what the walk found"
    )
    heading = (
        f"### {app_id} — {len(screens)} screen(s), {total['controls']} controls, "
        f"{total['recognisedShare']}% recognised ({denominator})"
    )
    return [
        heading,
        "",
        "| Control type | Controls | Recognised | Share | Ambiguous | No property |",
        "|---|---|---|---|---|---|",
        *(
            f"| {row['controlType']} | {row['controls']} | {row['recognised']} "
            f"| {row['recognisedShare']}% | {row['ambiguous']} | {row['noProperty']} |"
            for row in rows
        ),
    ]


# --------------------------------------------------------------------------- subcommands


def run_measure(args: argparse.Namespace) -> int:
    apps = load_apps()
    chosen = args.apps or pilot_ids(apps)
    unknown = [app_id for app_id in chosen if app_id not in apps]
    if unknown:
        print(f"unknown app(s): {', '.join(unknown)}", file=sys.stderr)
        return 2
    stamp = datetime.now(UTC).strftime("%Y-%m-%d")
    written: list[Path] = []
    empty: list[str] = []
    for app_id in chosen:
        screens = read_screens(app_id, labels=args.labels)
        if not screens:
            empty.append(app_id)
            continue
        controls = [control for screen in screens for control in counted(screen)]
        missing = sum(len(screen.missing) for screen in screens)
        written.append(
            write_csv(
                RESULTS / f"{app_id}-{stamp}-rates.csv",
                RATE_COLUMNS,
                rate_rows(controls, missing=missing),
            )
        )
        written.append(
            write_csv(
                RESULTS / f"{app_id}-{stamp}-controls.csv",
                CONTROL_COLUMNS,
                control_rows(screens),
            )
        )
        print("\n".join(summary_table(app_id, screens)))
        print()
    for app_id in empty:
        print(
            f"{app_id}: no snapshot in {SNAPSHOTS / app_id}. Capture one first: "
            f"measure.py capture {app_id} --screen <name>",
            file=sys.stderr,
        )
    for path in written:
        print(f"wrote {path.relative_to(REPO)}")
    return 1 if empty and not written else 0


def run_capture(args: argparse.Namespace) -> int:
    """Snapshot the app's open windows. Windows only: this is the half that needs UIA."""
    apps = load_apps()
    if args.app not in apps:
        print(f"unknown app: {args.app}", file=sys.stderr)
        return 2
    entry = apps[args.app]
    try:
        from ayna_agent.recognition.uia import UiaDesktop
    # Broad on purpose: off Windows this is an ImportError, but `ctypes.wintypes` raises
    # ValueError instead on some platforms, and either way the answer is the same message.
    except Exception as exc:  # noqa: BLE001  # pragma: no cover - Windows only
        print(f"cannot load the UIA backend: {exc}", file=sys.stderr)
        return 2

    desktop = UiaDesktop()
    desktop.setup()
    try:
        wanted = str(entry["process"]).lower()
        windows = [
            window
            for window in desktop.list_windows()
            if str(window.get("processName") or "").lower() == wanted
        ]
        if not windows:
            print(
                f"no open window of {entry['process']}. Start {entry['app']} and open the "
                "screen first; apps.json lists the screens RQ1 measures.",
                file=sys.stderr,
            )
            return 1
        folder = SNAPSHOTS / args.app
        folder.mkdir(parents=True, exist_ok=True)
        for index, window in enumerate(windows):
            name = args.screen if len(windows) == 1 else f"{args.screen}-{index + 1}"
            path = folder / f"{name}.json"
            if path.exists() and not args.force:
                print(
                    f"{path.relative_to(REPO)} exists. A snapshot a result used is frozen "
                    "(eval/AGENTS.md); pass --force only if nothing has used it.",
                    file=sys.stderr,
                )
                return 1
            document = desktop.snapshot(int(window["handle"]), args.timeout_ms)
            path.write_text(
                json.dumps(document, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            capture = document.get("capture") or {}
            print(
                f"wrote {path.relative_to(REPO)}: {capture.get('elementCount')} elements "
                f"in {capture.get('durationMs')} ms, {capture.get('readErrors')} read "
                f"errors — {window.get('title')!r}"
            )
    finally:
        desktop.close()
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    # The summary is a markdown table meant to be pasted into an issue, and it carries Turkish
    # control names. A Windows console is cp1254 here, which would turn them into mojibake
    # whether they are read or redirected to a file.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="RQ1 recognition measurement (#29).")
    sub = parser.add_subparsers(dest="command", required=True)

    capture = sub.add_parser(
        "capture", help="snapshot a pilot app's open windows (Windows only)"
    )
    capture.add_argument("app", help="an id from apps.json")
    capture.add_argument(
        "--screen", default="main", help="file name for this screen (default: main)"
    )
    capture.add_argument("--timeout-ms", type=int, default=None, help="walk budget")
    capture.add_argument("--force", action="store_true", help="overwrite a snapshot")
    capture.set_defaults(run=run_capture)

    measure = sub.add_parser("measure", help="measure the snapshots and write the CSVs")
    measure.add_argument("apps", nargs="*", help="app ids (default: the D1 pilots)")
    measure.add_argument(
        "--labels",
        action="store_true",
        help="use the ground-truth labels in eval/rq1/labels/ as the denominator",
    )
    measure.set_defaults(run=run_measure)

    args = parser.parse_args(argv)
    return int(args.run(args))


if __name__ == "__main__":
    raise SystemExit(main())
