"""One read of a window: its shape, and the text a cell or an item shows (#40).

`Click`, `Type` and the element checkpoints need **one** element and nothing around it, so #26
could throw the raw nodes away as soon as `describe_tree` had turned them into descriptors.
`Select` and the row keywords cannot: "the item whose text is `value`" and "the row `row`
addresses" are *descendants* of the target, so playback has to keep the tree it just read, not
only the list of descriptors.

:class:`Tree` is that: one read, with the parent/child links the nodes already carry
(`id`/`parent`, which `describe_tree` reads too) resolved into positions, so the descriptor,
the live element and the children of one target are all reachable by the same index. A read is
never cached between polls -- a re-read gives new live elements and holding the old ones would
act on stale handles, the same reason #22's `elementFromPoint` compares identity rather than
trusting a remembered element.

:func:`displayed_text` is the other thing both `Select` and the row checks need, and it is
**one rule in one place** because the step schema states it once: "a cell's text is its
ValuePattern value when that value is non-empty, else its UI Automation Name". Qt cells and
list items have an empty ValuePattern and carry their text in Name; a WinForms `DataGridView`
cell's Name is its column header plus row index, and its text is the Value. Two
implementations of that would drift, and a `Select` that read an item differently from a
`rowExists` on the same list would be indefensible.

Pure: the pattern lookup is injected, so every rule here is tested with fakes off Windows
(`agent/AGENTS.md`).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from ayna_agent.model import Element, describe_tree, text_value
from ayna_agent.playback.actions import Patterns, uia_patterns


@dataclass(frozen=True, slots=True)
class Tree:
    """One window as it was read once: nodes, their descriptors and their live elements.

    All three are indexed alike: `descriptors[i]` describes `nodes[i]` and `infos[i]` is the
    element to act on. That is the invariant `recognition.uia.read_tree` returns and the one
    `playback.resolve` already relies on (`Resolution.index`).
    """

    nodes: Sequence[Mapping[str, Any]]
    descriptors: Sequence[Element]
    infos: Sequence[Any]
    #: position -> its children's positions, in tree order. Built once per read.
    links: Mapping[int, tuple[int, ...]]

    def children(self, index: int) -> tuple[int, ...]:
        """The direct children of the node at `index`, in the order the walk saw them."""
        return self.links.get(index, ())

    def descendants(self, index: int) -> list[int]:
        """Every node under `index`, in pre-order, excluding `index` itself.

        Pre-order because that is the order the application shows things in: the first item of
        a list comes before the second, which is what makes "the first row whose cell is
        `value`" (the schema's own rule for a row) mean the same thing here as on screen.
        """
        out: list[int] = []
        stack = list(reversed(self.children(index)))
        while stack:
            position = stack.pop()
            out.append(position)
            stack.extend(reversed(self.children(position)))
        return out


def of(nodes: Sequence[Mapping[str, Any]], infos: Sequence[Any]) -> Tree:
    """A :class:`Tree` from what `read_tree` returned.

    A node's `parent` is another node's `id`, not its position, so the ids are mapped to
    positions first: the walk happens to number them alike today, but `describe_tree` already
    treats `id` as the link and a tree that disagreed would otherwise give the wrong children
    silently -- the worst failure a selector can have.
    """
    position = {node.get("id", index): index for index, node in enumerate(nodes)}
    links: dict[int, list[int]] = {}
    for index, node in enumerate(nodes):
        parent = position.get(node.get("parent"))
        if parent is not None and parent != index:
            links.setdefault(parent, []).append(index)
    return Tree(
        nodes=nodes,
        descriptors=describe_tree(nodes),
        infos=infos,
        links={parent: tuple(kids) for parent, kids in links.items()},
    )


def displayed_text(
    descriptor: Element,
    element: Any,
    patterns: Patterns = uia_patterns,
) -> str | None:
    """The text a cell or an item shows, by the step schema's own rule.

    ValuePattern value when it is non-empty, else the UI Automation Name. Compared through
    :func:`ayna_agent.model.text_value`, so it is matched in the form a descriptor stores text
    in (stripped, blank is nothing) -- a value a tester reads in the Spy is then the value
    their step can write.
    """
    pattern = patterns(element, "Value")
    if pattern is not None:
        value = text_value(_read(lambda: pattern.CurrentValue))
        if value:
            return value
    return text_value(descriptor.name)


def _read(call: Any) -> Any:
    try:
        return call()
    except Exception:  # noqa: BLE001 - a provider that does not answer means "no value"
        return None
