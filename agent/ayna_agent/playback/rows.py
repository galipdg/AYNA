"""The rows of a grid or a list: `SelectRow`, and the `cell` / `rowExists` / `rowCount` checks.

Step schema v0.2 (ADR `2026-10-28-step-schema-v0-2-rows`) addresses a row either by position
(`{"index": 2}`, counted from 1, header rows not counted) or by a key cell
(`{"value": "Yılmaz", "column": "Soyad"}`, the first row from the top, the column optional).
This module turns one read of the window (`playback.tree`) into those rows.

**There is no single shape for "a row", and the ADR measured all three**, so the rule is
structural rather than per framework:

* **the item is the row** -- KeePass 2's entry list is a `List` of `ListItem`s, each with one
  `Text` child per column *in header order*; a WinForms `DataGridView` row is an item with its
  cells as children. Any item that has cell children is a row and those children are its cells.
* **the items are the cells** -- a Qt `QTableView` has *no row element at all*
  (`QAccessible::Row` maps to `HeaderItem`), only `DataItem` cells directly under the table. So
  for a `Table`/`DataGrid` whose items are leaves, the rows are the cells grouped by
  `GridItemPattern.CurrentRow`, which is **0-based** while `index` counts from 1.
* **the item is a one-cell row** -- a `QListWidget` is a `List` of leaf `ListItem`s, and the
  row's only cell is the item itself.

**The columns come from the captured tree, by the same rule the server uses** -- a `Header`
child's named `HeaderItem`s, or for a grid the header children before the first cell, minus the
ones lying wholly left of it (Qt's row headers `1`, `2`, …). That duplication is deliberate and
has to stay exact: `server/.../repository/GridColumns.java` is what fills `RepoObject.columns`
and therefore what the step editor offered the tester as a column (#221). A column list that
disagreed would read the cell next to the one they picked -- and report `passed` doing it.

**A target reporting no columns at all is not an error** (an empty Qt table reports none,
because Qt collects headers through row 0): a key with a column then matches no row, which the
ADR settles as `rowExists` false rather than a broken step. A column that is *not among* the
columns the target does report is a genuine mistake and says so, with the names it has.

Pure: the pattern lookup is injected, so every rule above is tested with fakes off Windows
(`agent/AGENTS.md`); only `uia_patterns` needs Windows.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from ayna_agent.playback.actions import Patterns, uia_patterns
from ayna_agent.playback.checkpoint import says, show
from ayna_agent.playback.tree import Tree, displayed_text

#: Checkpoint properties that read the target's rows rather than the target itself.
ROW_PROPERTIES: frozenset[str] = frozenset({"cell", "rowExists", "rowCount"})

#: Control types that have columns, so a `cell` check applies to them (step schema v0.2).
GRID_TYPES: frozenset[str] = frozenset({"DataGrid", "Table"})

#: An item of a grid or list: a row, or -- on a Qt table, which has no row element -- a cell.
ITEM_TYPES: frozenset[str] = frozenset({"DataItem", "ListItem"})

#: The children of a row that are its cells. `Text` is KeePass 2's shape (one `Text` per column
#: in header order), `DataItem` and `Edit` a grid row's cells.
CELL_TYPES: frozenset[str] = frozenset({"Text", "DataItem", "Edit"})

HEADER_TYPES: frozenset[str] = frozenset({"Header", "HeaderItem"})


class RowError(Exception):
    """The row or the column cannot be addressed at all: the step says something impossible."""


class RowsUnavailable(Exception):
    """The target is not something whose rows playback can address."""


#: Why a `RowFailed` happened, for #63's triage. Plain strings rather than `playback.triage`'s
#: names, because triage imports this module and not the other way round.
ROW_NOT_FOUND = "notFound"
ROW_REFUSED = "refused"


class RowFailed(Exception):
    """`SelectRow` could not select the row, with the reason already worded for the result.

    `kind` says which of the two it was, because they are different findings and #63 must not
    merge them: a row that is **not there** is evidence about recognition, while a row the
    application **refused to select** is evidence about the application's behaviour.
    """

    def __init__(self, message: str, kind: str = ROW_NOT_FOUND) -> None:
        self.kind = kind
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class Address:
    """A `$defs/row`: by position, or by a key cell."""

    index: int | None = None
    value: str | None = None
    column: str | None = None

    def describe(self) -> str:
        """How a message names this row, in the wording of the PR #231 review."""
        if self.index is not None:
            return f"row {self.index}"
        if self.column is not None:
            return f"a row with {show(self.value)} in {show(self.column)}"
        return f"a row with {show(self.value)}"


