"""The three row shapes the step schema v0.2 ADR measured, as windows playback can read (#40).

Not a test module: `test_playback_rows.py` and `test_playback_runner.py` both build their
windows from here, so the shapes stay **one** description of what was measured rather than two
that can drift.

* :func:`entry_list` — KeePass 2's entry list: a `List` with a `Header` of named `HeaderItem`s
  and one `ListItem` per entry, each carrying one `Text` child per column in header order. The
  item *is* the row.
* :func:`customer_grid` — the Qt probe table: a `Table` with no row element at all, its
  `DataItem` cells directly under it, their row and column only in `GridItemPattern`, and a
  row-header `HeaderItem` that lies wholly left of the first cell (the one the column rule has
  to drop; measured on 2026-11-12 at one pixel of margin).
* :func:`city_list` — a `QListWidget`: leaf `ListItem`s, each a one-cell row.

Every node carries an `info` string naming the live element it stands for (`table`,
`grid-cell:0,1`, `row:2`, `text:2,0`), so a test asserts on *what* was acted on and the pattern
fake can answer `GridItem` without a second table of positions.
"""

from __future__ import annotations

from typing import Any

#: KeePass 2's entry list, as the 2026-11-07 Windows session measured it.
ENTRY_LIST = "KeePass.main.entryList"
ENTRY_HEADERS = ("Title", "User Name", "Password")
ENTRIES = (
    ("Gmail", "ayna@example.com", "******"),
    ("GitHub", "hasan", "******"),
)

#: The Qt probe table (#221's step 6).
CUSTOMER_GRID = "QApplication.listWindow.customerGrid"
CUSTOMER_COLUMNS = ("Ad", "Soyad", "Şehir")
CUSTOMERS = (
    ("Ayşe", "Yılmaz", "Ankara"),
    ("Mehmet", "Demir", "İzmir"),
)

#: A QListWidget.
CITY_LIST = "QApplication.listWindow.cityList"
CITIES = ("Adana", "Ankara")


def node(
    id_: int,
    parent: int | None,
    control_type: str,
    name: str | None = None,
    info: str = "",
    **extra: Any,
) -> dict:
    return {
        "id": id_,
        "parent": parent,
        "control_type": control_type,
        "name": name,
        "info": info,
        "enabled": True,
        "offscreen": False,
        **extra,
    }


def read(content: list[dict]) -> tuple[list[dict], list[str]]:
    """`(nodes, infos)` as `recognition.uia.read_tree` returns them."""
    return content, [item["info"] for item in content]


def entry_list(entries: tuple[tuple[str, ...], ...] = ENTRIES) -> list[dict]:
    """KeePass 2's shape: the item is the row, its `Text` children are the cells."""
    content = [
        node(0, None, "Window", "AYNA Demo - KeePass", "window", class_name="WinForms"),
        node(1, 0, "List", "Entries", "list", automation_id=ENTRY_LIST),
        node(2, 1, "Header", None, "header"),
    ]
    for position, title in enumerate(ENTRY_HEADERS):
        content.append(node(10 + position, 2, "HeaderItem", title, f"header:{title}"))
    for row, entry in enumerate(entries):
        content.append(node(100 + row, 1, "ListItem", entry[0], f"row:{row}"))
        for column, text in enumerate(entry):
            content.append(
                node(
                    200 + row * 10 + column,
                    100 + row,
                    "Text",
                    text,
                    f"text:{row},{column}",
                )
            )
    return content


