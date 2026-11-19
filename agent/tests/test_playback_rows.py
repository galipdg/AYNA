"""Tests for the rows of a grid or a list (#40): the three shapes, and how a row is addressed.

What is worth testing here rather than through the runner:

- **the three shapes**, because the rule is structural and each one came from a measurement:
  the item is the row (KeePass 2), the items are the cells and only `GridItemPattern` says
  which row they belong to (Qt's table has no row element), the item is a one-cell row (a
  `QListWidget`);
- **the columns**, which must come out exactly as `server/.../GridColumns.java` produces them,
  Qt's row header dropped and all — the dropdown the tester picked the column from is filled
  from that rule, and a disagreement would read the cell next to the one they meant;
- **addressing**: by position counted from 1, or the first row from the top whose cell matches;
- **the messages**, including the two whose wording was promised in the PR #231 review.

Everything is injected, so none of it needs Windows (`agent/AGENTS.md`).
"""

from __future__ import annotations

import grids
import pytest

from ayna_agent.playback import rows, tree
from ayna_agent.playback.rows import Address

TARGET = 1  # every window in `grids` has its grid or list right under the window


def grid_of(content, patterns=None):
    """`(the Grid of the target, the tree it came from)`."""
    read = tree.of(*grids.read(content))
    return rows.of(read, TARGET, patterns or (lambda e, n: None)), read


# --- the three shapes ----------------------------------------------------------------------


def test_a_keepass_list_item_is_the_row_and_its_text_children_are_the_cells():
    """Measured on 2026-11-07: each `ListItem` has one `Text` child per column in header
    order, and the item's own Name is only the Title column."""
    grid, read = grid_of(grids.entry_list())
    assert [row.index for row in grid.rows] == [1, 2]
    assert all(row.is_row for row in grid.rows)
    assert [rows.text_at(read, cell) for cell in grid.rows[0].cells] == [
        "Gmail",
        "ayna@example.com",
        "******",
    ]


def test_a_qt_table_has_no_row_element_so_its_cells_are_grouped_by_griditem():
    """`GridItemPattern` row and column are 0-based while `index` counts from 1."""
    grid, read = grid_of(grids.customer_grid(), grids.Patterns())
    assert [row.index for row in grid.rows] == [1, 2]
    assert not any(row.is_row for row in grid.rows)
    assert [rows.text_at(read, cell) for cell in grid.rows[1].cells] == [
        "Mehmet",
        "Demir",
        "İzmir",
    ]
    assert read.infos[grid.rows[1].element] == "grid-cell:1,0", (
        "SelectRow acts on the row's first cell, since there is no row"
    )


def test_a_cell_is_not_counted_as_a_row():
    """The Qt table's cells are items too. Counting them as rows would report a two-row grid
    as six, and `rowCount` is a number a tester reads straight off the screen."""
    grid, _read = grid_of(grids.customer_grid(), grids.Patterns())
    assert len(grid.rows) == 2


def test_a_list_of_leaf_items_is_a_grid_of_one_cell_rows():
    grid, read = grid_of(grids.city_list())
    assert [rows.text_at(read, row.cells[0]) for row in grid.rows] == [
        "Adana",
        "Ankara",
    ]
    assert all(row.is_row for row in grid.rows)


def test_an_empty_grid_has_no_rows_rather_than_no_answer():
    """Zero rows is a perfectly good answer to `rowCount` and to `rowExists`."""
    grid, _read = grid_of(grids.customer_grid(()), grids.Patterns())
    assert grid.rows == ()
    assert grid.count == 0


def test_a_grid_whose_cells_do_not_report_their_position_says_so():
    """Without `GridItem` there is no way to tell which cells make up a row, and guessing from
    the child order would be a silent wrong answer on a sorted or virtualised grid."""
    with pytest.raises(rows.RowsUnavailable):
        grid_of(grids.customer_grid(), lambda e, n: None)


# --- rowCount ------------------------------------------------------------------------------


def test_the_grid_pattern_count_wins_over_the_rows_in_the_tree():
    """A virtualised grid materialises only what is on screen, so the pattern's count is the
    honest number for `rowCount` even when the walk saw fewer rows."""
    grid, _read = grid_of(grids.customer_grid(), grids.Patterns(row_count=120))
    assert grid.count == 120
    assert len(grid.rows) == 2


def test_a_target_without_the_grid_pattern_counts_the_rows_it_has():
    grid, _read = grid_of(grids.entry_list())
    assert grid.count == 2


# --- the columns, by the server's own rule -------------------------------------------------


def test_a_header_child_gives_its_header_item_names_in_order():
    """KeePass 2's list, which has no Table pattern at all."""
    grid, _read = grid_of(grids.entry_list())
    assert grid.columns == grids.ENTRY_HEADERS