@dataclass(frozen=True, slots=True)
class Row:
    """One row of the target: what to act on, and its cells in column order."""

    #: Tree position of the element `SelectRow` acts on: the row when there is one, else its
    #: first cell (the ADR's rule for Qt, which has no row element).
    element: int
    #: Tree positions of the row's cells, left to right.
    cells: tuple[int, ...]
    #: Position from the top, counted from 1 -- what `row.index` means and what a message says.
    index: int
    #: Whether `element` is the row itself. False means acting on it selects a *cell*, which
    #: selects the whole row only on a view whose SelectionBehavior is SelectRows.
    is_row: bool


@dataclass(frozen=True, slots=True)
class Grid:
    """The target's rows and columns, from one read."""

    rows: tuple[Row, ...]
    #: Column header texts, in order. Empty when the target reports none (an empty Qt table).
    columns: tuple[str, ...]
    #: `rowCount`: `GridPattern.RowCount` when the target has one -- it counts rows the walk
    #: did not materialise -- else the rows found in the tree.
    count: int


def address(spec: Any) -> Address:
    """Read a `$defs/row`. Raises :class:`RowError` for anything the schema would refuse.

    The schema refuses all of this already, so a request carrying it is a client bug; refusing
    beats guessing, because a row addressed differently from what the step says would act on
    the wrong data and report `passed`.
    """
    if not isinstance(spec, Mapping):
        raise RowError("the step names no row")
    index = spec.get("index")
    value = spec.get("value")
    if index is not None and value is not None:
        raise RowError("a row is addressed by index or by a cell value, not by both")
    if index is not None:
        if not isinstance(index, int) or isinstance(index, bool) or index < 1:
            raise RowError(f"a row index counts from 1, so {index!r} is not one")
        return Address(index=index)
    if not isinstance(value, str) or not value:
        raise RowError(
            "a row is addressed by an index, or by the text of one of its cells"
        )
    column = spec.get("column")
    if column is not None and (not isinstance(column, str) or not column):
        raise RowError("a row's column is the header's text")
    return Address(value=value, column=column)


def of(tree: Tree, index: int, patterns: Patterns = uia_patterns) -> Grid:
    """The target's rows and columns. Raises :class:`RowsUnavailable` when it has no rows.

    "No rows" means the shape is not one this module can address -- a grid whose cells do not
    report their row and column, for instance. An **empty** grid is not that: it has zero rows,
    which is a perfectly good answer to `rowCount` and to `rowExists`.
    """
    element = tree.infos[index]
    control_type = tree.descriptors[index].control_type
    columns = columns_of(tree, index)
    items = _items(tree, index)

    if any(_cells_of(tree, item) for item in items):
        # The item is the row (KeePass 2's ListItems, a WinForms DataGridView row).
        rows = tuple(
            Row(
                element=item,
                cells=tuple(_cells_of(tree, item)),
                index=position + 1,
                is_row=True,
            )
            for position, item in enumerate(items)
        )
    elif items and control_type in GRID_TYPES:
        # A Qt table: no row element, so the cells are grouped by their GridItem row.
        rows = _grouped(tree, items, patterns)
    else:
        # A list of leaf items: each item is a row whose only cell is itself.
        rows = tuple(
            Row(element=item, cells=(item,), index=position + 1, is_row=True)
            for position, item in enumerate(items)
        )
    return Grid(rows=rows, columns=columns, count=_count(element, patterns, len(rows)))


def columns_of(tree: Tree, index: int) -> tuple[str, ...]:
    """The target's column headers, in order.

    The same rule as `server/src/main/java/com/ayna/server/repository/GridColumns.java`, which
    is what filled the dropdown the tester picked the column from (#221). Verified against real
    captures on 2026-11-12: KeePass 2's entry list gives its five `HeaderItem` names, the Qt
    probe table gives `Ad`, `Soyad`, `Şehir` without its `1`/`2`/`3` row headers, and
    HandBrake's queue (a `List` with no `Header`) gives none.
    """
    children = tree.children(index)
    for position in children:
        if tree.descriptors[position].control_type == "Header":
            named = _names(
                tree,
                [
                    child
                    for child in tree.children(position)
                    if tree.descriptors[child].control_type == "HeaderItem"
                ],
            )
            if named:
                return named

    if tree.descriptors[index].control_type not in GRID_TYPES:
        # A List's `Header` child is a container; its own name is no column.
        return ()
    first_cell = next(
        (
            position
            for position in children
            if tree.descriptors[position].control_type in ITEM_TYPES
        ),
        None,
    )
    headers: list[int] = []
    for position in children:
        if position == first_cell:
            break
        if tree.descriptors[position].control_type in HEADER_TYPES and not _left_of(
            tree, position, first_cell
        ):
            headers.append(position)
    return _names(tree, headers)


