"""The sample app's controlled UI-change versions, declared and not copied (#46).

Six versions of the #33 app, `v2a` … `v2f`: five of them make **one kind** of change and the
sixth combines them, which is what a real release looks like. They exist to measure
self-healing (#73, #86) and locator fragility (RQ4), so for every control they touch there has
to be a ground truth saying what it became -- `ground_truth.py` generates it from this file
and from what `variant_patch.py` reports it actually did.

**Why a change set and not six copies of the app.** The issue asks for `v2a..v2f` directories.
One declaration instead, because the ground truth and the app then cannot disagree: both come
from the tuples below. The second reason is `eval/AGENTS.md`'s "one module name per tree" --
six copies of `windows.py`, `model.py` and `texts.py` would each need a unique name, and a fix
in the app's rules would have to be made seven times (#199 measured what a shadowed module
costs). The third is that a reviewer can read a change set; nobody reads a diff of six trees.

This module stays **free of Qt**, so the spec is testable on any machine; `variant_patch.py`
holds the widget surgery and `ground_truth.py` the measurement.

Three rules the change sets obey, each learned from the app's own code:

* **A retype only ever becomes a class whose API covers what the app calls on the control.**
  `main.resultCountLabel` is only ever `setText`, so a read-only `QLineEdit` is safe; the
  detail form's `notesInput` is read with `toPlainText()` and is therefore never retyped.
* **A removal only hits a control the app never touches again** after wiring it up in
  `__init__` (`main.wizardButton`); `variant_patch.py` also unbinds the attribute, so a later
  call would raise in Python instead of crashing on a deleted C++ object.
* **The visible strings of a change live here, next to the change**, not in `texts.py`, so the
  old -> new pair is readable in one place. `texts.py` stays the list of every *v1* string.

What the versions deliberately do **not** do: touch the settings screen or the wizard. The
reference scenarios (#55) and the healing measurement cross `login`, `main` and `detail`, and
a change nothing plays over is a change nobody can score.
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: `sample_app.py --variant` for the unchanged app. Not a key of `VARIANTS`.
BASELINE = "v1"

#: The screens the versions change. The other two are untouched on purpose (see the docstring).
SCREENS = ("login", "main", "detail")

# --- change kinds --------------------------------------------------------------------------

#: The visible text or the accessible name changes; the AutomationId does not. Breaks a
#: locator that matched on `name` or on the nearest label.
RENAME = "rename"
#: The control keeps everything but its place among its siblings. Breaks index and geometry.
MOVE = "move"
#: The control becomes another class, so its UIA ControlType changes. A retyped label also
#: moves its string from the UIA **Name** to the **Value**, which no `name` match survives.
RETYPE = "retype"
#: The control moves into a new container. In Qt the AutomationId *is* the object chain, so a
#: re-parent is always an id change as well -- there is no way to re-parent and keep the id.
REPARENT = "reparent"
#: `objectName` is cleared, so the control has no AutomationId left and can only be found by
#: its name, its label or its place.
ID_REMOVED = "id-removed"
#: The control is gone. Its ground-truth counterpart is `null`: the one case where the right
#: answer is *not* to heal.
REMOVED = "removed"

KINDS = (RENAME, MOVE, RETYPE, REPARENT, ID_REMOVED, REMOVED)


@dataclass(frozen=True)
class Change:
    """One change to one control of one screen, named by its **v1** `objectName`."""

    screen: str
    target: str
    kind: str
    #: RENAME: the new visible text (`QLabel`, `QPushButton`, `QCheckBox`).
    text: str | None = None
    #: RENAME, or a retype into a combo box: the new `accessibleName`, which is what UIA
    #: reports as the Name.
    accessible: str | None = None
    #: RETYPE: the Qt class to become, from `variant_patch.RETYPE_CLASSES`.
    to_class: str | None = None
    #: RETYPE into a combo box: its items, in order.
    items: tuple[str, ...] = ()
    #: MOVE inside a `QHBoxLayout`/`QVBoxLayout`/`QFormLayout`: the new index. A form row
    #: carries its label with it, and `ground_truth.py` records the label as changed too.
    index: int | None = None
    #: MOVE inside a `QGridLayout`: the new (row, column).
    cell: tuple[int, int] | None = None
    #: REPARENT: `objectName` of the container to create and move the control into.
    group: str | None = None
    #: REPARENT: that container's visible title.
    group_title: str | None = None
    #: Why this control is in the set -- what a locator that relied on it would lose.
    note: str = ""


@dataclass(frozen=True)
class Variant:
    """One change version: an id, the kind it is about, and its changes."""

    id: str
    kind: str
    summary: str
    changes: tuple[Change, ...] = field(default_factory=tuple)

    def screens(self) -> tuple[str, ...]:
        """The screens this version changes, in `SCREENS` order."""
        touched = {change.screen for change in self.changes}
        return tuple(screen for screen in SCREENS if screen in touched)


V2A = Variant(
    id="v2a",
    kind=RENAME,
    summary="Captions and accessible names change; every AutomationId stays as it was.",
    changes=(
        Change(
            screen="login",
            target="loginButton",
            kind=RENAME,
            text="Oturum aç",
            note="SC-14 clicks this button; a locator matching its Name loses it.",
        ),
        Change(
            screen="login",
            target="userNameLabel",
            kind=RENAME,
            text="Kullanıcı kodu",
            note="The label an input is recognised by when it has no id of its own.",
        ),
        Change(
            screen="login",
            target="userNameInput",
            kind=RENAME,
            accessible="Kullanıcı kodu",
            note="Renamed with its label, which is how a real release renames a field.",
        ),
        Change(
            screen="main",
            target="searchButton",
            kind=RENAME,
            text="Sorgula",
            note="SC-18 starts here.",
        ),
        Change(
            screen="main",
            target="openButton",
            kind=RENAME,
            text="Detay",
            note="The control SC-18 waits to become enabled.",
        ),
        Change(
            screen="detail",
            target="saveButton",
            kind=RENAME,
            text="Güncelle",
            note="SC-34 saves with this button.",
        ),
        Change(
            screen="detail",
            target="emailLabel",
            kind=RENAME,
            text="E-posta adresi",
            note="A caption that only grows a word -- the easy case a healer should get.",
        ),
        Change(
            screen="detail",
            target="emailInput",
            kind=RENAME,
            accessible="E-posta adresi",
            note="Renamed with its label.",
        ),
    ),
)

V2B = Variant(
    id="v2b",
    kind=MOVE,
    summary="Controls change place among their siblings; ids, names and types are untouched.",
    changes=(
        Change(
            screen="login",
            target="loginButton",
            kind=MOVE,
            index=2,
            note="The button row is reversed: first becomes last.",
        ),
        Change(
            screen="login",
            target="exitButton",
            kind=MOVE,
            index=0,
            note="And last becomes first, so sibling index and geometry both move.",
        ),
        Change(
            screen="main",
            target="clearButton",
            kind=MOVE,
            cell=(1, 3),
            note="Swapped with Yenile: the same two cells, the other way round.",
        ),
        Change(
            screen="main",
            target="refreshButton",
            kind=MOVE,
            cell=(0, 3),
            note="A grid-layout move, which changes the cell and not the parent.",
        ),
        Change(
            screen="detail",
            target="departmentCombo",
            kind=MOVE,
            index=0,
            note="The Departman row becomes the form's first row, label and all.",
        ),
    ),
)

V2C = Variant(
    id="v2c",
    kind=RETYPE,
    summary="Five controls become another class, so their UIA ControlType changes.",
    changes=(
        Change(
            screen="login",
            target="headingLabel",
            kind=RETYPE,
            to_class="QLineEdit",
            note="Text -> Edit: the heading's string moves from the Name to the Value.",
        ),
        Change(
            screen="login",
            target="serverCombo",
            kind=RETYPE,
            to_class="QLineEdit",
            note="ComboBox -> Edit, the shape a Select step cannot play at all.",
        ),
        Change(
            screen="login",
            target="rememberMeCheck",
            kind=RETYPE,
            to_class="QComboBox",
            items=("Hayır", "Evet"),
            accessible="Beni hatırla",
            note="CheckBox -> ComboBox: a Click step has to become a Select step.",
        ),
        Change(
            screen="main",
            target="resultCountLabel",
            kind=RETYPE,
            to_class="QLineEdit",
            note="The label a result count is read from becomes a read-only field.",
        ),
        Change(
            screen="detail",
            target="statusLabel",
            kind=RETYPE,
            to_class="QLineEdit",
            note="Same for the form's status line, which SC-34 verifies.",
        ),
    ),
)

V2D = Variant(
    id="v2d",
    kind=REPARENT,
    summary="Controls move into new containers, which in Qt also lengthens their ids.",
    changes=(
        Change(
            screen="login",
            target="userNameInput",
            kind=REPARENT,
            group="credentialsGroup",
            group_title="Kimlik bilgileri",
            note="Two fields are grouped, so both ids gain a level.",
        ),
        Change(
            screen="login",
            target="passwordInput",
            kind=REPARENT,
            group="credentialsGroup",
            group_title="Kimlik bilgileri",
            note="Into the same container, as a release that groups a form would do.",
        ),
        Change(
            screen="main",
            target="customerGrid",
            kind=REPARENT,
            group="resultsGroup",
            group_title="Sonuçlar",
            note="Every grid and row step points at this control (#147).",
        ),
        Change(
            screen="detail",
            target="activeCheck",
            kind=REPARENT,
            group="flagsGroup",
            group_title="Durum",
            note="A check box wrapped on its own: parentPath changes, nothing else does.",
        ),
    ),
)

V2E = Variant(
    id="v2e",
    kind=ID_REMOVED,
    summary="Six controls lose their AutomationId; name, type and place stay as they were.",
    changes=(
        Change(
            screen="login",
            target="loginButton",
            kind=ID_REMOVED,
            note="A button that can now only be found by its caption.",
        ),
        Change(
            screen="login",
            target="passwordInput",
            kind=ID_REMOVED,
            note="An input with no visible text of its own: name, label or place.",
        ),
        Change(
            screen="main",
            target="searchButton",
            kind=ID_REMOVED,
            note="SC-18's first step.",
        ),
        Change(
            screen="main",
            target="customerGrid",
            kind=ID_REMOVED,
            note="The grid: its Name is the heading, which another control also carries.",
        ),
        Change(
            screen="detail",
            target="saveButton",
            kind=ID_REMOVED,
            note="A caption two screens share (Ayarlar also has Kaydet).",
        ),
        Change(
            screen="detail",
            target="nameInput",
            kind=ID_REMOVED,
            note="The required field of SC-34.",
        ),
    ),
)

V2F = Variant(
    id="v2f",
    kind="combined",
    summary="One release doing all five at once, plus a control that is simply gone.",
    changes=(
        Change(
            screen="main",
            target="searchButton",
            kind=RENAME,
            text="Bul",
            note="A shorter caption than v2a's, so the two versions cannot be confused.",
        ),
        Change(
            screen="main",
            target="openButton",
            kind=ID_REMOVED,
            note="The id goes while the caption stays: name is all that is left.",
        ),
        Change(
            screen="main",
            target="clearButton",
            kind=MOVE,
            cell=(1, 3),
            note="The same swap as v2b, on a screen that is changed in four other ways.",
        ),
        Change(
            screen="main",
            target="refreshButton",
            kind=MOVE,
            cell=(0, 3),
            note="Its other half.",
        ),
        Change(
            screen="main",
            target="wizardButton",
            kind=REMOVED,
            note="Gone with the feature. The right answer here is to fail, not to heal.",
        ),
        Change(
            screen="detail",
            target="statusLabel",
            kind=RETYPE,
            to_class="QLineEdit",
            note="Text -> Edit on the line SC-34 verifies.",
        ),
        Change(
            screen="detail",
            target="activeCheck",
            kind=REPARENT,
            group="flagsGroup",
            group_title="Durum",
            note="Re-parented, so its id gains a level while its name stays.",
        ),
    ),
)

#: Every change version, in the order the report quotes them.
VARIANTS: dict[str, Variant] = {
    variant.id: variant for variant in (V2A, V2B, V2C, V2D, V2E, V2F)
}

#: `--variant` values: the unchanged app and the six versions.
VARIANT_CHOICES = (BASELINE, *VARIANTS)


def changes_for(variant: str, screen: str) -> tuple[Change, ...]:
    """The changes of `variant` that apply to `screen`, in declaration order."""
    return tuple(
        change for change in VARIANTS[variant].changes if change.screen == screen
    )


def validate() -> list[str]:
    """Everything wrong with the change sets, as a list of messages (empty when sound).

    A spec that says nothing, or says two things about the same control, would make the
    ground truth meaningless, so `tests/test_variants.py` fails on any message here.
    """
    problems: list[str] = []
    for variant_id, variant in VARIANTS.items():
        if variant_id != variant.id:
            problems.append(f"{variant_id}: keyed as {variant_id}, says {variant.id}")
        if not variant.changes:
            problems.append(f"{variant.id}: no changes")
        seen: set[tuple[str, str]] = set()
        for change in variant.changes:
            where = f"{variant.id} {change.screen}.{change.target}"
            if change.screen not in SCREENS:
                problems.append(f"{where}: screen is not one of {SCREENS}")
            if change.kind not in KINDS:
                problems.append(f"{where}: kind {change.kind!r} is not one of {KINDS}")
            if (change.screen, change.target) in seen:
                problems.append(f"{where}: changed twice in one version")
            seen.add((change.screen, change.target))
            if not change.note:
                problems.append(f"{where}: no note saying what the change costs")
            problems.extend(_problems_of_kind(where, change))
    return problems


def _problems_of_kind(where: str, change: Change) -> list[str]:
    """What the fields of one change have to say for its kind, and nothing else."""
    problems: list[str] = []
    if change.kind == RENAME and change.text is None and change.accessible is None:
        problems.append(f"{where}: a rename needs a new text or a new accessible name")
    if change.kind == MOVE and (change.index is None) == (change.cell is None):
        problems.append(f"{where}: a move needs either an index or a cell, not both")
    if change.kind == RETYPE and not change.to_class:
        problems.append(f"{where}: a retype needs the class to become")
    if change.kind == REPARENT and not (change.group and change.group_title):
        problems.append(f"{where}: a re-parent needs a container id and a title")
    if change.items and change.kind != RETYPE:
        problems.append(f"{where}: items only mean something for a retype")
    if change.kind in (ID_REMOVED, REMOVED) and (
        change.text or change.accessible or change.to_class or change.group
    ):
        problems.append(
            f"{where}: {change.kind} changes nothing but the control's presence"
        )
    return problems
