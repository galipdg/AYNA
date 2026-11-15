"""Applies one change version to a built window, and reports what it touched (#46).

`variants.py` declares the change sets; this module is the only place that knows Qt. It is
called at the end of every window's `__init__` (`windows.py`), so a version is applied to the
screen a tester opens *and* to the windows that screen opens later -- a run that logs in and
reaches the customer list gets the changed list, not the v1 one.

Two things it does besides the change itself, both because the change has to be observable:

* **The window title carries the version** (`AYNA Örnek 1.0-v2a - Giriş`), so a screenshot or
  a snapshot says which copy it came from. The window's UIA ClassName is untouched, so every
  test and `uia_check.py` still find the screen the same way.
* **Every widget it touched is reported**, keyed by the control's v1 `objectName`, with `None`
  for one that is gone. `ground_truth.py` builds the old -> new mapping from that report
  rather than from the declaration, so a change that drags a form label along with it lands in
  the mapping without anyone having to remember to declare the label.

The surgery itself follows three rules that the app's own code forces:

* **A retype swaps the widget**, so the window's attribute (`self.result_count_label`) is
  rebound to the new one. Without that, `setText` would be called on a deleted C++ object and
  the app would die on the next search. `variants.py` only ever retypes to a class whose API
  covers what the app calls.
* **A form row moves as a row.** `QFormLayout` owns the label, and a field that moved or was
  re-parented without its caption would be a different change from the declared one.
* **A removal unbinds the attribute first**, so a later call raises `AttributeError` in Python
  instead of taking the process down with a dangling pointer.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QBoxLayout,
    QComboBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QLayout,
    QLineEdit,
    QWidget,
)

import texts
from variants import (
    BASELINE,
    ID_REMOVED,
    MOVE,
    REMOVED,
    RENAME,
    REPARENT,
    RETYPE,
    SCREENS,
    VARIANTS,
    Change,
    changes_for,
)

#: The classes a control may be retyped into. Both are measured in the README's id tables, so
#: the ControlType the change produces (`Edit`, `ComboBox`) is known and not guessed.
RETYPE_CLASSES = ("QLineEdit", "QComboBox")

#: Widget classes the user types or picks in. A label that becomes a `QLineEdit` is made
#: read-only, so the app still behaves as it did; a combo box that becomes one stays editable.
_INPUT_CLASSES = (QLineEdit, QComboBox)

#: The version `apply_active` applies, set once by `sample_app.py` before the first window.
_active: str = BASELINE


def set_active(variant: str | None) -> None:
    """Choose the version every window built from now on gets. `None` or `v1` means none."""
    global _active
    if variant not in (None, BASELINE) and variant not in VARIANTS:
        raise ValueError(f"unknown variant {variant!r}")
    _active = variant or BASELINE


def active() -> str:
    """The version currently being applied, `v1` when the app is unchanged."""
    return _active


def apply_active(window: QWidget) -> dict[str, QWidget | None]:
    """Apply the active version to `window`. The hook every window's `__init__` ends with."""
    return apply(window, _active)


def apply(window: QWidget, variant: str) -> dict[str, QWidget | None]:
    """Change `window` into its `variant` self and report every control that was touched.

    The key is the control's **v1** `objectName`, which is how a scenario, a repository object
    and the ground truth all name it.
    """
    if variant in (None, BASELINE):
        return {}
    if variant not in VARIANTS:
        raise ValueError(f"unknown variant {variant!r}")

    window.setWindowTitle(texts.with_variant(window.windowTitle(), variant))

    screen = window.objectName()
    if screen not in SCREENS:
        # The settings screen, the wizard and the two dialogs are unchanged on purpose; they
        # still get the version in their title, which is why this is not an early return.
        return {}

    touched: dict[str, QWidget | None] = {}
    for change in changes_for(variant, screen):
        touched.update(_apply_change(window, change))
    return touched


def _apply_change(window: QWidget, change: Change) -> dict[str, QWidget | None]:
    """One change, dispatched by kind. Fails loudly on a target that is not on the screen."""
    widget = window.findChild(QWidget, change.target)
    if widget is None:
        raise LookupError(
            f"{change.screen}.{change.target}: no such control, so "
            f"variants.py and windows.py disagree"
        )
    if change.kind == RENAME:
        return _rename(widget, change)
    if change.kind == ID_REMOVED:
        return _remove_id(widget, change)
    if change.kind == MOVE:
        return _move(widget, change)
    if change.kind == RETYPE:
        return _retype(window, widget, change)
    if change.kind == REPARENT:
        return _reparent(window, widget, change)
    if change.kind == REMOVED:
        return _remove(window, widget, change)
    raise ValueError(f"{change.screen}.{change.target}: unknown kind {change.kind!r}")