def column_index(grid: Grid, column: str) -> int | None:
    """Where `column` sits, None when the target reports no columns at all.

    None is the ADR's answer for an empty Qt table, which reports no headers because Qt
    collects them through row 0: a key with a column then matches no row, rather than failing
    on a column the target cannot name. A column that is not among the ones it *does* report is
    a real mistake and raises.
    """
    if not grid.columns:
        return None
    if column not in grid.columns:
        known = ", ".join(show(name) for name in grid.columns)
        raise RowError(f"the target has no column {show(column)}; it has {known}")
    return grid.columns.index(column)


def cell_of(row: Row, column: int | None) -> int | None:
    """The tree position of `row`'s cell in `column`, None when the row has no such cell.

    `column` None means the row's own text, which is what a list item is. Separate from
    :func:`text_at` because **a missing cell is not an empty one**: `expected: ""` is a real
    check ("the Notes column is empty") and reading a cell that is not there as `""` would pass
    it on a row that has no such column at all.
    """
    if column is None:
        return row.cells[0] if row.cells else row.element
    return row.cells[column] if 0 <= column < len(row.cells) else None


def text_at(tree: Tree, position: int, patterns: Patterns = uia_patterns) -> str | None:
    """The text of the cell at `position`, by the schema's one rule for a cell."""
    return displayed_text(tree.descriptors[position], tree.infos[position], patterns)


def find(
    tree: Tree,
    grid: Grid,
    want: Address,
    patterns: Patterns = uia_patterns,
) -> Row | None:
    """The row `want` addresses, or None when the target has no such row.

    By position it is the n-th row as the target shows it *now* -- after its sorting and
    filtering, which is what the schema says and what makes "the first result" mean what a
    tester means. By key cell it is the **first from the top**, the schema's own rule, which is
    why `playback.tree.descendants` walks in pre-order.
    """
    if want.index is not None:
        position = want.index - 1
        return grid.rows[position] if 0 <= position < len(grid.rows) else None
    column = column_index(grid, want.column) if want.column else None
    if want.column and column is None:
        # The target names no columns, so nothing can be matched *in* one.
        return None
    for row in grid.rows:
        if column is not None:
            cell = cell_of(row, column)
            if cell is not None and text_at(tree, cell, patterns) == want.value:
                return row
        elif any(
            text_at(tree, cell, patterns) == want.value
            for cell in (row.cells or (row.element,))
        ):
            return row
    return None


def select(row: Row, tree: Tree, patterns: Patterns = uia_patterns) -> str | None:
    """Select `row`. Returns the pattern that did it, or None when the provider refused.

    `SelectionItem.Select` clears the selection and selects the element, which is what
    "afterwards only that row is selected" means (the ADR's own citation). `Invoke` is not a
    fallback here: invoking a row activates it -- a double-click, opening what it points at --
    and a step that said "select" must not open a window.
    """
    element = tree.infos[row.element]
    item = patterns(element, "SelectionItem")
    if item is not None and _try(lambda: item.Select()):
        return "SelectionItem"
    legacy = patterns(element, "LegacyIAccessible")
    if legacy is not None and _try(lambda: legacy.Select(_SELFLAG_TAKESELECTION)):
        # KeePass 2's list offers only Selection and LegacyIAccessible (measured 2026-11-07),
        # and MSAA's own "take selection" is the same intent, not a click.
        return "LegacyIAccessible"
    return None


#: Above this many rows, `make_current` does not walk down with the arrow key: 500 presses at
#: :data:`KEY_PAUSE_S` is five seconds, and the step reports the row as not current instead.
MAX_KEYED_ROWS = 500

#: The pause between two key presses while moving to a row; pywinauto's own default (50 ms)
#: would make row 100 cost five seconds.
KEY_PAUSE_S = 0.01


class Keyboard:
    """Focus through UI Automation, keys to whatever has the focus. Never coordinates.

    A seam so `make_current` is tested without a desktop; `agent/tests/conftest.py` replaces
    :data:`keyboard` for every test, so no unit test ever presses a real key.
    """

    def focus(self, element: Any) -> bool:
        return _try(lambda: getattr(element, "element", element).SetFocus())

    def send(self, keys: str) -> None:
        from pywinauto import keyboard as pywinauto_keyboard

        pywinauto_keyboard.send_keys(keys, pause=KEY_PAUSE_S)


#: The keyboard `make_current` uses; replaced in tests.
keyboard = Keyboard()


