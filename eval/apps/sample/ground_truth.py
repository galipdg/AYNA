"""Generate the old -> new ground truth for #46's change versions, never type it by hand.

For every control one of `variants.py`'s versions touches, the healing measurement (#73, #86)
needs to know what that control *became*: a different name, a different place, a different
class, a longer id, or nothing at all. That mapping is this file's output,
`ground_truth.json`, and it is **generated**:

1. the screen is built once as v1 and every widget on it is read,
2. it is built a second time and `variant_patch.apply` changes it, reporting every widget it
   touched, keyed by the control's v1 `objectName`,
3. each reported widget is read the same way, and the pair is one row of the mapping.

So the mapping cannot drift from the app: the same declaration produces both, and a change
that drags a form label along with it lands in the mapping without anyone declaring the label
(such a row says `"declared": false`).

    .venv/Scripts/python.exe eval/apps/sample/ground_truth.py            # summary
    .venv/Scripts/python.exe eval/apps/sample/ground_truth.py --write    # regenerate the file
    .venv/Scripts/python.exe eval/apps/sample/ground_truth.py --check    # fail if it is stale

It runs on Qt's offscreen platform, which is chosen in Qt's own argv and **never** with
`QT_QPA_PLATFORM` (that variable is inherited by the app processes the UIA tests start, and
they would come up with no window at all -- `memory-bank/learnings.md` 2026-11-12). So macOS
generates the same file as Windows, and `tests/test_variants.py` checks it everywhere.

**What is certain here and what is predicted.** The *mapping* is certain: it is what the patch
reports it did. The `name`, `controlType` and `automationId` of each side are derived from the
three Qt -> UIA rules measured on this app (`README.md`, "What Qt exposes to UI Automation"):
`objectName` is the AutomationId as a dotted path over the object chain, `accessibleName`
replaces the Name, the Python class name is the ClassName. **Every row is then checked against
a real provider** by `tests/test_variant_uia.py`, which is not a formality: on its first run
(2026-11-15) it corrected the biggest assumption in here -- a control whose `objectName` was
cleared does not lose its AutomationId, it gets its class name instead (`automation_id` below).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from PySide6.QtWidgets import (
    QApplication,
    QBoxLayout,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)

import texts
import variant_patch
from variants import BASELINE, VARIANTS

#: Where the generated mapping lives. Read by the measurement, written only by this script.
GROUND_TRUTH_PATH = Path(__file__).resolve().parent / "ground_truth.json"

#: Qt's AutomationId is a dotted path over the whole object chain, and the chain's root is the
#: `QApplication` itself -- measured, see the README's id tables.
UIA_ROOT = "QApplication"

#: Qt class -> UIA ControlType, from the README's measured tables. A class that is not in
#: here has never been measured on this app, so the mapping says `null` rather than guessing;
#: that is the case for the `QGroupBox` containers v2d creates.
CONTROL_TYPES = {
    "QLabel": "Text",
    "QLineEdit": "Edit",
    "QPushButton": "Button",
    "QCheckBox": "CheckBox",
    "QComboBox": "ComboBox",
    "QSpinBox": "Spinner",
    "QPlainTextEdit": "Edit",
    "QTableWidget": "Table",
}

#: Classes whose UIA Name is their own visible text when no `accessibleName` is set.
_TEXT_IS_NAME = (QLabel, QPushButton, QCheckBox, QGroupBox)


def offscreen_app() -> QApplication:
    """A `QApplication` with no display, for building the screens twice."""
    return QApplication.instance() or QApplication(
        ["ground_truth", "-platform", "offscreen"]
    )


def build_screen(screen: str, variant: str = BASELINE) -> QWidget:
    """One screen, optionally changed. `variant_patch` is driven by hand, not by the hook."""
    from sample_app import open_screen

    variant_patch.set_active(BASELINE)
    window = open_screen(screen, delay_ms=0)
    if variant != BASELINE:
        variant_patch.apply(window, variant)
    return window


def automation_id(widget: QWidget) -> str:
    """The AutomationId Qt builds for `widget`: `QApplication.login.loginButton`.

    **A control with no `objectName` still has an id**: Qt puts its class name in the path
    instead, so clearing the name of `login.loginButton` gives
    `QApplication.login.QPushButton`. Measured on 2026-11-15 for `QPushButton`, `QLineEdit`
    and `QTableWidget` on all three screens (`tests/test_variant_uia.py`), and it is the
    finding v2e is worth building: removing an id does not leave a control without one, it
    leaves it with an id that is **not the logical name and not unique** -- two buttons that
    both lose their name would share `…QPushButton`, and #33's "an AutomationId on every
    control" still passes.
    """
    chain: list[str] = []
    node: QWidget | None = widget
    while node is not None:
        chain.append(node.objectName() or type(node).__name__)
        node = node.parentWidget()
    return ".".join([UIA_ROOT, *reversed(chain)])


def uia_name(widget: QWidget) -> str:
    """The Name UI Automation reports, by this app's three measured rules.

    `accessibleName` replaces the Name wherever it is set; otherwise a label, a button, a
    check box or a group box shows its own text, a combo box its current item, and an input
    nothing at all -- which is what makes a retyped label (v2c) so hard to find again: its
    string moves out of the Name and into the Value.
    """
    accessible = widget.accessibleName()
    if accessible:
        return accessible
    if isinstance(widget, QComboBox):
        return widget.currentText()
    if isinstance(widget, _TEXT_IS_NAME):
        return widget.title() if isinstance(widget, QGroupBox) else widget.text()
    return ""


def place_of(widget: QWidget) -> tuple[int | None, list[int] | None]:
    """Where the control sits in its own layout: a row/index, or a grid cell.

    Deliberately *not* the UIA sibling index, which only a real provider can report: this is
    the layout position, which is what a move changes and what can be read without Windows.
    """
    try:
        layout = variant_patch.owning_layout(widget)
    except LookupError:
        return None, None
    if isinstance(layout, QGridLayout):
        index = layout.indexOf(widget)
        row, column, _rows, _columns = layout.getItemPosition(index)
        return None, [row, column]
    if isinstance(layout, QFormLayout):
        row, _role = layout.getWidgetPosition(widget)
        return row, None
    if isinstance(layout, QBoxLayout):
        return layout.indexOf(widget), None
    return None, None


def uia_value(widget: QWidget) -> str:
    """The string a control holds rather than shows: its ValuePattern value.

    It is in the mapping because a retype (v2c) is exactly the case where a string **moves**
    from the Name to the value, and a healer that only ever reads Names cannot see where it
    went.
    """
    if isinstance(widget, QComboBox):
        return widget.currentText()
    if isinstance(widget, QLineEdit):
        return widget.text()
    return ""


def describe(widget: QWidget) -> dict:
    """One side of a mapping: what a locator has to work with."""
    index, cell = place_of(widget)
    parent = widget.parentWidget()
    class_name = type(widget).__name__
    return {
        "automationId": automation_id(widget),
        "name": uia_name(widget),
        "value": uia_value(widget),
        "className": class_name,
        "controlType": CONTROL_TYPES.get(class_name),
        "parentPath": automation_id(parent) if parent is not None else "",
        "layoutIndex": index,
        "cell": cell,
    }


def index_screen(window: QWidget) -> dict[str, dict]:
    """Every control of a screen the app itself named, by `objectName`.

    Qt's own internals (`qt_scrollarea_viewport`, `qt_spinbox_lineedit`) are left out: they
    are in the UIA tree and in the README's tables, but no scenario ever points at one, and a
    change that moves their parent would otherwise fill the mapping with Qt's plumbing.
    """
    described: dict[str, dict] = {}
    for widget in window.findChildren(QWidget):
        name = widget.objectName()
        if name and not name.startswith("qt_") and name not in described:
            described[name] = describe(widget)
    return described


def mappings_for(variant: str) -> list[dict]:
    """The old -> new rows of one version, screen by screen, in declaration order."""
    declared = {
        (change.screen, change.target): change for change in VARIANTS[variant].changes
    }
    rows: list[dict] = []
    for screen in VARIANTS[variant].screens():
        # Two copies of the screen: one stays v1 and is the `old` side, the other is changed
        # here rather than in `build_screen`, because the patch's **report** is what the
        # mapping is built from. Both windows are kept in a local until the rows are read:
        # a window that goes out of scope takes its C++ children with it, and the report
        # holds nothing but those children.
        baseline_window = build_screen(screen)
        before = index_screen(baseline_window)
        changed_window = build_screen(screen)
        report = variant_patch.apply(changed_window, variant)
        for target, widget in report.items():
            change = declared.get((screen, target))
            rows.append(
                {
                    "screen": screen,
                    "control": target,
                    "kind": (
                        change.kind
                        if change is not None
                        else _kind_of(variant, screen, target)
                    ),
                    "declared": change is not None,
                    "note": change.note if change is not None else "",
                    "old": before.get(target),
                    "new": describe(widget) if widget is not None else None,
                }
            )
        rows.extend(_shifted_rows(screen, before, index_screen(changed_window), report))
        del baseline_window, changed_window
    return rows


def _shifted_rows(
    screen: str,
    before: dict[str, dict],
    after: dict[str, dict],
    report: dict[str, object],
) -> list[dict]:
    """Controls the patch never touched whose description changed anyway.

    A form row that moves pushes the rows below it down, and a container that appears takes a
    place in the window's column -- so a control nobody declared can still end up somewhere
    else, which is exactly what an index-based locator trips over. Those rows are in the
    mapping with `"kind": "shifted"` so that "a mapping for every changed control" means every
    control whose description changed, and not only every control the change set names.
    """
    shifted: list[dict] = []
    for name in sorted(before):
        if name in report or name not in after or after[name] == before[name]:
            continue
        shifted.append(
            {
                "screen": screen,
                "control": name,
                "kind": "shifted",
                "declared": False,
                "note": "not changed itself; moved because another control's change did",
                "old": before[name],
                "new": after[name],
            }
        )
    return shifted


def _kind_of(variant: str, screen: str, target: str) -> str:
    """The kind of the change that touched an undeclared control (a form row's label).

    A label only ever moves because its field did, so the kind is the one change on that
    screen whose own target shares the label's row -- in practice there is exactly one kind
    per screen that drags labels (`move` or `reparent`), and that is what is reported.
    """
    kinds = {
        change.kind
        for change in VARIANTS[variant].changes
        if change.screen == screen and change.kind in ("move", "reparent", "removed")
    }
    return min(kinds) if len(kinds) == 1 else "+".join(sorted(kinds))


def generate() -> dict:
    """The whole file: every version, every mapping."""
    offscreen_app()
    return {
        "generatedBy": "eval/apps/sample/ground_truth.py",
        "app": texts.APP_NAME,
        "appVersion": texts.VERSION,
        "uiaRoot": UIA_ROOT,
        "issue": 46,
        "variants": {
            variant_id: {
                "kind": variant.kind,
                "summary": variant.summary,
                "screens": list(variant.screens()),
                "mappings": mappings_for(variant_id),
            }
            for variant_id, variant in VARIANTS.items()
        },
    }


def as_text(document: dict) -> str:
    return json.dumps(document, indent=2, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate #46's old -> new ground truth from the change versions."
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="write ground_truth.json and say what changed",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit non-zero if ground_truth.json is not what this script would write",
    )
    args = parser.parse_args(argv)

    # Every name on these screens is Turkish, and a redirected stdout on a Turkish Windows
    # console is cp1254 (the same reason `uia_check.py` does this).
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    document = generate()
    text = as_text(document)

    if args.check:
        current = (
            GROUND_TRUTH_PATH.read_text(encoding="utf-8")
            if GROUND_TRUTH_PATH.exists()
            else ""
        )
        if current == text:
            print(f"OK   {GROUND_TRUTH_PATH.name} is up to date")
            return 0
        print(
            f"STALE {GROUND_TRUTH_PATH.name}: regenerate it with --write",
            file=sys.stderr,
        )
        return 1

    if args.write:
        GROUND_TRUTH_PATH.write_text(text, encoding="utf-8")
        print(f"wrote {GROUND_TRUTH_PATH}")

    for variant_id, variant in document["variants"].items():
        declared = sum(1 for row in variant["mappings"] if row["declared"])
        print(
            f"{variant_id}  {variant['kind']:<10} "
            f"{len(variant['mappings']):>2} controls "
            f"({declared} declared, {len(variant['mappings']) - declared} dragged along) "
            f"on {', '.join(variant['screens'])}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