# --- the six kinds -------------------------------------------------------------------------


def _rename(widget: QWidget, change: Change) -> dict[str, QWidget | None]:
    if change.text is not None:
        setter = getattr(widget, "setText", None)
        if setter is None:
            raise TypeError(
                f"{change.screen}.{change.target}: a {type(widget).__name__} has no text"
            )
        setter(change.text)
    if change.accessible is not None:
        widget.setAccessibleName(change.accessible)
    return {change.target: widget}


def _remove_id(widget: QWidget, change: Change) -> dict[str, QWidget | None]:
    """Clear `objectName`, which is what Qt builds the AutomationId from.

    Never done to a control that has named children **of the app's own**: Qt's id is the
    whole object chain, so clearing a container's name would silently take the id off every
    control below it, and the version would be measuring something it does not declare.

    Qt's own internals (`qt_scrollarea_viewport` under the grid, `qt_spinbox_lineedit`) do
    lose their path, because they hang below the control whose name went. That is a real
    consequence of removing an id and not a side effect of how this is implemented -- the
    README's v1 table has one such row (`detail.notesInput.qt_scrollarea_viewport`).
    """
    own_children = [
        child
        for child in widget.findChildren(QWidget)
        if child.objectName() and not child.objectName().startswith("qt_")
    ]
    if own_children:
        raise ValueError(
            f"{change.screen}.{change.target}: has named children "
            f"({', '.join(child.objectName() for child in own_children)}), so clearing "
            f"its name would take the id off those too"
        )
    widget.setObjectName("")
    return {change.target: widget}


def _move(widget: QWidget, change: Change) -> dict[str, QWidget | None]:
    layout = owning_layout(widget)
    if change.cell is not None:
        if not isinstance(layout, QGridLayout):
            raise TypeError(
                f"{change.screen}.{change.target}: a cell move needs a QGridLayout, "
                f"not a {type(layout).__name__}"
            )
        layout.removeWidget(widget)
        layout.addWidget(widget, *change.cell)
        return {change.target: widget}

    if isinstance(layout, QFormLayout):
        label = _take_form_row(layout, widget)
        _insert_form_row(layout, change.index, label, widget)
        touched: dict[str, QWidget | None] = {change.target: widget}
        if label is not None:
            touched[label.objectName()] = label
        return touched
    if isinstance(layout, QBoxLayout):
        layout.removeWidget(widget)
        layout.insertWidget(change.index, widget)
        return {change.target: widget}
    raise TypeError(
        f"{change.screen}.{change.target}: no index move for a {type(layout).__name__}"
    )


def _retype(
    window: QWidget, widget: QWidget, change: Change
) -> dict[str, QWidget | None]:
    """Replace the control with one of another class, in its own place in its own layout."""
    if change.to_class not in RETYPE_CLASSES:
        raise ValueError(
            f"{change.screen}.{change.target}: cannot retype to {change.to_class!r}"
        )
    layout = owning_layout(widget)
    new = _build_replacement(widget, change)
    layout.replaceWidget(widget, new)
    _rebind(window, widget, new)
    widget.setParent(None)
    widget.deleteLater()
    return {change.target: new}


def _reparent(
    window: QWidget, widget: QWidget, change: Change
) -> dict[str, QWidget | None]:
    """Move the control into a container, creating it where the control used to be.

    In Qt this is also an id change: the AutomationId is the chain of `objectName`s, so the
    control's id gains the container's level. There is no way to re-parent and keep the id,
    which is the measured fact this version is built to show.
    """
    group = window.findChild(QGroupBox, change.group)
    source = owning_layout(widget)
    if group is None:
        group = QGroupBox(change.group_title, window)
        group.setObjectName(change.group)
        QFormLayout(group)
        top = window.layout()
        top.insertWidget(_top_level_index(top, widget), group)
    group_layout = group.layout()

    touched: dict[str, QWidget | None] = {change.target: widget}
    if isinstance(source, QFormLayout):
        label = _take_form_row(source, widget)
        if label is not None:
            group_layout.addRow(label, widget)
            touched[label.objectName()] = label
        else:
            group_layout.addRow(widget)
    else:
        source.removeWidget(widget)
        group_layout.addRow(widget)
    return touched