def make_current(
    row: Row,
    grid_index: int,
    tree: Tree,
    patterns: Patterns = uia_patterns,
    keys: Keyboard | None = None,
) -> bool:
    """Make `row` the target's **current** row, not only its selected one (#265).

    On a Qt table, `SelectionItem.Select` (and MSAA's take-focus) changes the selection model
    but not the current index, so an application that acts on `currentRow()` -- the common
    idiom, and the sample app's Open button -- still acts on the old row, while a person's click
    sets both. Measured on the sample app (2026-11-19): Select, SetFocus, both, and
    `accSelect(TAKEFOCUS|TAKESELECTION)` all left "Open" on row 1; only the keyboard moved it.
    So: focus the grid through UI Automation, `Ctrl+Home` to its first row, then `Down` to the
    row -- the keys a person would press, which move the current index *and* the selection.

    Only for a table with no row element (`row.is_row` False, Qt's shape): where the provider
    has real rows, `Select` is its own selection and keys are not needed. Returns True when the
    row is still the selected one afterwards (the keys landed where they should), False when
    it could not be done or the keys went elsewhere -- then the step's own selection is put
    back, and the caller says so in the step's message.
    """
    if row.is_row:
        return True
    keys = keyboard if keys is None else keys
    if row.index > MAX_KEYED_ROWS or not keys.focus(tree.infos[grid_index]):
        return False
    keys.send("^{HOME}" + "{DOWN}" * (row.index - 1))
    item = patterns(tree.infos[row.element], "SelectionItem")
    if item is None:
        return False
    if _read(lambda: item.CurrentIsSelected):
        return True
    _try(lambda: item.Select())
    return False


def whole_row_selected(
    row: Row, tree: Tree, patterns: Patterns = uia_patterns
) -> bool | None:
    """Whether selecting `row.element` selected the whole row. None when it cannot be told.

    Asked only of a grid whose rows are cells (Qt): the ADR says a view that selects cells
    rather than rows leaves one cell selected, and that playback must report what it selected
    instead of claiming the row. One pattern read -- the row's last cell -- rather than one per
    cell, because that is enough to tell the two apart.
    """
    if row.is_row or len(row.cells) < 2:
        return True
    item = patterns(tree.infos[row.cells[-1]], "SelectionItem")
    if item is None:
        return None
    state = _read(lambda: item.CurrentIsSelected)
    return None if state is None else bool(state)


# --- the messages, worded for the tester who reads them ------------------------------------


def not_found(name: str, want: Address, grid: Grid, timeout_ms: int) -> str:
    """`SelectRow`: the row never appeared."""
    after = f" after {timeout_ms} ms" if timeout_ms else ""
    return f"{name}: {want.describe()} was not found{after}; {_rows(grid.count)}"


def refused(name: str, want: Address) -> str:
    """`SelectRow`: the row is there and the application would not select it."""
    return (
        f"{name}: {want.describe()} is there, but the application refused to select it "
        f"(SelectionItem and LegacyIAccessible were tried)"
    )


def selected_a_cell(name: str, want: Address) -> str:
    """`SelectRow` on a view that selects cells: what it did, rather than what it was asked.

    A passing step with a message: the ADR says playback "reports what it selected instead of
    claiming the row", and a failure would be wrong -- the step did select, and no pilot app is
    ours to reconfigure.
    """
    return (
        f"{name}: the target selects cells rather than rows, so the first cell of "
        f"{want.describe()} is selected"
    )


def not_current(name: str, want: Address) -> str:
    """`SelectRow` selected the row but could not make it the current one (#265).

    A passing step with a message, like :func:`selected_a_cell`: the row *is* selected, which
    is what the step asked, but an application acting on its current row will not see it.
    """
    return (
        f"{name}: {want.describe()} is selected, but playback could not make it the "
        "current row, so an action on 'the current row' may still use another one"
    )


def describe_exists(
    name: str, want: Address, expected: bool, grid: Grid, found: Row | None
) -> str:
    """`rowExists`, in the wording promised in the PR #231 review.

    `main.customerGrid: a row with "Yılmaz" in "Soyad" should exist, none does`. By position the
    second half is the count instead, because "row 7 should exist, none does" says nothing a
    tester can act on while "the target has 3 rows" says everything.
    """
    if expected:
        missing = _rows(grid.count) if want.index is not None else "none does"
        return f"{name}: {want.describe()} should exist, {missing}"
    if want.index is not None:
        return f"{name}: {want.describe()} should not exist, {_rows(grid.count)}"
    return f"{name}: {want.describe()} should not exist, row {found.index} is one"