def test_a_qt_table_drops_the_row_header_that_lies_left_of_the_first_cell():
    """The #221 measurement, to the pixel: the row header `1` ends at 666 and the first cell
    starts at 667, so `Ad`, `Soyad`, `Şehir` are the columns and `1`, `2` are not."""
    grid, _read = grid_of(grids.customer_grid(), grids.Patterns())
    assert grid.columns == grids.CUSTOMER_COLUMNS


def test_a_list_of_leaf_items_reports_no_columns():
    """HandBrake's queue is such a list, and a `List`'s `Header` child is a container whose own
    name is no column."""
    grid, _read = grid_of(grids.city_list())
    assert grid.columns == ()


def test_an_empty_grid_still_reports_its_columns_because_they_are_read_from_the_tree():
    """Better than the ADR expected, and worth knowing: it reasoned from
    `TablePattern.GetColumnHeaders`, which Qt collects through row 0 and so reports nothing for
    an empty table. Reading the captured `HeaderItem`s instead (the server's rule, #221) still
    names the columns, so "a key with a column matches no row" happens only on a target with no
    header elements at all -- HandBrake's queue, not an empty Qt table.
    """
    grid, _read = grid_of(grids.customer_grid(()), grids.Patterns())
    assert grid.columns == grids.CUSTOMER_COLUMNS


def test_a_column_that_is_not_one_of_the_target_s_is_a_mistake_with_the_names_listed():
    grid, _read = grid_of(grids.entry_list())
    with pytest.raises(rows.RowError) as caught:
        rows.column_index(grid, "Soyad")
    assert '"Title", "User Name", "Password"' in str(caught.value)


def test_a_target_that_names_no_columns_at_all_is_not_a_mistake():
    """The ADR settles this: a key with a column then matches no row, rather than failing on a
    column the target cannot name."""
    grid, read = grid_of(grids.city_list())
    assert rows.column_index(grid, "Şehir") is None
    assert rows.find(read, grid, Address(value="Ankara", column="Şehir")) is None


# --- addressing a row ----------------------------------------------------------------------


def test_a_row_index_counts_from_1_as_the_target_shows_it_now():
    grid, read = grid_of(grids.entry_list())
    assert rows.find(read, grid, Address(index=2)).index == 2
    assert rows.find(read, grid, Address(index=3)) is None


def test_a_key_cell_finds_the_first_row_from_the_top():
    entries = (("Gmail", "hasan", "x"), ("GitHub", "hasan", "y"))
    grid, read = grid_of(grids.entry_list(entries))
    found = rows.find(read, grid, Address(value="hasan", column="User Name"))
    assert found.index == 1


def test_a_key_cell_without_a_column_matches_any_cell_of_the_row():
    """So "the Yılmaz row" works without knowing the column names, which is what the NL
    assistant can produce."""
    grid, read = grid_of(grids.customer_grid(), grids.Patterns())
    assert rows.find(read, grid, Address(value="İzmir")).index == 2


def test_a_key_cell_in_a_column_does_not_match_the_same_text_elsewhere():
    """The column is the point of giving one: a surname that is also a city must not match."""
    customers = (("Ayşe", "Ankara", "Bursa"), ("Mehmet", "Demir", "Ankara"))
    grid, read = grid_of(grids.customer_grid(customers), grids.Patterns())
    assert rows.find(read, grid, Address(value="Ankara", column="Şehir")).index == 2


def test_a_cell_the_row_does_not_have_is_not_an_empty_cell():
    """`expected: ""` is a real check ("the Notes column is empty"), so reading a cell that is
    not there as `""` would pass it on a row that has no such column."""
    short = (("Gmail", "hasan"),)
    grid, _read = grid_of(grids.entry_list(short))
    assert rows.cell_of(grid.rows[0], 2) is None
    assert rows.cell_of(grid.rows[0], 1) is not None


# --- selecting -----------------------------------------------------------------------------


def test_select_uses_selection_item_which_leaves_only_that_row_selected():
    grid, read = grid_of(grids.entry_list())
    patterns = grids.Patterns()
    assert rows.select(grid.rows[1], read, patterns) == "SelectionItem"
    assert patterns.selected == ["row:1"]


def test_select_falls_back_to_the_msaa_take_selection_not_to_invoke():
    """KeePass 2's list offers only Selection and LegacyIAccessible (measured 2026-11-07), and
    invoking a row would *activate* it -- opening what it points at, which "select" never
    means."""
    grid, read = grid_of(grids.entry_list())
    patterns = grids.Patterns(selection_item=False, legacy=True)
    assert rows.select(grid.rows[0], read, patterns) == "LegacyIAccessible"
    assert patterns.selected == ["row:0"]


