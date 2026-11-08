# What UI Automation reports for a grid and for a list

Measurements behind step schema v0.2 (#147, PR #150) and its ADR
`2026-10-28-step-schema-v0-2-rows`: the `SelectRow` keyword and the `cell` / `rowExists` /
`rowCount` checks, and the rule for where a cell's text lives.

Script: [`grid_probe.py`](grid_probe.py), with [`grid_probe_app.py`](grid_probe_app.py) as the Qt
target. Both runs below are from this machine; re-run them with

```
python grid_probe.py qt
python grid_probe.py handle <handle> --automation-id m_lvEntries
```

**Environment.** Windows 11 Pro 26300, one display at 120 DPI (125 %), Python 3.13.0,
pywinauto 0.6.9, PySide6 6.12.0, KeePass 2 (portable) from `C:\ayna-pilots\keepass2\` with the demo
database `ayna-demo.kdbx`. The Qt run is 2026-10-29, repeated 2026-11-07 through the committed
script with the same results; the KeePass 2 run is 2026-11-07.

For the KeePass 2 handle, `kp_state.py main` prints it after opening the database.

## The rule under test

ADR `2026-10-28-step-schema-v0-2-rows`, `$defs/row`:

> A cell's text is its ValuePattern value when that value is non-empty, else its UI Automation
> Name.

The order matters only where both are non-empty, so the question for each framework is which of the
two is populated.

## Qt — `QTableWidget` and `QListWidget`

```
QTableWidget  id=QApplication.GridProbeWindow.central.customerGrid  controlType=Table
  patterns: Grid, Table, Selection, Value, LegacyIAccessible, Invoke
  RowCount=3  ColumnCount=3                     (3 data rows + 1 header row)
  ColumnHeaders: ['Ad', 'Soyad', 'Şehir']
  RowHeaders:    ['1', '2', '3']                (the vertical header, not data)

  16 ControlView children, flat: 1 Pane, the 3 column Headers, then per row a
  Header named '1'/'2'/'3' followed by that row's 3 DataItems. No row element.
    DataItem Name='Ayşe'   Value=''  -> the rule reads 'Ayşe'
    DataItem Name='Yılmaz' Value=''  -> the rule reads 'Yılmaz'
  Grid.GetItem(0,0) -> 'Ayşe'   gridItem=(row=0,col=0)
  Grid.GetItem(1,2) -> 'İstanbul' gridItem=(row=1,col=2)

  SelectRow probe: SelectionItem.Select() on row 1, column 0
    row 0: IsSelected per cell = [False, False, False]
    row 1: IsSelected per cell = [True, True, True]
    container Selection: 3 selected ['Mehmet', 'Demir', 'İstanbul']
    CanSelectMultiple=0  IsSelectionRequired=1

QListWidget  id=QApplication.GridProbeWindow.central.cityList  controlType=List
  patterns: Selection, Value, LegacyIAccessible, Invoke
  Grid pattern: NO     Table pattern: NO
  4 ListItem children in insertion order: Ankara, İstanbul, İzmir, Bursa
```

1. **A Qt cell's text is in `Name`; its ValuePattern exists and is empty.** Every one of the nine
   cells reports `Value=''`. So a rule that preferred ValuePattern *because the pattern is present*
   would read every Qt cell as the empty string. The ADR's non-empty-first wording handles this
   correctly.
2. **`GridPattern.RowCount` excludes the header row** — 3 for 3 data rows — so `rowCount` maps
   straight onto it.
3. **`GridItemPattern` row and column are 0-based**, while the schema's `row.index` counts from 1:
   playback maps `index = GridItem.CurrentRow + 1`.
4. **`TablePattern.GetCurrentColumnHeaders()` gives the header texts**, so `column` by exact header
   text works as specified. `GetCurrentRowHeaders()` returns the vertical header (`1`, `2`, `3`),
   which nothing in the schema uses.
5. **`SelectionItem.Select()` on a row's first cell selects the whole row — but only because the
   view selects by row.** `grid_probe_app.py` sets
   `SelectionBehavior = SelectRows` deliberately: with Qt's default (`SelectItems`) the same call
   selects one cell while every check still passes, so the schema's promise would be quietly false.
   The sample app (#33) must set `SelectRows`; pilot apps are not ours to configure, so playback
   (#40) reports what it selected rather than claiming the row.
6. **Qt has no row element** — `QAccessible::Row` maps to HeaderItem — so rows are addressed only
   through the grid, by `GetItem`.
7. **Every descendant carries the grid's own AutomationId.** AutomationId is not unique inside a Qt
   window, and cells are told apart only by GridItem row and column. Hence: never store a cell as a
   repository object (also a finding for #11 and #12).

## WinForms — KeePass 2's entry list

```
m_lvEntries  class=WindowsForms10.SysListView32...  controlType=List
  patterns: Selection, LegacyIAccessible
  Grid pattern: NO     Table pattern: NO

  3 ControlView children:
  [0] Header 'Header Control'
        5 HeaderItem: 'Title' 'User Name' 'Password' 'URL' 'Notes'
  [1] ListItem Name='Sample Entry'      patterns: SelectionItem, Invoke, ScrollItem
        5 Text children: 'Sample Entry' | 'User Name' | '********' |
                         'https://keepass.info/' | 'Notes'
  [2] ListItem Name='Sample Entry #2'   patterns: SelectionItem, Invoke, ScrollItem
        5 Text children: 'Sample Entry #2' | 'Michael321' | '********' |
                         'https://keepass.info/help/kb/testform.html' | ''

  ValuePattern: absent on the list, on every ListItem and on every Text child (Value = None).
```

1. **No Grid pattern and no Table pattern**, so `GridPattern.RowCount`, `GetItem` and
   `TablePattern.GetColumnHeaders` are all unavailable. `rowCount` is the number of `ListItem`
   children — 2 — and the `Header` child is correctly excluded by "rows are its ListItem/DataItem
   children".
2. **The list has columns without having a TablePattern:** a `Header` with five `HeaderItem`s. So
   the reason `cell` is grid-only is not "a list has no columns" — it is that `$defs/column` is
   defined as the Name of a column header *from TablePattern*, and a List need not support it.
3. **Each `ListItem` has five `Text` children, one per column, in header order**, each carrying its
   column's text in `Name`, while the ListItem's own `Name` is the **Title column only**. The #6
   dump showed none of these children because it was taken with the Add Entry dialog on top and the
   list behind it. So a per-column read on a pattern-less list *is* possible: playback (#40) reads a
   row's cells from the row element's `Text`/`DataItem` children in order, so `rowExists {value}`
   with no column matches **any** column (`"Michael321"` finds the second entry) and
   `{value, column}` maps the header text to a child index through the `Header`'s `HeaderItem`s.
4. **No ValuePattern anywhere on this control**, so the cell-text rule falls through to `Name` and
   reads correctly. Together with the Qt result: **Value-first and Name-first are
   indistinguishable on every WinForms control we actually have**, so the choice between them rests
   on the `DataGridView` documentation alone.
5. An empty cell reads as `''` (the second entry's Notes). `row.value` has `minLength: 1`, so
   "this cell is empty" is not expressible in v0.2 — no action needed, noting it so it is not
   mistaken for a gap in the implementation.

## Still not measured

**No pilot app has a WinForms `DataGridView`**: KeePass 2 is a `SysListView32` (above), HandBrake is
WPF, Notepad++ is Win32, KeePassXC is Qt. So ADR source [9] — a `DataGridView` cell's accessible
Name being the column header text plus the row index, which is the whole reason the rule reads
Value first — stays documentation-only until the sample app (#33) or a semester-2 application brings
one. `grid_probe.py handle <h> --automation-id <id>` is the command to run on it when it exists.