def _remove(
    window: QWidget, widget: QWidget, change: Change
) -> dict[str, QWidget | None]:
    """Take the control out of the window for good; its ground-truth counterpart is `null`."""
    layout = owning_layout(widget)
    touched: dict[str, QWidget | None] = {change.target: None}
    label = None
    if isinstance(layout, QFormLayout):
        label = _take_form_row(layout, widget)
    else:
        layout.removeWidget(widget)
    # Unbind before deleting: a window that still holds the attribute would call into a
    # deleted C++ object and take the process down, instead of raising in Python.
    _rebind(window, widget, None)
    widget.setParent(None)
    widget.deleteLater()
    if label is not None:
        touched[label.objectName()] = None
        _rebind(window, label, None)
        label.setParent(None)
        label.deleteLater()
    return touched


# --- Qt helpers ----------------------------------------------------------------------------


def _build_replacement(old: QWidget, change: Change) -> QWidget:
    """The new widget of a retype: same id, same string, the class the change asks for.

    What the retype *costs* a locator is deliberate and measured: a label's string moves from
    the UIA Name to the Value, because a `QLineEdit` reports its text as the value and takes
    its Name from `accessibleName` alone.
    """
    parent = old.parentWidget()
    accessible = (
        change.accessible if change.accessible is not None else old.accessibleName()
    )
    if change.to_class == "QLineEdit":
        new: QWidget = QLineEdit(parent)
        new.setText(_string_of(old))
        new.setReadOnly(not isinstance(old, _INPUT_CLASSES))
    else:
        new = QComboBox(parent)
        new.addItems(list(change.items))
    new.setObjectName(old.objectName())
    if accessible:
        new.setAccessibleName(accessible)
    # `isHidden`, not `isVisible`: nothing is visible yet while the window is being built, so
    # copying `isVisible()` hid every replacement for good (measured 2026-11-15 -- the UIA
    # tree had no `headingLabel` at all). `isHidden` is "explicitly hidden", which is what the
    # wizard's off-page widgets are and what has to be carried over.
    if old.isHidden():
        new.setVisible(False)
    return new


def _string_of(widget: QWidget) -> str:
    """The string a control shows: a combo box's current item, otherwise its text."""
    if isinstance(widget, QComboBox):
        return widget.currentText()
    getter = getattr(widget, "text", None)
    return getter() if getter is not None else ""


def owning_layout(widget: QWidget) -> QLayout:
    """The layout that directly holds `widget`, which is not always its parent's own.

    The screens nest layouts (a button row inside the window's column), so the layout a
    control sits in has to be searched for rather than read off the parent widget.
    """
    parent = widget.parentWidget()
    top = parent.layout() if parent is not None else None
    found = _find_layout(top, widget) if top is not None else None
    if found is None:
        raise LookupError(f"{widget.objectName()!r} is in no layout of its parent")
    return found


def _find_layout(layout: QLayout, widget: QWidget) -> QLayout | None:
    for index in range(layout.count()):
        item = layout.itemAt(index)
        if item.widget() is widget:
            return layout
        child = item.layout()
        if child is not None:
            found = _find_layout(child, widget)
            if found is not None:
                return found
    return None


def _top_level_index(top: QLayout, widget: QWidget) -> int:
    """Where in the window's own layout the branch holding `widget` sits.

    A new container goes exactly there, so the screen keeps its reading order instead of
    growing a group box at the bottom.
    """
    for index in range(top.count()):
        item = top.itemAt(index)
        if item.widget() is widget:
            return index
        child = item.layout()
        if child is not None and _find_layout(child, widget) is not None:
            return index
    return top.count()


def _take_form_row(layout: QFormLayout, widget: QWidget) -> QWidget | None:
    """Take the control's whole row out of the form and return its label, if it had one."""
    row, _role = layout.getWidgetPosition(widget)
    if row < 0:
        raise LookupError(f"{widget.objectName()!r} is not a row of this form")
    label_item = layout.itemAt(row, QFormLayout.ItemRole.LabelRole)
    label = label_item.widget() if label_item is not None else None
    layout.takeRow(row)
    return label


def _insert_form_row(
    layout: QFormLayout, row: int, label: QWidget | None, widget: QWidget
) -> None:
    if label is None:
        layout.insertRow(row, widget)
    else:
        layout.insertRow(row, label, widget)


def _rebind(window: QWidget, old: QWidget, new: QWidget | None) -> None:
    """Point every attribute of `window` that held `old` at `new`.

    The windows keep their controls as attributes (`self.save_button`), and a swapped or
    deleted widget would leave those pointing at a dead C++ object.
    """
    for name, value in list(vars(window).items()):
        if value is old:
            setattr(window, name, new)