def test_select_answers_none_when_the_provider_refuses():
    grid, read = grid_of(grids.entry_list())
    assert rows.select(grid.rows[0], read, grids.Patterns(refuses=True)) is None


def test_a_view_that_selects_rows_selects_the_whole_row_from_its_first_cell():
    """Measured on `QTableWidget` with SelectionBehavior = SelectRows."""
    patterns = grids.Patterns(selects_rows=True)
    grid, read = grid_of(grids.customer_grid(), patterns)
    rows.select(grid.rows[0], read, patterns)
    assert rows.whole_row_selected(grid.rows[0], read, patterns) is True


def test_a_view_that_selects_cells_leaves_one_cell_selected_and_that_is_detectable():
    """The ADR's open case: playback reports what it selected instead of claiming the row."""
    patterns = grids.Patterns(selects_rows=False)
    grid, read = grid_of(grids.customer_grid(), patterns)
    rows.select(grid.rows[0], read, patterns)
    assert rows.whole_row_selected(grid.rows[0], read, patterns) is False


def test_a_real_row_is_never_asked_whether_the_whole_row_is_selected():
    """It is the row; there is nothing else it could have selected."""
    patterns = grids.Patterns()
    grid, read = grid_of(grids.entry_list(), patterns)
    assert rows.whole_row_selected(grid.rows[0], read, patterns) is True


def test_a_cell_that_cannot_report_its_selection_answers_none_rather_than_false():
    patterns = grids.Patterns(selection_item=False)
    grid, read = grid_of(grids.customer_grid(), grids.Patterns())
    assert rows.whole_row_selected(grid.rows[0], read, patterns) is None


# --- reading a `$defs/row` -----------------------------------------------------------------


def test_a_row_is_read_as_a_position_or_as_a_key_cell():
    assert rows.address({"index": 3}) == Address(index=3)
    assert rows.address({"value": "Yılmaz"}) == Address(value="Yılmaz")
    assert rows.address({"value": "Yılmaz", "column": "Soyad"}) == Address(
        value="Yılmaz", column="Soyad"
    )


@pytest.mark.parametrize(
    "spec",
    [
        None,
        {},
        {"index": 0},
        {"index": True},
        {"index": "2"},
        {"value": ""},
        {"index": 1, "value": "Yılmaz"},
        {"value": "Yılmaz", "column": ""},
    ],
)
def test_a_row_the_schema_would_refuse_is_refused_here_too(spec):
    """The schema catches all of these, so a request carrying one is a client bug -- and
    guessing would address a different row and report `passed`."""
    with pytest.raises(rows.RowError):
        rows.address(spec)


# --- the messages --------------------------------------------------------------------------


def test_a_row_names_itself_the_way_the_review_promised():
    assert Address(index=3).describe() == "row 3"
    assert (
        Address(value="Yılmaz", column="Soyad").describe()
        == 'a row with "Yılmaz" in "Soyad"'
    )
    assert Address(value="Yılmaz").describe() == 'a row with "Yılmaz"'


def test_row_exists_is_worded_exactly_as_promised_on_pr_231():
    grid, _read = grid_of(grids.customer_grid(), grids.Patterns())
    message = rows.describe_exists(
        "main.customerGrid", Address(value="Yılmaz", column="Soyad"), True, grid, None
    )
    assert message == (
        'main.customerGrid: a row with "Yılmaz" in "Soyad" should exist, none does'
    )


def test_a_missing_row_by_position_says_how_many_rows_there_are_instead():
    """ "Row 7 should exist, none does" says nothing a tester can act on."""
    grid, _read = grid_of(grids.customer_grid(), grids.Patterns())
    message = rows.describe_exists("main.grid", Address(index=7), True, grid, None)
    assert message == "main.grid: row 7 should exist, the target has 2 rows"


def test_a_row_that_should_not_be_there_names_the_row_that_is():
    grid, read = grid_of(grids.customer_grid(), grids.Patterns())
    found = rows.find(read, grid, Address(value="Demir", column="Soyad"))
    message = rows.describe_exists(
        "main.grid", Address(value="Demir", column="Soyad"), False, grid, found
    )
    assert message == (
        'main.grid: a row with "Demir" in "Soyad" should not exist, row 2 is one'
    )


def test_a_cell_check_names_the_cell_what_it_should_be_and_what_it_is():
    message = rows.describe_cell(
        "main.grid", Address(index=1), "Soyad", "equals", "Yılmaz", "Demir"
    )
    assert message == (
        'main.grid: the "Soyad" cell of row 1 should be "Yılmaz", it is "Demir"'
    )


