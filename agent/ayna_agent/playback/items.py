"""Choosing an item in a list or a combo box: the `Select` keyword (#40).

`Select` is **not** a pure action, and that is the whole point of this module. `Click` and
`Type` each get one element and act on it; `Select` is told "choose the item whose text is
`value`" and the item is a *descendant* of the target — on a combo box, one that **may not
exist until the box is expanded** (#33 measured exactly that on Qt). So the keyword needs the
tree and a re-read, which is why the pieces are here and the loop is in `playback.runner`.

The order, and why:

1. look for an item of the target whose text is `value` in the tree just read;
2. if there is none and the target has `ExpandCollapse`, expand it and look again in a **new**
   read — the re-read is the point, because the items are new elements;
3. :func:`choose` it: `SelectionItem.Select`, then `Invoke` (a menu item answers to Invoke);
4. collapse again if step 2 expanded it, so the next step sees the screen the test left;
5. only then, for an editable combo box, `Value.SetValue` — last, because it *writes text*
   rather than choosing an item, and a box that accepts arbitrary text would otherwise hide a
   genuine "there is no such item" behind a pass.

**The first item with that text wins**, and that is the schema's own rule rather than a guess:
a row is "the first row from the top with a cell whose text is exactly `value`". Unlike
`resolve`, where "more than one match" has to be a failure because UI Automation does not
promise a stable child order between runs, a list's item order *is* what the user sees, and
pre-order (`tree.descendants`) is that order.

**Three failures, because a tester fixes each differently**: the target is not a list or a
combo box at all; it is, and has no item with that text (so the message says how many it has);
and it has the item but the provider refused to select it. The third is the Qt case from #33
and is a finding about the framework, not about the test — it must not read as "your text is
wrong".

Pure: the pattern lookup is injected, so the ladders above are tested with fakes off Windows
and only `uia_patterns` needs Windows (`agent/AGENTS.md`).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from ayna_agent.model import text_value
from ayna_agent.playback.actions import Patterns, uia_patterns
from ayna_agent.playback.checkpoint import show
from ayna_agent.playback.tree import Tree, displayed_text

#: Control types that are an item of something: what `Select` may choose. `DataItem` is a grid
#: row, which `SelectRow` addresses properly, but a one-column grid is a list to the person
#: using it and refusing it here would only make them write a `SelectRow` for the same thing.
#: Deliberately **not** `Text` or `Button`: a label inside a list is not an item, and choosing
#: one would act on the wrong element while reporting success.
ITEM_TYPES: frozenset[str] = frozenset(
    {"ListItem", "TreeItem", "MenuItem", "DataItem", "TabItem"}
)


class SelectFailed(Exception):
    """`Select` could not choose the item, with the reason already worded for the result."""


def items_of(tree: Tree, index: int) -> list[int]:
    """Positions of the target's items, in the order the application shows them.

    Every descendant, not only the direct children: a WPF `ComboBox` keeps its `ListItem`s
    under an inner `List`, and a Qt popup nests them one level deeper again, so "the children
    of the combo box" would find nothing on either.
    """
    return [
        position
        for position in tree.descendants(index)
        if tree.descriptors[position].control_type in ITEM_TYPES
    ]


def find(
    tree: Tree,
    index: int,
    value: str,
    patterns: Patterns = uia_patterns,
) -> tuple[int | None, int]:
    """`(the first item whose text is `value`, how many items the target has)`.

    The text is :func:`playback.tree.displayed_text` — the schema's one rule for a cell or an
    item — so `Select` reads an item exactly as a `rowExists` on the same list does.
    """
    items = items_of(tree, index)
    for position in items:
        text = displayed_text(
            tree.descriptors[position], tree.infos[position], patterns
        )
        if text == value:
            return position, len(items)
    return None, len(items)


def selectable(element: Any, patterns: Patterns = uia_patterns) -> bool:
    """Whether this element could hold items at all: it has a Selection or ExpandCollapse.

    Asked only when the target shows no items, to tell "not a list or a combo box" from "a
    list that is empty or still filling". A `Selection` pattern is what a list, a tab control
    and a combo box have in common; `ExpandCollapse` catches a collapsed combo box whose
    `Selection` some providers only expose once it is open.
    """
    return any(
        patterns(element, name) is not None for name in ("Selection", "ExpandCollapse")
    )


def can_expand(element: Any, patterns: Patterns = uia_patterns) -> bool:
    return patterns(element, "ExpandCollapse") is not None


def expand(element: Any, patterns: Patterns = uia_patterns) -> bool:
    """Open the target. False when it has no `ExpandCollapse` or refused to open."""
    pattern = patterns(element, "ExpandCollapse")
    return pattern is not None and _try(lambda: pattern.Expand())


def collapse(element: Any, patterns: Patterns = uia_patterns) -> bool:
    """Close the target again. A refusal is not a step failure: the item is already chosen."""
    pattern = patterns(element, "ExpandCollapse")
    return pattern is not None and _try(lambda: pattern.Collapse())


def choose(element: Any, patterns: Patterns = uia_patterns) -> str | None:
    """Select the item. Returns the pattern that did it, or None when both refused.

    `SelectionItem.Select` first, because that is what choosing an item *means*; `Invoke`
    second, for a menu item, which is activated rather than selected.
    """
    item = patterns(element, "SelectionItem")
    if item is not None and _try(lambda: item.Select()):
        return "SelectionItem"
    invoke = patterns(element, "Invoke")
    if invoke is not None and _try(lambda: invoke.Invoke()):
        return "Invoke"
    return None


def write(element: Any, value: str, patterns: Patterns = uia_patterns) -> bool:
    """Last resort for an **editable** combo box: write `value` as its text.

    Only after the item ladder has failed, and only when the box is not read-only. It does not
    choose an item, so the result records `SetValue` and the run report shows that the step
    typed rather than chose.

    **The value is read back**, and a box that did not take it counts as a refusal: `SetValue`
    returns without complaint on a provider that then normalises or ignores the text, and
    "AYNA says it chose Ankara" while the box still reads "Adana" is the one outcome a tester
    cannot debug. Compared through :func:`ayna_agent.model.text_value`, so a box that merely
    trimmed the text still counts as having taken it.
    """
    pattern = patterns(element, "Value")
    if pattern is None or _read_only(pattern):
        return False
    if not _try(lambda: pattern.SetValue(value)):
        return False
    written = _read(lambda: pattern.CurrentValue)
    return text_value(written) == value


def not_a_list(name: str) -> str:
    """The target cannot hold items at all."""
    return (
        f"{name}: Select needs a list or a combo box; this element shows no items and has "
        f"neither a Selection nor an ExpandCollapse pattern"
    )


def no_such_item(name: str, value: str, count: int, timeout_ms: int) -> str:
    """The target is a list, and nothing in it reads as `value`.

    The count is in the message because it is what separates the two things a tester does
    next: 0 items means the list never filled (or its popup is a window of its own), while 12
    items means the text is wrong. `after N ms` only when it re-read until the time ran out,
    the same distinction the checkpoints make.
    """
    after = f" after {timeout_ms} ms" if timeout_ms else ""
    if not count:
        return (
            f"{name}: no item has the text {show(value)}{after}; the target shows no items "
            f"at all, so its list may be filled only when it is open, or be a popup window "
            f"of its own"
        )
    return (
        f"{name}: no item has the text {show(value)}{after}; the target offers "
        f"{_items(count)}"
    )


def refused(name: str, value: str, tried: Sequence[str]) -> str:
    """The item is there and the provider would not select it: the Qt case from #33.

    Worded as a finding about the application, not about the test, because that is what it is.
    """
    return (
        f"{name}: the item {show(value)} is there, but the application refused to select it "
        f"({' and '.join(tried)} were tried)"
    )


def vanished(exc: Exception, value: str) -> str:
    """The target was there a moment ago and is not now: a different fact from "no such item".

    Same shape as the checkpoint's "while checking <property>", because it is the same event:
    the window moved on between two reads of one wait.
    """
    return f"{exc} while choosing {show(value)}"


def _items(count: int) -> str:
    return "1 item" if count == 1 else f"{count} items"


def _read(call: Any) -> Any:
    try:
        return call()
    except Exception:  # noqa: BLE001 - a provider that does not answer means "no value"
        return None


def _read_only(pattern: Any) -> bool:
    try:
        return bool(pattern.CurrentIsReadOnly)
    except Exception:  # noqa: BLE001 - a provider that does not answer is treated as writable
        return False


def _try(call: Any) -> bool:
    """`call()`, True when it returned, False when the provider refused it.

    Same rule as `playback.actions._try`: a pattern can be present and still refuse, and a
    refusal moves to the next fallback rather than ending the step.
    """
    try:
        call()
    except Exception:  # noqa: BLE001 - COMError and pywinauto both land here; same meaning
        return False
    return True
