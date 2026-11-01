"""The window snapshot document: one window's whole subtree at one moment (#12).

Like :mod:`ayna_agent.model`, this module reads no UI Automation. It takes the **raw nodes**
a walk already collected -- plain mappings of UIA properties plus ``id`` and ``parent`` -- and
assembles the document that `schemas/snapshot.schema.json` validates. The walk itself is in
``recognition/uia.py`` and only runs on Windows; keeping the two apart is what lets the
document's shape be tested on any OS and replayed over the dumps of #6.

Three things about the document are normative, because other components depend on them and a
schema cannot express them:

- **Element order is pre-order**, the window's own root element first, a parent always before
  its children. One pass then builds the tree, which is what the server's import (#15) and the
  Spy's tree (#24) do.
- **Element ids are ``e<position>``** in that order, and they are *opaque*: a healing proposal
  names one (#149), so it must be stable inside a document, but nothing may parse or order it.
- **A snapshot only exists for a walk that covered the whole window.** A walk that ran out of
  its budget raises :class:`ayna_agent.rpc.SnapshotTimeout` and returns no document, because
  candidates ranked from a partial tree give a confident but unfounded proposal (RS 0.6
  FR-29/FR-35, "search incomplete"; TBD-5).

:func:`dumps` writes a canonical text -- fixed key order, two-space indent, LF, UTF-8 kept as
UTF-8 -- so that ``dumps(loads(text)) == text`` for every document this module accepts, which
is the load-save round trip #12 asks for.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

from ayna_agent import __version__
from ayna_agent.model import JSON_NAMES, describe_tree

#: Schema version this module reads and writes.
VERSION = "0.1"

#: How the computed properties (`parentPath`, `siblingIndex`, `nearestLabel`, `dpi`) were
#: derived. Healing recomputes them from a stored snapshot (#43), so a snapshot derived by
#: another rule set is not comparable with one derived by this one. The canonical constant
#: belongs next to the graph features of #43 (`heal/features.py`, galip); until that exists,
#: this is the one value, and a change to a derivation rule in #11 or #43 bumps both.
FEATURE_VERSION = "features-v0"

#: Default time budget for one window's walk, in milliseconds. 2.2x the slowest full walk
#: measured on a pilot window (2.26 s for 114 WinForms elements) and room for about 330
#: elements at that rate -- see `eval/spikes/uia-walk-cost.md` (#161) for why it is not
#: NFR-02's 2 s: that bound is scoped to the sample app, where an element costs ~4.3 ms.
DEFAULT_BUDGET_MS = 5_000

#: Key order of the document, so that a round trip gives the same file back.
_DOCUMENT_KEYS = ("version", "snapshotId", "capture", "app", "window", "elements")
_CAPTURE_KEYS = (
    "startedAt",
    "durationMs",
    "budgetMs",
    "elementCount",
    "readErrors",
    "agentVersion",
    "featureVersion",
)
_APP_KEYS = ("exeName", "fileVersion")
_WINDOW_KEYS = ("handle", "title", "className", "processId", "bounds", "dpi")
_NODE_KEYS = ("id", "parentId", "element")
_ELEMENT_KEYS = tuple(JSON_NAMES.values())


def new_snapshot_id() -> str:
    """A fresh snapshot id. A UUID4: the agent makes it, nothing else has to agree on it."""
    return str(uuid.uuid4())


def element_id(position: int) -> str:
    """The id of the element at `position` in the pre-order list."""
    return f"e{position}"


def build(
    nodes: Sequence[Mapping[str, Any]],
    *,
    window: Mapping[str, Any],
    app: Mapping[str, Any],
    started_at: datetime,
    duration_ms: int,
    budget_ms: int = DEFAULT_BUDGET_MS,
    read_errors: int = 0,
    snapshot_id: str | None = None,
    agent_version: str = __version__,
    feature_version: str = FEATURE_VERSION,
) -> dict[str, Any]:
    """The snapshot document for one window, from raw nodes in pre-order.

    `nodes` is what a walk collected: the root window first, each node carrying the UIA
    properties under the snake_case names of :func:`ayna_agent.model.describe_tree` plus its
    ``id`` (its position in this list) and ``parent`` (the parent's id, None for the root).
    `window` and `app` are camelCase already, as `listWindows` returns them; blank values are
    left out, like every absent element property.

    Raises ValueError when the nodes are not a single tree in pre-order, because every
    consumer builds the tree in one pass over this list.
    """
    _check_tree(nodes)
    descriptors = describe_tree(nodes)
    elements = [
        {
            "id": element_id(position),
            "parentId": (
                None if node.get("parent") is None else element_id(int(node["parent"]))
            ),
            "element": descriptor.to_json(),
        }
        for position, (node, descriptor) in enumerate(zip(nodes, descriptors))
    ]
    capture = {
        "startedAt": _timestamp(started_at),
        "durationMs": int(duration_ms),
        "budgetMs": int(budget_ms),
        "elementCount": len(elements),
        "readErrors": int(read_errors),
        "agentVersion": agent_version,
        "featureVersion": feature_version,
    }
    document = {
        "version": VERSION,
        "snapshotId": snapshot_id or new_snapshot_id(),
        "capture": capture,
        "app": _prune(app, _APP_KEYS),
        "window": _prune(window, _WINDOW_KEYS),
        "elements": elements,
    }
    return canonical(document)


def _timestamp(moment: datetime) -> str:
    """ISO 8601 with a UTC offset, to the second.

    A snapshot is compared with a screenshot taken just before the walk (#54), so a reader
    must be able to tell which came first wherever the two were taken; a naive datetime
    cannot say that.
    """
    if moment.tzinfo is None or moment.tzinfo.utcoffset(moment) is None:
        raise ValueError("startedAt needs a time zone: use datetime.now().astimezone()")
    return moment.isoformat(timespec="seconds")


def _check_tree(nodes: Sequence[Mapping[str, Any]]) -> None:
    if not nodes:
        raise ValueError("a snapshot has at least the window's own root element")
    for position, node in enumerate(nodes):
        if node.get("id", position) != position:
            raise ValueError(
                f"node {position} has id {node.get('id')!r}, expected its position"
            )
        parent = node.get("parent")
        if position == 0:
            if parent is not None:
                raise ValueError(
                    "the first node is the window's root and has no parent"
                )
            continue
        if parent is None:
            raise ValueError(
                f"node {position} is a second root: a snapshot is one window"
            )
        if (
            not isinstance(parent, int)
            or isinstance(parent, bool)
            or not 0 <= parent < position
        ):
            # Pre-order is what lets a consumer build the tree in one pass, so a forward
            # reference is refused rather than silently reordered.
            raise ValueError(
                f"node {position} has parent {parent!r}, expected an earlier node"
            )


def _prune(values: Mapping[str, Any], keys: Sequence[str]) -> dict[str, Any]:
    """`values` in `keys` order, without the blanks and without unknown keys."""
    unknown = sorted(set(values) - set(keys))
    if unknown:
        raise ValueError(f"unknown keys: {', '.join(unknown)}")
    out: dict[str, Any] = {}
    for key in keys:
        value = values.get(key)
        if value is None or (isinstance(value, str) and not value.strip()):
            continue
        out[key] = list(value) if key == "bounds" else value
    return out


def canonical(document: Mapping[str, Any]) -> dict[str, Any]:
    """The same document with every key in the schema's order and nothing else in it.

    Two documents that differ only in key order are the same snapshot, so the round trip is
    defined on this form rather than on whatever order a file happened to be written in.
    """
    out = _ordered(document, _DOCUMENT_KEYS, "document")
    out["capture"] = _ordered(document["capture"], _CAPTURE_KEYS, "capture")
    out["app"] = _ordered(document.get("app", {}), _APP_KEYS, "app")
    out["window"] = _ordered(document["window"], _WINDOW_KEYS, "window")
    out["elements"] = [
        {
            **_ordered(node, _NODE_KEYS, "element"),
            "element": _ordered(node["element"], _ELEMENT_KEYS, "element properties"),
        }
        for node in document["elements"]
    ]
    return out


def _ordered(
    values: Mapping[str, Any], keys: Sequence[str], what: str
) -> dict[str, Any]:
    unknown = sorted(set(values) - set(keys))
    if unknown:
        raise ValueError(f"unknown {what} keys: {', '.join(unknown)}")
    return {key: values[key] for key in keys if key in values}


def dumps(document: Mapping[str, Any]) -> str:
    """The canonical text of `document`: UTF-8, two-space indent, LF, one trailing newline.

    Turkish labels stay readable (`ensure_ascii=False`), which is also what the server and
    the client store.
    """
    return json.dumps(canonical(document), indent=2, ensure_ascii=False) + "\n"


def loads(text: str) -> dict[str, Any]:
    """Read a snapshot document, refusing another version and a broken tree.

    Structural rules a JSON Schema cannot state are checked here: one root, unique ids,
    pre-order, and `elementCount` agreeing with the list. Raises ValueError for a document
    this release does not speak, TypeError when the JSON is not an object at all.
    """
    document = json.loads(text)
    if not isinstance(document, Mapping):
        raise TypeError(
            f"a snapshot document is a JSON object, not {type(document).__name__}"
        )
    version = document.get("version")
    if version != VERSION:
        raise ValueError(f"snapshot document version {version!r}, expected {VERSION!r}")
    missing = [key for key in _DOCUMENT_KEYS if key not in document]
    if missing:
        raise ValueError(f"the document is missing: {', '.join(missing)}")
    elements = document["elements"]
    if not isinstance(elements, list) or not elements:
        raise ValueError("a snapshot has at least the window's own root element")
    count = document["capture"].get("elementCount")
    if count != len(elements):
        raise ValueError(
            f"capture.elementCount is {count!r}, but there are {len(elements)} elements"
        )
    seen: set[str] = set()
    for position, node in enumerate(elements):
        parent = node.get("parentId")
        if position == 0:
            if parent is not None:
                raise ValueError(
                    "the first element is the window's root and has no parent"
                )
        elif parent not in seen:
            # Checked before this element's own id joins `seen`, so an element cannot be its
            # own parent and a forward reference cannot pass as pre-order.
            raise ValueError(
                f"element {node.get('id')!r} names parent {parent!r}, which is not above it"
            )
        node_id = node.get("id")
        if node_id in seen:
            raise ValueError(f"element id {node_id!r} appears twice")
        seen.add(node_id)
    return canonical(document)


def read(path: str | Path) -> dict[str, Any]:
    return loads(Path(path).read_text(encoding="utf-8"))


def write(document: Mapping[str, Any], path: str | Path) -> None:
    """Write the canonical text. `newline=""` keeps the LF on Windows too, so the same
    snapshot is byte-identical on every machine."""
    Path(path).write_text(dumps(document), encoding="utf-8", newline="")
