# Step schema v0.2: grid and list rows

- Date: 2026-10-28
- Status: Proposed — accepted when Galip, Ömerfaruk and Hasan approve the #147 PR
- Deciders: Galip (proposal), Ömerfaruk, Hasan
- Issue: #147 · Extends [Step schema v0](2026-10-27-step-schema-v0.md) (#13); nothing in it is withdrawn

## Context
A v0 step acts on one repository object and checks one UI Automation property of it. A grid's rows are data, not repository objects, so v0 cannot select a row or check what a row or cell holds. This came up three times on 2026-10-27: the generator (#37) turned "the table lists Yılmaz" into `Verify main.customerGrid name contains "Yılmaz"`, which is valid but reads the grid's Name; the NL guideline (#36, §6.7) puts grid rows out of scope; the SDD (#50, AI-3 known limit 2) lists it. The sample app's list screen (#33; RS C.2: search field, search button, results grid, Open button), the `listSearch` pairs of #36 and playback v1 (#40) need it before the contracts freeze (#52, 7 Dec).

What constrains the design:
- **UI Automation.** A DataGrid or Table control supports the Grid pattern (`RowCount`, `ColumnCount`, `GetItem(row, column)`, zero-based) and, when it has headers, the Table pattern (`GetColumnHeaders`); its items support GridItem/TableItem and, if selectable, SelectionItem [1]–[4]. A List holds ListItem or DataItem children, supports Grid only optionally and never Table [5].
- **Qt (the sample app, PySide6).** A `QTableView` is a UIA Table whose cells are DataItem children; there is no row element (`QAccessible::Row` maps to HeaderItem) [6]. `GetItem` passes the zero-based indexes straight to `cellAt` [7]. Column headers are collected through row 0, so an empty table reports none [8].
- **WinForms.** A `DataGridView` cell's accessible Name is the column header text plus the row index; its Value is the formatted content [9]. So "the cell's text" cannot simply be its Name.
- **pywinauto** wraps DataGrid, List and Table in one `ListViewWrapper`: `item_count()` is the Grid `RowCount`, `cell(row, column)` is `GetItem`, `columns()` reads the Table headers, and `get_item(text)` finds the first item whose Name equals the text [10].
- **The generator (#37)** derives its grammar from this schema and raises on anything it does not know: step rules may test only `keyword`, checkpoint rules only `property`, a `then` may set only `properties` and `required`; no `oneOf`, `not`, `dependentRequired`; and a `then` cannot narrow an `enum` with another `enum`. A rule that ties two fields together (say, "a `cell` check needs a `row` on the step") cannot be derived.

## Options considered
**Where the row goes**
- *A `row` field on any step* (Click, Select, Verify + row). Reads naturally, but "Select needs `value` or `row`" and "a `cell` check needs the step's `row`" tie two fields. The schema could say so only with a step-level `anyOf` or an `if` on two fields, which the derivation does not handle; either the schema stops catching such steps or #37 grows. Rejected.
- *A row inside the logical name* (`main.customerGrid[Soyad=Yılmaz]`). One field, but `target` stops being a repository object id (`(Step)-[:TARGETS]->(RepoObject)`), its pattern becomes a small language, and the parts cannot be validated. Rejected.
- *One repository object per row.* Rows are data that change between runs; the repository describes the UI's structure. Rejected.
- *Select on a grid means "the row with a cell whose text is `value`"*. No schema change, but no position, no column, and no checks. Kept for lists and combo boxes only, as in v0.
- **Chosen:** a new keyword **SelectRow** with a required `row`; a Verify carries its row **inside the checkpoint**, with new checkpoint properties. Every rule is per keyword or per checkpoint property, so the schema enforces all of them and the #37 derivation accepts the schema unchanged. The cost is that a row appears in two places (on a SelectRow step, in a row checkpoint); both use the same `$defs/row`, so the editor needs one row picker.

**How a row is addressed**
- *Position only*: says "the first result", but breaks when the data or the sort order changes.
- *Key cell only*: robust, but cannot say "the first result" or "the grid is not empty".
- **Chosen: both, as two alternative forms.** `{"index": 1}` or `{"column": "Soyad", "value": "Yılmaz"}`. `column` is optional, so "the Yılmaz row" (any cell) works without knowing the column names; this matches pywinauto's `get_item(text)` and lets the NL assistant produce a row without column metadata. When several rows match, the first from the top wins, as with `get_item`.
- *Combined* (the n-th of the rows that match a key): no scenario needs it; it can be added later without breaking stored tests.

**Which checks**
- **Cell text** (`equals`, `notEquals`, `contains`): "row X shows Y". A new property `cell` with `row` and `column`, rather than v0's `name` on a cell, because a WinForms cell's Name is not its text [9].
- **Row exists** (boolean): "the table lists Yılmaz" (the #37 finding) and "the row is gone".
- **Row count** (integer, `equals` only): "the search finds 2 customers", "the grid is empty". "Not empty" is `rowExists` of `{"index": 1}`. `notEquals` and greater/less are left out: numeric comparisons are out of scope in #36 (§6.7), and narrowing the operator `enum` would need a #37 change.
- *Row selected*: useful after SelectRow, but Qt has no row element, so it needs a per-framework rule. Deferred; a new property is backward compatible.
- *Whole-table checkpoint* (compare the grid with a stored table, as TestComplete does): too large for v0.2.

**Version**
- *Accept "0.1" and "0.2"* (`enum`): v0.1 documents stay valid as they are, but a document labelled 0.1 could then hold SelectRow, and the generator reads `version.const`. Rejected.
- **Chosen: `const: "0.2"`**, as v0 decided ("each schema release accepts only its own version").

## Decision
- **Version** `"0.2"`.
- **SelectRow** (new keyword): `target` is the grid or list (a repository object, as always), `row` is required, `value` and `checkpoint` are not allowed. Afterwards only that row is selected (SelectionItem `Select` semantics [11]). The other keywords do not take `row`.
- **Row** (`$defs/row`), one of:
  - `{"index": n}`, 1 ≤ n ≤ 100000: the n-th row from the top as the target shows it now (after sorting or filtering), header rows not counted;
  - `{"value": "…", "column": "…"}`, `column` optional: the first row from the top with a cell whose text is exactly `value` (case-sensitive, 1–1000 characters), in that column if given, else in any column.
  A cell's text is its ValuePattern value when that value is non-empty, else its UIA Name. Measured on Qt (Hasan, 2026-10-29): every `QTableWidget` cell and `QListWidget` item has a ValuePattern whose value is the empty string, and the text is in Name. On WinForms a `DataGridView` cell's Name is its column header text and row index, and its text is the Value [9]. So Name-first would read every WinForms cell as its header and row number, while non-empty-Value-first reads both correctly. For a list, the row is the list item itself.
- **Column** (`$defs/column`): the column header's text exactly as the grid shows it (TablePattern header Name), 1–100 characters.
- **New checkpoint properties** (on a grid or list target):

  | `property` | Needs | `operator` | `expected` |
  |---|---|---|---|
  | `cell` | `row`, `column` | `equals`, `notEquals`, `contains` | string ≤ 1000, may be empty |
  | `rowExists` | `row` (no `column`) | `equals` | boolean |
  | `rowCount` | neither | `equals` | integer 0–100000 |

  The v0 properties do not take `row` or `column`. `expected` may now be a string, a boolean or an integer; each property allows one of them.

  `cell` is grid-only: a list has no columns (no Table pattern, no headers), so a list item is checked with `rowExists` or selected by its text. `rowCount` of a list is the number of its list items (counted as ListItem children, since a list has no Grid pattern). The schema cannot enforce "grid only" because it does not know the target's control type: a `column` against a list target is a playback error, not a validation error, and the editor (#38) and the generator (#37) must not expect the schema to catch it.
- **Waiting.** SelectRow does the target's smart wait and then waits, within the same `timeoutMs`, until its row exists. A Verify of `cell`, `rowExists` or `rowCount` does the target's smart wait and then re-reads the target until the check holds, within the same `timeoutMs`; if it never holds, the step fails as a failed check with the last actual value (the cell text, or "row not found" / "column not found"; whether the row exists; the count). Rows fill after the grid itself is ready (SC-18), which the target's smart wait cannot see. The re-read interval is **250 ms**, and a re-read reads only what the check needs: `rowCount` polls `GridPattern.RowCount`, which is cheap, while finding a row by a key cell walks cells, which costs about 9–12 ms per element on WinForms normally but seconds per element while a modal window blocks the app (#161, PR #170; the 2.6 s per element in the #6 KeePass 2 dump was such a blocked walk), so one pass may take longer than 250 ms there. v0 checks keep their v0 behaviour.

## Compatibility and migration
- **Every v0.1 step is a valid v0.2 step, unchanged**: the change only adds a keyword, an optional field and checkpoint properties, and every v0 rule still holds. The tests check this on every v0.1 example and case.
- **A v0.1 document becomes a v0.2 document by changing `"version": "0.1"` to `"0.2"`**, nothing else. #134 and the server's tests API (#39, PR #156) merged before this ADR. The server reads the version from the schema's `const`, so after this merges it accepts only 0.2; a test saved as 0.1 on a development database is relabelled by changing `version` only, and no production data exists. Relabelled in this PR: `schemas/examples/step/`, the 12 trial pairs in `eval/nl/pairs.jsonl`, and the #37/#71/#36 tests, which now read the version from the schema instead of hard-coding it.

## Consequences
- **Playback (#40, Hasan).** Implements SelectRow and the three properties through the Grid and Table patterns (pywinauto `item_count`, `cell`, `columns`). Row `index` n is Grid row n − 1 (`GetItem`, not the n-th child: a WinForms header row is a child). For Qt, which has no row element, SelectRow selects the row's first cell (SelectionItem `Select`, or a click if the cell has no SelectionItem); with the usual `SelectRows` behaviour that selects the whole row. A list without the Grid pattern: rows are its ListItem/DataItem children, in order. On an empty Qt table no column headers are reported [8], so a key with `column` matches no row (`rowExists` false) instead of failing on the column. Rows a virtualized grid has not loaded are not counted [1]; known limit. Measured by Hasan on 2026-10-29 (a throwaway PySide6 6.12.0 `QTableWidget`, 3 data rows × 3 columns, and a `QListWidget`; pywinauto 0.6.9, raw UIA patterns; Windows 11, 120 DPI):
  - Cell text is in Name and the ValuePattern value is empty (the text rule above).
  - `GridPattern.RowCount` excludes the header (3 for 3 data rows), so `rowCount` maps onto it. `TablePattern.GetCurrentColumnHeaders()` gives the header texts.
  - `GridItemPattern` row and column are **0-based**, while `row.index` counts from 1: playback maps `index = GridItem.CurrentRow + 1`.
  - `SelectRow` is defined on targets that select by row. `SelectionItemPattern.Select()` on the row's first cell selects the whole row on a view with `SelectionBehavior = SelectRows` (verified on `QTableWidget`); on a cell-selecting view the same call selects one cell, and playback reports what it selected instead of claiming the row. The sample app's grid sets `SelectRows` (#33). Pilot apps are not ours to configure, so #40 meets the cell-selecting case.
  - A `QListWidget`'s items are ListItem children in insertion order, each with SelectionItem; the list has Selection but no Grid pattern.
  - Every descendant of a Qt table carries the grid's own AutomationId, so cells are told apart only by GridItem row and column: rows are addressed through the grid and never stored as repository objects (also a finding for #11/#12).
  - Still to check at a Windows session: no current pilot has a WinForms `DataGridView`, so the [9] half of the text rule is untested on our apps. KeePass 2's entry list `m_lvEntries` is a `SysListView32`: a UIA List with a Header of 5 HeaderItems, whose ListItems are named after the Title column only and have no cell children in the #6 dump (which shows only LegacyIAccessible on the list). Check the Grid and Table patterns and `GetItem` on it. If they are missing, KeePass 2 rows are list items: `SelectRow` and `rowExists` work by the Title text, and `cell` checks do not apply.
- **Editor (#38, Ömerfaruk).** One more keyword in the list; a row picker (position, or cell value with an optional column) used for SelectRow and for `cell` / `rowExists` checks; a column field for `cell`; an integer field for `rowCount`; the target picker should offer only grids and lists for SelectRow and the row properties (by control type). Agreed (Ömerfaruk, 2026-10-29): the server keeps `columns` on a grid's RepoObject as a string list, filled from the snapshot's Table headers on import (#15) and on "add to repository" (#25). Qt collects headers through row 0, so an empty table reports none: `columns` may be empty, and neither the editor nor the AI validator rejects an unknown column when it is. The editor's `column` field is a dropdown when the columns are known and free text otherwise.
- **Graph (Ömerfaruk, `docs/graph-model.md`).** `Step` gains `row`, stored as a JSON string like `checkpoint` (Ömerfaruk; the server's `StepSchema.JSON_FIELDS` already lists it); `checkpoint` may hold `row` and `column`. No new node or relationship: the target is still the grid, so impact analysis is unchanged.
- **Generator (#37).** The derivation accepts v0.2 without code changes, and Ollama accepted the derived grammar in a live probe (checked on `galip/37-constrained-generation` 95de284; see the #147 task note). Done in this PR: the tests read the version from the schema, and the per-keyword field-set and checkpoint-split tests cover the new branches. To do after approval: the prompt names SelectRow and the three properties and maps "is listed" to `rowExists`; grid object descriptions list their column headers, and the derivation narrows `column` to an `enum` of the known headers when `columns` is non-empty (in the probe, qwen3 filled `column` with 100 characters of garbage).
- **Guideline (#36).** Take grid rows, row counts and "is listed" out of §6.7. Canonical forms: Select for a list or combo item by its text; SelectRow for a grid row and for a list item by position. Vocabulary: *… satırını seç*, *ilk sonucu seç*, *… listelenmeli*, *N kayıt görünmeli*, *tablo boş olmalı*. The object list gets `columns` for grids. The pairs are relabelled to `"0.2"` in this PR. Absence checks (`rowExists` false, `rowCount` 0) can pass before a slow update has started, so they follow a step that waits for that update.
- **RS / SDD (Galip).** FR-11 lists the keywords: add SelectRow (#35). SDD AI-3 known limit 2 is resolved once #37 adopts v0.2.
- **Freeze (#52).** v0.2 must be accepted and merged before 7 Dec, so that contracts v1 carries it. Row selected, rows on Click or Wait, and a combined row address are later additive changes, each with its own ADR.

## Sources
1. Microsoft, Grid control pattern — https://learn.microsoft.com/en-us/windows/win32/winauto/uiauto-implementinggrid
2. Microsoft, Table control pattern — https://learn.microsoft.com/en-us/windows/win32/winauto/uiauto-implementingtable
3. Microsoft, DataGrid control type — https://learn.microsoft.com/en-us/windows/win32/winauto/uiauto-supportdatagridcontroltype
4. Microsoft, Table control type — https://learn.microsoft.com/en-us/windows/win32/winauto/uiauto-supporttablecontroltype
5. Microsoft, List control type — https://learn.microsoft.com/en-us/windows/win32/winauto/uiauto-supportlistcontroltype
6. Qt, `qwindowsuiautils.cpp` (`roleToControlTypeId`) — https://contribute.qt-project.org/doc/d9/d06/qwindowsuiautils_8cpp_source.html
7. Qt, `qwindowsuiagridprovider.cpp` — https://contribute.qt-project.org/doc/d5/d0b/qwindowsuiagridprovider_8cpp_source.html
8. Qt, `qwindowsuiatableprovider.cpp` — https://contribute.qt-project.org/doc/d4/d44/qwindowsuiatableprovider_8cpp_source.html
9. Microsoft, `DataGridViewCell.DataGridViewCellAccessibleObject` (Name, Value) — https://learn.microsoft.com/en-us/dotnet/api/system.windows.forms.datagridviewcell.datagridviewcellaccessibleobject
10. pywinauto, `controls/uia_controls.py` (`ListViewWrapper`, `ListItemWrapper`) — https://github.com/pywinauto/pywinauto/blob/master/pywinauto/controls/uia_controls.py
11. Microsoft, `IUIAutomationSelectionItemPattern::Select` ("Clears any selected items and then selects the current element") — https://learn.microsoft.com/en-us/windows/win32/api/uiautomationclient/nf-uiautomationclient-iuiautomationselectionitempattern-select
