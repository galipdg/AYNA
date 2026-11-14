# #40 Playback v1: all keywords + smart waits

- Issue: https://github.com/galipdg/AYNA/issues/40
- Owner: hasan · Branch: `hasan/40-playback-v1`
- Started: 2026-11-14 · Last update: 2026-11-14

## Where #26 left it

`playback/runner.py` already has the shape: resolve with a deadline, act, record one result,
stop the run on a failure. `IMPLEMENTED = frozenset({"Click", "Type"})` and every other keyword
fails by name saying "#40". So this issue is a **delta**, not a rewrite:

| keyword | #26 | #40 |
|---|---|---|
| `Click`, `Type` | done | unchanged |
| `Wait` | fails | wait until the target is *ready*, then pass |
| `Select` | fails | choose the item whose text is `value` |
| `Verify` | fails | the checkpoint: 9 properties × 3 operators, re-read until it holds |
| `SelectRow` | fails | select the row `row` addresses |

The schema on `main` is **0.2** (galip's v0.2 merged), so `SelectRow` and the three row
checkpoints (`cell`, `rowExists`, `rowCount`) are part of v1 whether or not the issue text lists
them — the step editor already produces them (omer's #220), and a document playback cannot read
is worse than a keyword that is not offered.

## The one real gap in #26's waiting, and it is in the issue text

The issue says "before each step wait until the element **exists, is visible and enabled**".
`_resolve_waiting` waits only until the target *resolves*: a disabled or offscreen element
resolves immediately, and the step then fails in `actions` instead of waiting for the control to
become usable. The schema uses the same word for this — `timeoutMs` is "longest wait for the
target … to become **ready**", and `Wait` is "only wait until the target is ready".

So **"ready" = resolves to exactly one element, and is not disabled, and is not offscreen**, and
it is the pre-step wait for *every* keyword, not a `Wait`-only idea. `Resolution` already carries
the `descriptor`, whose `enabled` and `offscreen` come from the same re-read, so this costs
nothing extra per poll.

HandBrake gives the real example from #29: with no source loaded **every** tab reads
`enabled: false`. Under #26's rule a step targeting one fails instantly with an action error;
under this rule it waits out its timeout and then says the control never became enabled, which is
what a tester needs to read.

`enabled`/`offscreen` are `None` when the provider did not report them. `None` must count as
**ready**, not as not-ready: refusing to act on an element whose state could not be read would
make playback depend on a property `NEVER_MATCH` already calls unreliable.

## Decisions (small, local to this task)

- 2026-11-14 — **"Ready" gates every keyword, and a `Verify` is the exception** — a checkpoint
  whose whole purpose is `enabled: false` or `visible: false` would be unplayable if the runner
  refused to look at a disabled element. So a `Verify` step waits only for *resolution*, and the
  checkpoint itself is what re-reads. `Wait`, `Click`, `Type`, `Select` and `SelectRow` wait for
  ready.
- 2026-11-14 — **Keep `within N ms` for element-not-found** even though the issue's third
  criterion says "after N ms". #26 shipped `within`, it is tested, and omer's run report (#59)
  renders it; a checkpoint that ran out of time says `after N ms`, which is the wording I
  committed to in the PR #231 review. Two different waits, two words, both deliberate. Noted on
  the issue rather than changed silently.
- 2026-11-14 — **A checkpoint re-reads on its own deadline, like resolution does** — the schema
  says `timeoutMs` covers "the target (and for SelectRow and row checks, its row or check)
  becoming ready". The same `POLL_INTERVAL_S` (250 ms) and the same deadline, so a property that
  is about to change is not a race.
- 2026-11-14 — **Message wording is fixed and comes from the #231 review**, not invented here:
  `login.message: name should contain "Invalid", it is "Welcome, admin!"`,
  `login.okButton: enabled should be true, it is false`,
  `main.customerGrid: rowCount should be 3, it is 5`,
  `main.customerGrid: a row with "Yılmaz" in "Soyad" should exist, none does`. Lower case,
  logical name first, no "Step failed:" prefix, ` after N ms` appended when it re-read until the
  time ran out. **#40 must use exactly these** — I promised omer they would, and his seed data
  and the report's tests are written against them.

## Status

- [x] Branch, task note, the delta and the "ready" design
- [x] `Wait` + the ready gate — `826b386`
- [x] `Verify` for the six element properties — `playback/checkpoint.py`, `ca51c83`
- [x] `Select` — `playback/items.py` + `playback/tree.py`, `f36f1b3`
- [x] `SelectRow` and the three row checkpoints — `playback/rows.py`
- [x] The three acceptance criteria, each with its own test (see below)
- [x] `docs/agent-rpc.md`'s `runSteps` section rewritten for all six keywords
- **612 agent tests pass, ruff clean (2026-11-14).** No PR yet.
- Next step: ask the user about pushing and opening the PR, then post the Windows manual check
  on the issue and add `needs-windows-test`. Nothing in the code is waiting on anything.

### The three acceptance criteria, and where each is tested

1. **Unit test per keyword** — `test_playback_runner.py`: Click/Type from #26, then `Wait`,
   `Verify` (six properties), `Select`, `SelectRow` and the three row checks, each with its
   happy path and its failures. The pure rules are in `test_playback_items.py` (29) and
   `test_playback_rows.py` (44).
2. **A control that appears after 3 s, no fixed sleeps** — four of them now, one per kind of
   wait: the element (#26's), a property (`Verify`), the items of a list (`Select`) and the
   rows of a grid (`SelectRow` and a row check). Each asserts `clock.at == 3.0`, that every
   sleep was exactly `POLL_INTERVAL_S`, and that `durationMs` is 3000.
3. **Timeout names the logical name** — asserted on `Wait`, `Select`, `SelectRow` and the
   checkpoints. **Kept as `within N ms`** for an element that never appeared (see the decision
   above); a state that never changed says `after N ms`.

### `Select` is not a pure action, and that is the design

`actions.click` and `actions.type_text` each get **one** element and act on it. `Select`
cannot: "choose the item whose text is `value`" needs the *item*, which is a descendant of the
target, and on a combo box **the items may not exist until it is expanded** (#33 measured
exactly this on Qt). So the flow belongs in the runner, where the tree and the re-read live:

1. resolve the target and wait for ready (already done by the time the keyword is reached);
2. look for a descendant of the target whose text is `value` in the tree just read;
3. if there is none and the target has `ExpandCollapse`, expand it, **re-read the tree**, and
   look again — the re-read is the point, because the items are new elements;
4. `SelectionItem.Select()` the item; `Invoke` as a fallback (a menu item answers to Invoke);
5. collapse again if step 3 expanded it, so the screen is left as the test found it;
6. if the target is an editable combo box and none of that worked, `Value.SetValue(value)` —
   last, because it writes text rather than choosing an item, and a combo box that accepts
   arbitrary text would otherwise hide a genuine "no such item".

An item's text: `ValuePattern` value when non-empty, else the UIA Name — **the same rule the
schema already states for a cell** ("a cell's text is its ValuePattern value when that value is
non-empty, else its UI Automation Name"), so `Select` and the row checks share it rather than
each inventing one. That rule belongs in one place both can import.

**The failure must distinguish three things**, because a tester fixes each differently: the
target is not a list or combo box at all; it is, and has no item with that text (say how many
items it does have); and it has the item but the provider refused to select it. The third is
the Qt case and is a finding about the framework, not about the test.

**Expect Qt to refuse** (`active.md`, from #33): `SelectionItem.Select`, `Invoke` and
`ValuePattern.SetValue` all leave a Qt combo box unchanged, and the items only exist after
`ExpandCollapse`. **SC-20 needs `Select` on a combo box**, so if it still refuses after the
expand-and-re-read above, that is a real obstacle for a reference scenario: report it on #40
and raise it for SC-20 rather than faking a pass. Measure it on the sample app (#33) before
concluding anything — the earlier finding was made without the expand-then-re-read step.

### What `Verify` turned out to need

- **Three of the six properties are not in a descriptor and are read live**: `value`
  (`ValuePattern`, then `LegacyIAccessible` — the same ladder `Type` writes down), `checked`
  (`TogglePattern` state is **On**, so indeterminate is *not* checked) and `selected`
  (`SelectionItemPattern`). `name`, `enabled` and `visible` come from the descriptor the walk
  already derived, so they cost nothing beyond the read the runner did.
- **"Cannot be read" is its own failure, not `false`.** No `TogglePattern` on the target, or a
  provider that does not report `IsEnabled`: there is no answer, and reporting "expected true,
  got false" would tell a tester their application is wrong when it is the check that does not
  apply.
- **An empty expectation has to match an element with no text.** `expected: ""` is a real check
  ("the error label is empty") and a nameless target reads as `None`, so `_same` compares
  `actual or ""` against a string expectation. Otherwise an empty label could never be verified.
- **A target that disappears mid-check reports that**, not a property failure: "it was there and
  now it is not" is a different fact and a tester debugs the two differently.
- **The target is resolved again on every poll** rather than kept. A re-read gives new live
  elements and holding the old one would read a stale handle — the same reason #22's
  `elementFromPoint` compares identity instead of trusting a remembered element.

### What `SelectRow` and the row checks turned out to need

- **There is no single shape for "a row", and the rule has to be structural**, not per
  framework, or the next application breaks it. Three shapes, all from the v0.2 ADR's own
  measurements: *the item is the row* and its children are the cells (KeePass 2's `ListItem`
  with one `Text` per column, a WinForms `DataGridView` row); *the items are the cells* and
  only `GridItemPattern` says which row they belong to (a Qt `QTableView` has **no row element
  at all**); *the item is a one-cell row* (a `QListWidget`). The code asks "do the items have
  cell children?" and then "is the target a Table/DataGrid?", which covers all three without
  naming a framework.
- **A grid whose cells do not report `GridItem` is refused, not guessed at.** Inferring rows
  from the child order would be silently wrong on a sorted or virtualised grid, and the whole
  point of #40 is that a wrong `passed` is undebuggable.
- **The column rule is a deliberate duplicate of `server/.../repository/GridColumns.java`**
  (#221) and has to stay exact: that is what fills `RepoObject.columns`, which is the dropdown
  the tester picked the column from. A column list off by one would read the cell *next to* the
  one they meant. `test_playback_rows.py` pins the Qt row-header case to the pixel (the header
  `1` ends at 666, the first cell starts at 667).
- **An empty Qt table still reports its columns here, which is better than the ADR expected.**
  The ADR reasoned from `TablePattern.GetColumnHeaders`, which Qt collects through row 0;
  reading the captured `HeaderItem`s instead still names them. So "a keyed row matches nothing
  because the target names no columns" happens only where there are no header elements at all
  — HandBrake's queue, not an empty table. Worth telling galip, since it is his ADR's text.
- **`rowCount` prefers `GridPattern.RowCount`** — cheap, and it counts rows a virtualised grid
  has not materialised, which the walk cannot see. So `rowCount` 120 and `rowExists {index:
  40}` false can both be true at once; that is honest (`rowCount` is what the grid says it
  has, `rowExists` is what is on screen) and it is a known limit in the ADR.
- **`SelectRow` never falls back to `Invoke`.** Invoking a row *activates* it — a double-click,
  which opens what it points at — and a step that said "select" must not open a window. The
  fallback is MSAA's `LegacyIAccessible.Select(TAKEFOCUS|TAKESELECTION)`, because KeePass 2's
  list offers only Selection and LegacyIAccessible (measured 2026-11-07) and that call means
  the same thing.
- **A view that selects cells rather than rows passes with a message**, which is the ADR's
  "report what it selected instead of claiming the row". A failure would be wrong — the step
  did select — and silence would be worse. Detected with **one** pattern read, the row's last
  cell, rather than one per cell. This is the first place a *passing* step carries a `message`;
  the run report (#59) renders it, which is exactly where it should show up.
- **A cell that is not there is not an empty cell.** `expected: ""` is a real check ("the Notes
  column is empty"), so `cell_of` answers None for a missing cell and the step says "cannot be
  read" with the row count, rather than comparing nothing against "".
- **The ` after N ms` suffix is appended at the end for the checkpoints** (where the wording is
  what omer's report is written against) but sits mid-message for the action keywords, whose
  wording is new: `row 5 was not found after 500 ms; the target has 2 rows` reads, while the
  same clause at the end does not. One rule each, both deliberate.
- **A step whose own shape is wrong fails before the window is read at all**: the checkpoint
  and the row are validated in `_run_one`, so a `SelectRow` with no row or a `cell` check with
  no column does not spend its timeout first. The tests assert `reads == 0`.
- **`agent/tests/grids.py` is the one description of the three measured shapes**, shared by the
  row tests and the runner tests, with an `info` string per node naming the live element. Do
  not duplicate those trees into a test file: they are the measurements.

## Open issues

- **`model.describe_tree` loops for ever on a node that is its own ancestor** (the `while
  walker is not None` ancestor walk has no seen-set). Unreachable from a real UIA walk, where
  parents come from the walker and are strictly upward, and found only because a defensive test
  of mine built such a tree by hand — it hung pytest. Not fixed here: it is outside #40's scope
  and `model.py` is normative under #11. Worth one small issue.
- **The editable-combo `SetValue` read-back may be too strict on a slow provider.** `write`
  confirms the text by reading `CurrentValue` straight back; a box that applies the value
  asynchronously would read as a refusal and the step would report "no item has the text …".
  Only reachable after the whole timeout has already passed, and it has to be checked on
  Windows with a real editable combo box before it is defended.

- **UI Automation cannot choose an item in a Qt combo box** (from #33, recorded in `active.md`):
  `SelectionItem.Select`, `Invoke` and `ValuePattern.SetValue` all leave it unchanged, and the
  items only exist after `ExpandCollapse`. **SC-20 needs `Select` on a combo box**, so this is a
  real obstacle for one of the reference scenarios rather than a detail. Plan: implement `Select`
  through the patterns ladder, expand first when the target offers `ExpandCollapse`, and if Qt
  still refuses, report it on #40 and raise it for SC-20 rather than faking a pass.
- `cell` is grid-only in the schema while `rowExists {value, column}` is allowed on a list — the
  same column mapping, one forbidden and one required. Raised on #220/#221; galip's v0.2 ADR to
  settle. Playback implements what the schema says and the asymmetry stays visible.

## Manual checks

- **2026-11-14 · posted, pending the Windows session** · the full check is issue comment
  `6879885017` on #40 and `needs-windows-test` is on the issue; PR is **#237**. It runs against
  the **sample app** (`eval/apps/sample/sample_app.py`, whose main screen has `cityFilterCombo`
  and `customerGrid`, and whose grid already sets `SelectionBehavior = SelectRows` —
  `windows.py:214`), KeePass 2 and HandBrake. In the order that makes each one count:
  1. **`Select` on the sample app's `cityFilterCombo`**. This is the one that may *fail*: #33 found
     `SelectionItem.Select`, `Invoke` and `ValuePattern.SetValue` all leaving the box
     unchanged, and the items existing only after `ExpandCollapse`. The expand-then-re-read is
     new, so the question is open again — and the second question is whether the popup's items
     are in the window's tree at all or in a window of their own, which would make the
     editable-box `SetValue` the only route. **SC-20 needs this**; if it still refuses, report
     it on #40 and raise it for SC-20 rather than faking a pass.
  2. **`SelectRow` on the sample app's `customerGrid`**: does `SelectionItem.Select` on the first cell
     select the whole row (SelectionBehavior = SelectRows), i.e. is the result `passed` with no
     message? A message means the view selects cells, which is a finding, not a bug.
  3. **`SelectRow` and `rowExists` on KeePass 2's entry list** by a key cell in a column, which
     exercises the `ListItem` + `Text`-children shape and the `Header`/`HeaderItem` columns.
  4. **A `cell` check on `customerGrid`**, which exercises the `GridItem` grouping and the column
     list that must match the editor's dropdown.
  5. **`Wait` and `Verify` on HandBrake with no source loaded**, where every tab reads
     `enabled: false` (#29) — the case the ready gate exists for.

## Handoff

## Outcome (fill when the issue closes)