def describe_cell(
    name: str,
    want: Address,
    column: str,
    operator: str,
    expected: Any,
    actual: Any,
) -> str:
    """`cell`: which cell, what it should be, what it is."""
    return (
        f"{name}: the {show(column)} cell of {want.describe()} {says(operator)} "
        f"{show(expected)}, it is {show(actual)}"
    )


def unreadable_cell(name: str, want: Address, column: str, grid: Grid) -> str:
    """`cell` on a row or a column that is not there: the check has no answer at all."""
    return (
        f"{name}: the {show(column)} cell of {want.describe()} cannot be read; "
        f"{_rows(grid.count)}"
    )


def _rows(count: int) -> str:
    return "the target has 1 row" if count == 1 else f"the target has {count} rows"


# --- reading the tree ----------------------------------------------------------------------

#: MSAA's `SELFLAG_TAKEFOCUS | SELFLAG_TAKESELECTION`, the "select only this" of
#: `LegacyIAccessible.Select` -- the same intent as `SelectionItem.Select`.
_SELFLAG_TAKESELECTION = 0x3


def _items(tree: Tree, index: int) -> list[int]:
    """The target's items, in tree order, without descending into one.

    Not every descendant: a row's cells are items too on some frameworks, and counting them as
    rows would report a three-row grid as nine. The walk stops at the first item on each branch
    and so steps over the `Header` subtree as well.
    """
    out: list[int] = []
    stack = list(reversed(tree.children(index)))
    while stack:
        position = stack.pop()
        if tree.descriptors[position].control_type in ITEM_TYPES:
            out.append(position)
            continue
        stack.extend(reversed(tree.children(position)))
    return out


def _cells_of(tree: Tree, item: int) -> list[int]:
    """`item`'s cells: its direct children that carry text, in order."""
    return [
        child
        for child in tree.children(item)
        if tree.descriptors[child].control_type in CELL_TYPES
    ]


def _grouped(tree: Tree, items: Sequence[int], patterns: Patterns) -> tuple[Row, ...]:
    """Cells into rows, by `GridItemPattern`. For a grid with no row element (Qt)."""
    found: dict[int, list[tuple[int, int]]] = {}
    for item in items:
        at = _cell_at(tree.infos[item], patterns)
        if at is None:
            continue
        row, column = at
        found.setdefault(row, []).append((column, item))
    if not found:
        raise RowsUnavailable(
            "the grid has no row elements and its cells do not report their row and column, "
            "so playback cannot tell which cells make up a row"
        )
    rows = []
    for position, row in enumerate(sorted(found)):
        cells = tuple(item for _column, item in sorted(found[row]))
        rows.append(
            Row(element=cells[0], cells=cells, index=position + 1, is_row=False)
        )
    return tuple(rows)


def _cell_at(element: Any, patterns: Patterns) -> tuple[int, int] | None:
    """A cell's `(row, column)`, 0-based as `GridItemPattern` reports them."""
    pattern = patterns(element, "GridItem")
    if pattern is None:
        return None
    row = _read(lambda: pattern.CurrentRow)
    column = _read(lambda: pattern.CurrentColumn)
    if row is None or column is None:
        return None
    return int(row), int(column)


def _count(element: Any, patterns: Patterns, found: int) -> int:
    """`rowCount`: the Grid pattern's count when there is one, else what the tree holds.

    The pattern is preferred because it is cheap and because it counts rows a virtualised grid
    has not materialised -- which the walk cannot see at all. The two can therefore disagree,
    and `rowCount` is then the honest number while `rowExists` is about what is on screen.
    """
    grid = patterns(element, "Grid")
    if grid is not None:
        count = _read(lambda: grid.CurrentRowCount)
        if count is not None:
            return int(count)
    return found


def _names(tree: Tree, positions: Sequence[int]) -> tuple[str, ...]:
    """The names of `positions`, blanks left out and each name once, in order."""
    out: list[str] = []
    for position in positions:
        name = tree.descriptors[position].name
        if name and name not in out:
            out.append(name)
    return tuple(out)


def _left_of(tree: Tree, position: int, cell: int | None) -> bool:
    """True when `position` ends at or before the first cell's left edge: a Qt row header."""
    if cell is None:
        return False
    bounds = tree.descriptors[position].bounds
    first = tree.descriptors[cell].bounds
    if bounds is None or first is None:
        return False
    return bounds[2] <= first[0]


def _read(call: Any) -> Any:
    try:
        return call()
    except Exception:  # noqa: BLE001 - a provider that does not answer means "no value"
        return None


def _try(call: Any) -> bool:
    try:
        call()
    except Exception:  # noqa: BLE001 - COMError and pywinauto both land here; same meaning
        return False
    return True