def customer_grid(customers: tuple[tuple[str, ...], ...] = CUSTOMERS) -> list[dict]:
    """The Qt table's shape: no row element, the cells grouped by their GridItem row.

    The bounds are the measured ones in spirit: the column headers start at the first cell's
    left edge (667) and the row header ends one pixel before it (666), which is exactly what
    the column rule has to notice.
    """
    content = [
        node(
            0, None, "Window", "AYNA Grid Probe", "window", class_name="GridProbeWindow"
        ),
        node(
            1,
            0,
            "Table",
            "Müşteriler",
            "table",
            automation_id=CUSTOMER_GRID,
            bounds=[600, 280, 900, 400],
        ),
    ]
    for column, title in enumerate(CUSTOMER_COLUMNS):
        content.append(
            node(
                10 + column,
                1,
                "HeaderItem",
                title,
                f"header:{title}",
                bounds=[667 + 60 * column, 280, 727 + 60 * column, 316],
            )
        )
    for row in range(len(customers)):
        # Qt's vertical header: a HeaderItem that ends one pixel left of the first cell.
        content.append(
            node(
                20 + row,
                1,
                "HeaderItem",
                str(row + 1),
                f"row-header:{row}",
                bounds=[648, 316 + 37 * row, 666, 353 + 37 * row],
            )
        )
    for row, customer in enumerate(customers):
        for column, text in enumerate(customer):
            content.append(
                node(
                    100 + row * 10 + column,
                    1,
                    "DataItem",
                    text,
                    f"grid-cell:{row},{column}",
                    bounds=[
                        667 + 60 * column,
                        316 + 37 * row,
                        727 + 60 * column,
                        353 + 37 * row,
                    ],
                )
            )
    return content


def city_list(cities: tuple[str, ...] = CITIES) -> list[dict]:
    """A QListWidget: leaf items, each a one-cell row."""
    content = [
        node(0, None, "Window", "AYNA Trial - Liste", "window"),
        node(1, 0, "List", "Şehirler", "list", automation_id=CITY_LIST),
    ]
    for row, city in enumerate(cities):
        content.append(node(100 + row, 1, "ListItem", city, f"row:{row}"))
    return content


class Reader:
    """A window read as often as playback asks, counting the reads."""

    def __init__(self, content: list[dict]) -> None:
        self.content = content
        self.reads = 0
        self.gone = False

    def read_tree(self) -> tuple[list[dict], list[str]]:
        self.reads += 1
        if self.gone:
            return [], []
        return read(self.content)


class Patterns:
    """Patterns for the shapes above, driven by the `info` strings.

    * `Grid` on the table when `row_count` is given — so a test can make the pattern's count
      disagree with the tree, which is what a virtualised grid does;
    * `GridItem` on every `grid-cell:<row>,<column>`;
    * `SelectionItem` on cells and rows: `Select()` records what was selected, and
      `selects_rows` decides whether selecting a cell selects its whole row (a view whose
      SelectionBehavior is SelectRows) or only that cell;
    * `LegacyIAccessible.Select` when `legacy` — KeePass 2's list offers nothing else;
    * never `Value`: Qt cells answer it with the empty string and KeePass's do not have it, so
      the text comes from the Name either way (measured).
    """

    def __init__(
        self,
        *,
        row_count: int | None = None,
        columns: int = 3,
        selects_rows: bool = True,
        refuses: bool = False,
        legacy: bool = False,
        selection_item: bool = True,
    ) -> None:
        self.row_count = row_count
        self.columns = columns
        self.selects_rows = selects_rows
        self.refuses = refuses
        self.legacy = legacy
        self.selection_item = selection_item
        #: What `Select()` was called on, in order.
        self.selected: list[str] = []
        #: What reads as selected now.
        self.selection: set[str] = set()

    def __call__(self, element: str, name: str) -> object | None:
        recorder = self
        if name == "Grid" and element == "table" and self.row_count is not None:

            class G:
                CurrentRowCount = recorder.row_count

            return G()
        if name == "GridItem" and element.startswith("grid-cell:"):
            row, column = (int(part) for part in element.split(":")[1].split(","))

            class I:
                CurrentRow = row
                CurrentColumn = column

            return I()
        if (
            name == "SelectionItem"
            and self.selection_item
            and self._selectable(element)
        ):

            class S:
                @property
                def CurrentIsSelected(self) -> bool:
                    return element in recorder.selection

                def Select(self) -> None:
                    recorder._select(element)

            return S()
        if name == "LegacyIAccessible" and self.legacy and self._selectable(element):

            class L:
                def Select(self, flags: int) -> None:
                    recorder._select(element)

            return L()
        return None

    def _selectable(self, element: str) -> bool:
        return element.startswith(("grid-cell:", "row:"))

    def _select(self, element: str) -> None:
        if self.refuses:
            raise OSError("the provider leaves the selection unchanged")
        self.selected.append(element)
        self.selection.clear()
        if element.startswith("grid-cell:") and self.selects_rows:
            row = element.split(":")[1].split(",")[0]
            self.selection.update(f"grid-cell:{row},{c}" for c in range(self.columns))
        else:
            self.selection.add(element)