def test_a_cell_that_is_not_there_cannot_be_read_rather_than_being_wrong():
    grid, _read = grid_of(grids.customer_grid(), grids.Patterns())
    message = rows.unreadable_cell("main.grid", Address(index=9), "Soyad", grid)
    assert message == (
        'main.grid: the "Soyad" cell of row 9 cannot be read; the target has 2 rows'
    )


def test_a_row_that_never_appeared_says_how_long_it_waited_and_what_is_there():
    grid, _read = grid_of(grids.customer_grid(), grids.Patterns(row_count=1))
    message = rows.not_found("main.grid", Address(index=4), grid, 5000)
    assert message == (
        "main.grid: row 4 was not found after 5000 ms; the target has 1 row"
    )


def test_a_refusal_to_select_blames_the_application_not_the_test():
    message = rows.refused("main.grid", Address(index=2))
    assert "the application refused to select it" in message
    assert message.startswith("main.grid: row 2 is there, ")


def test_selecting_a_cell_instead_of_a_row_is_reported_as_what_it_did():
    message = rows.selected_a_cell("main.grid", Address(index=2))
    assert message == (
        "main.grid: the target selects cells rather than rows, so the first cell of row 2 "
        "is selected"
    )


# --- making the selected row the current one (#265) ----------------------------------------


class Keys:
    """A keyboard that may refuse the focus, or 'land' the keys on another row."""

    def __init__(self, *, focus: bool = True, then=None) -> None:
        self.allow = focus
        self.then = then
        self.focused: list[str] = []
        self.sent: list[str] = []

    def focus(self, element) -> bool:
        self.focused.append(element)
        return self.allow

    def send(self, keys: str) -> None:
        self.sent.append(keys)
        if self.then is not None:
            self.then()


def selected_qt_row(index: int):
    patterns = grids.Patterns()
    grid, read = grid_of(grids.customer_grid(), patterns)
    row = grid.rows[index - 1]
    assert rows.select(row, read, patterns) == "SelectionItem"
    return row, read, patterns


def test_a_qt_row_is_made_current_with_the_keys_a_person_would_press():
    """Ctrl+Home to the first row, then Down to the row: moves Qt's current index, which
    SelectionItem.Select does not (measured on the sample app, 2026-11-19)."""
    row, read, patterns = selected_qt_row(2)
    keys = Keys()
    assert rows.make_current(row, TARGET, read, patterns, keys) is True
    assert keys.focused == [read.infos[TARGET]], "the grid takes the focus, not a cell"
    assert keys.sent == ["^{HOME}{DOWN}"]


def test_the_first_row_needs_only_ctrl_home():
    row, read, patterns = selected_qt_row(1)
    keys = Keys()
    assert rows.make_current(row, TARGET, read, patterns, keys) is True
    assert keys.sent == ["^{HOME}"]


def test_a_row_the_provider_has_as_an_element_needs_no_keys():
    """KeePass 2's ListItems and a WinForms row are rows: their Select is the selection."""
    patterns = grids.Patterns(legacy=True, selection_item=False)
    grid, read = grid_of(grids.entry_list(), patterns)
    keys = Keys()
    assert rows.make_current(grid.rows[0], TARGET, read, patterns, keys) is True
    assert keys.focused == [] and keys.sent == []


def test_a_grid_that_will_not_take_the_focus_gets_no_keys():
    row, read, patterns = selected_qt_row(2)
    keys = Keys(focus=False)
    assert rows.make_current(row, TARGET, read, patterns, keys) is False
    assert keys.sent == []


def test_a_row_too_far_down_is_not_walked_to(monkeypatch):
    monkeypatch.setattr(rows, "MAX_KEYED_ROWS", 1)
    row, read, patterns = selected_qt_row(2)
    keys = Keys()
    assert rows.make_current(row, TARGET, read, patterns, keys) is False
    assert keys.focused == [] and keys.sent == []


def test_keys_that_land_on_another_row_are_reported_and_the_selection_put_back():
    row, read, patterns = selected_qt_row(2)
    other = read.infos[grid_of(grids.customer_grid(), patterns)[0].rows[0].element]
    keys = Keys(
        then=lambda: (patterns.selection.clear(), patterns.selection.add(other))
    )
    assert rows.make_current(row, TARGET, read, patterns, keys) is False
    assert patterns.selected[-1] == read.infos[row.element], (
        "the step's row selected again"
    )


def test_the_not_current_message_says_what_was_done_and_what_was_not():
    message = rows.not_current("main.customerGrid", Address(index=2))
    assert message.startswith("main.customerGrid: row 2 is selected")
    assert "could not make it the current row" in message
