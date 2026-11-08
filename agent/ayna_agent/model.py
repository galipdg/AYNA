"""The element descriptor: what AYNA stores about one UI element (#11).

This module is deliberately free of UI Automation. It takes **raw nodes** — plain mappings
of the properties a reader has already pulled from UIA, plus the tree links — and turns them
into descriptors. The UIA reading lives in the recognition backend (#12); keeping the two
apart is what lets the rules below be tested on any OS and replayed over the dumps from #6.

Three properties are *computed*, not read, and their rules are normative, because healing
recomputes equivalents from a stored snapshot (#43) and a property that is derived by a
different rule at capture time and at healing time looks like a property that changed:

- ``parent_path`` - programmatic control types of the ancestors, root first, joined by ``/``.
- ``sibling_index`` - zero-based position among the parent's children in the raw view.
- ``nearest_label`` - the text that names the element, with ``nearest_label_source``
  recording *which* rule produced it (see :func:`nearest_label`).

The JSON form is camelCase (`schemas/element.schema.json`, `urn:ayna:schema:element`) and is
a superset of the healing proposal's ``scoredElement``; the Python form is snake_case, as
agreed for every contract boundary.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, fields
from typing import Any

#: Schema version this module reads and writes.
VERSION = "0.1"

#: snake_case attribute -> camelCase key in JSON.
JSON_NAMES: dict[str, str] = {
    "automation_id": "automationId",
    "name": "name",
    "control_type": "controlType",
    "class_name": "className",
    "framework_id": "frameworkId",
    "bounds": "bounds",
    "dpi": "dpi",
    "parent_path": "parentPath",
    "sibling_index": "siblingIndex",
    "nearest_label": "nearestLabel",
    "nearest_label_source": "nearestLabelSource",
    "window_title": "windowTitle",
    "enabled": "enabled",
    "offscreen": "offscreen",
    "help_text": "helpText",
    "access_key": "accessKey",
    "native_window_handle": "nativeWindowHandle",
}

#: Properties a repository object may use as its primary identification, best first (#10 [5]:
#: ROBULA+ shows that a written-down priority beats both "always the id" and "always the path").
#: `automation_id` leads only when it is neither generated nor shared, which #6 measured to be
#: false for 96 % of Notepad++'s ids and for 90 % of KeePassXC's.
PRIMARY_PRIORITY: tuple[str, ...] = (
    "automation_id",
    "name",
    "nearest_label",
    "class_name",
    "parent_path",
)

#: Properties that must never identify an element, with the reason. Stored anyway: they are
#: useful for the win32 fallback (#23), for diagnostics and for reading a dump, and capture is
#: expensive to repeat while a scoring change is cheap.
NEVER_MATCH: dict[str, str] = {
    "bounds": "absolute geometry; compared only as DIP location/area/shape by the scorer",
    "dpi": "a property of the display, not of the element",
    "native_window_handle": "session-scoped: a new handle every run",
    "framework_id": "the same for every element of an application",
    "offscreen": "state, not identity: changes with scrolling and tab selection",
    "enabled": "state, not identity: changes with the application's own logic",
    "nearest_label_source": "says how nearest_label was found, not what the element is",
}

#: An AutomationId the framework generated rather than a developer chose: a Win32 control id
#: ("1001"), a GUID, or Qt's class-name fallback for an unnamed widget ("…QPushButton2").
#: Same rule as `eval/spikes/uia_tree_dump.py`, plus the Qt case #6 finding 3 measured.
_GENERATED_ID = re.compile(
    r"^(?:\d+|[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12})$"
)
_QT_FALLBACK_LEAF = re.compile(r"^Q[A-Z]\w*?\d*$")

#: Control types whose text can name another control. UIA reports a WinForms label, a WPF
#: TextBlock and a Qt QLabel as Text; Win32 dialogs sometimes use a Group box caption.
LABEL_TYPES: frozenset[str] = frozenset({"Text", "Group"})

#: How far a label may sit from what it labels, in device-independent pixels. Measured over
#: the four #6 dumps and the trial app: every label that UIA itself confirms through
#: ``LabeledBy`` is 13 DIP away (7 of 7 in KeePassXC) and the trial app's are 6 and 10 DIP,
#: while the nearest *wrong* pairing in those five applications is 261 DIP. 48 DIP - three
#: lines of 16 DIP text - sits an order of magnitude below the first error.
MAX_LABEL_GAP_DIP = 48


def _blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


@dataclass(frozen=True, slots=True)
class Element:
    """One UI element. Every property is optional: no framework fills them all in."""

    automation_id: str | None = None
    name: str | None = None
    control_type: str | None = None
    class_name: str | None = None
    framework_id: str | None = None
    bounds: tuple[int, int, int, int] | None = None
    dpi: int | None = None
    parent_path: str | None = None
    sibling_index: int | None = None
    nearest_label: str | None = None
    nearest_label_source: str | None = None
    window_title: str | None = None
    enabled: bool | None = None
    offscreen: bool | None = None
    help_text: str | None = None
    access_key: str | None = None
    native_window_handle: int | None = None

    def to_json(self) -> dict[str, Any]:
        """camelCase mapping for the schema. Absent and blank values are left out."""
        out: dict[str, Any] = {}
        for field in fields(self):
            value = getattr(self, field.name)
            if _blank(value):
                continue
            key = JSON_NAMES[field.name]
            out[key] = list(value) if field.name == "bounds" else value
        return out

    def to_document(self) -> dict[str, Any]:
        """The whole document the schema validates: ``{version, element}``."""
        return {"version": VERSION, "element": self.to_json()}

    @classmethod
    def from_json(cls, data: Mapping[str, Any]) -> Element:
        """Read a camelCase mapping. Unknown keys are refused, as the schema refuses them."""
        reverse = {camel: snake for snake, camel in JSON_NAMES.items()}
        unknown = sorted(set(data) - set(reverse))
        if unknown:
            raise ValueError(f"unknown element properties: {', '.join(unknown)}")
        values: dict[str, Any] = {}
        for camel, value in data.items():
            if _blank(value):
                continue
            snake = reverse[camel]
            values[snake] = tuple(value) if snake == "bounds" else value
        return cls(**values)

    @classmethod
    def from_document(cls, document: Mapping[str, Any]) -> Element:
        version = document.get("version")
        if version != VERSION:
            raise ValueError(
                f"element document version {version!r}, expected {VERSION!r}"
            )
        return cls.from_json(document.get("element") or {})

    def primary_property(self) -> str | None:
        """The property a repository object should identify this element by, or None.

        Follows :data:`PRIMARY_PRIORITY` and skips an ``automation_id`` the framework
        generated, because a generated id survives no release (#6 finding 4).
        """
        for prop in PRIMARY_PRIORITY:
            value = getattr(self, prop)
            if _blank(value):
                continue
            if prop == "automation_id" and is_generated_id(value):
                continue
            return prop
        return None


def is_generated_id(automation_id: str | None) -> bool:
    """True when the AutomationId looks machine-made rather than developer-chosen.

    Whole-string digits and GUIDs are generated anywhere. In a dotted Qt id only the leaf
    matters: ``QApplication.loginWindow.usernameInput`` is chosen, while
    ``QApplication.mainWindow.QPushButton2`` is Qt falling back to the class name, which is
    exactly the case that produced KeePassXC's 10 % id uniqueness (#6 finding 3).
    """
    if _blank(automation_id):
        return False
    text = str(automation_id).strip()
    leaf = text.rsplit(".", 1)[-1]
    return bool(
        _GENERATED_ID.match(text)
        or _GENERATED_ID.match(leaf)
        or _QT_FALLBACK_LEAF.match(leaf)
    )


def parent_path(ancestor_types: Iterable[str | None]) -> str | None:
    """``Window/Pane/Group`` from the ancestors' control types, root first.

    The element's own type is not part of its path. An ancestor whose control type could not
    be read becomes ``?``, so the path keeps its depth and a missing value cannot silently
    turn two different depths into the same string.
    """
    types = ["?" if _blank(t) else str(t).strip() for t in ancestor_types]
    return "/".join(types) if types else None


def nearest_label(
    element: Mapping[str, Any],
    siblings: Sequence[Mapping[str, Any]],
    parent_siblings: Sequence[Mapping[str, Any]] = (),
) -> tuple[str | None, str | None]:
    """The text that names ``element``, and which rule found it.

    The rule, in order, and normative for #43:

    1. **labeledBy** - the UIA ``LabeledBy`` relation, when the target has text. The toolkit's
       own answer always wins; only Qt filled it in the #6 dumps (12 % of KeePassXC's
       interactive elements), but when it is there it is better than any guess.
    2. **geometric** - the nearest label-like sibling (:data:`LABEL_TYPES`) that sits **to the
       left** of the element, overlapping it vertically, at most :data:`MAX_LABEL_GAP_DIP`
       away. The smaller gap wins; the lower ``siblingIndex`` breaks a tie, so the result is
       stable.
    3. **parentRow** - the same rule one level up, among the parent's siblings. Qt and WinForms
       wrap each form row in a panel, which puts the label outside the element's own parent.
       **One level only**: climbing further reaches the window and labels everything with the
       first text on the form.

    Only labels to the *left* count, which is a measurement rather than a preference. Across
    the four #6 dumps and the trial app, every label confirmed by ``LabeledBy`` is to the left
    (7 of 7), and so is every label a person would name for the WinForms, WPF and Win32 forms
    in those dumps. Accepting a label *above* was tried and produced only errors: in the trial
    app it gives the "Remember me" check box and the "Login" button the password field's label,
    6 DIP above them, and in KeePass 2 it labels a combo box with "20 ch.". A later version can
    add an "above" rule for web-style layouts if it also requires the two left edges to line up.

    Returns ``(None, None)`` when no rule applies. An element without bounds can only be
    labelled by rule 1, and gaps are measured in device-independent pixels, so the rule holds
    at every display scaling (``dpi`` on the element; 96 when it is missing).
    """
    labeled_by = element.get("labeled_by")
    if not _blank(labeled_by):
        return str(labeled_by).strip(), "labeledBy"

    own = _rect(element.get("bounds"))
    if own is None:
        return None, None
    dpi = element.get("dpi") or 96

    found = _closest_label(own, siblings, dpi)
    if found is not None:
        return found, "geometric"

    found = _closest_label(own, parent_siblings, dpi)
    if found is not None:
        return found, "parentRow"
    return None, None


def _rect(bounds: Any) -> tuple[int, int, int, int] | None:
    if bounds is None or len(tuple(bounds)) != 4:
        return None
    left, top, right, bottom = (int(v) for v in bounds)
    if right <= left or bottom <= top:
        return None
    return left, top, right, bottom


def _closest_label(
    own: tuple[int, int, int, int], candidates: Sequence[Mapping[str, Any]], dpi: int
) -> str | None:
    left, top, _right, bottom = own
    limit = MAX_LABEL_GAP_DIP * dpi / 96
    scored: list[tuple[float, int, str]] = []
    for index, candidate in enumerate(candidates):
        if candidate.get("control_type") not in LABEL_TYPES:
            continue
        text = candidate.get("name")
        if _blank(text):
            continue
        rect = _rect(candidate.get("bounds"))
        if rect is None:
            continue
        _c_left, c_top, c_right, c_bottom = rect
        if c_right > left or c_bottom <= top or c_top >= bottom:  # not on the same row
            continue
        gap = left - c_right
        if gap > limit:
            continue
        scored.append((gap, candidate.get("sibling_index", index), str(text).strip()))
    if not scored:
        return None
    scored.sort(key=lambda item: (item[0], item[1]))
    return scored[0][2]


def describe_tree(nodes: Sequence[Mapping[str, Any]]) -> list[Element]:
    """Descriptors for a whole window, from raw nodes in pre-order.

    A raw node is a mapping with the UIA properties under their snake_case names plus its
    position in the tree: ``id`` (its index in this list), ``parent`` (the parent's id or
    None) and optionally ``sibling_index``. The format of the #6 dumps is already this, which
    is what lets the rules be replayed over real applications.
    """
    by_id = {node.get("id", index): node for index, node in enumerate(nodes)}
    children: dict[Any, list[Mapping[str, Any]]] = {}
    for index, node in enumerate(nodes):
        children.setdefault(node.get("parent"), []).append(node)

    out: list[Element] = []
    for index, node in enumerate(nodes):
        parent_id = node.get("parent")
        siblings = [s for s in children.get(parent_id, []) if s is not node]
        parent = by_id.get(parent_id)
        parent_siblings = (
            [s for s in children.get(parent.get("parent"), []) if s is not parent]
            if parent is not None
            else []
        )
        label, source = nearest_label(node, siblings, parent_siblings)
        ancestors = []
        walker = parent
        while walker is not None:
            ancestors.append(walker.get("control_type"))
            walker = by_id.get(walker.get("parent"))
        bounds = _rect(node.get("bounds"))
        sibling_index = node.get("sibling_index")
        if sibling_index is None:
            sibling_index = next(
                (i for i, s in enumerate(children.get(parent_id, [])) if s is node),
                None,
            )
        out.append(
            Element(
                automation_id=_text(node.get("automation_id")),
                name=_text(node.get("name")),
                control_type=_text(node.get("control_type")),
                class_name=_text(node.get("class_name")),
                framework_id=_text(node.get("framework_id")),
                bounds=bounds,
                dpi=node.get("dpi"),
                parent_path=parent_path(reversed(ancestors)) if ancestors else None,
                sibling_index=sibling_index,
                nearest_label=label,
                nearest_label_source=source,
                window_title=_text(node.get("window_title")),
                enabled=node.get("enabled"),
                offscreen=node.get("offscreen"),
                help_text=_text(node.get("help_text")),
                access_key=_text(node.get("access_key")),
                native_window_handle=node.get("native_window_handle"),
            )
        )
    return out


def _text(value: Any) -> str | None:
    return None if _blank(value) else str(value).strip()
