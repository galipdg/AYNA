# #265 SelectRow selects a Qt table row but does not make it current

- Issue: https://github.com/galipdg/AYNA/issues/265
- Owner: hasan · Branch: `hasan/265-selectrow-current`
- Started: 2026-11-19 · Last update: 2026-11-19

## Approach
After `rows.select`, `rows.make_current` focuses the table through UIA and sends `Ctrl+Home` +
`Down`×(index−1), then checks the row's first cell still reads selected. Only for rows without a
row element (`Row.is_row` False = Qt's shape). Failure modes pass with `rows.not_current`'s
message and the selection put back. Keyboard is a seam (`rows.keyboard`); `agent/tests/conftest.py`
fakes it for every test not marked `windows`.

## Decisions (small, local to this task)
- 2026-11-19 — **fix with the keyboard (option a), not only report it.** Evidence (issue body):
  UIA Select, UIA SetFocus, both, MSAA accSelect(TAKEFOCUS|TAKESELECTION) and accSelect(TAKEFOCUS)
  all left Open on row 1; keys moved it (`Mehmet Demir`). Keys are within the "never
  coordinates" rule: `Type` already falls back to focus + keys.
- 2026-11-19 — structural condition (`is_row` False) instead of FrameworkId "Qt": the shape is
  what lacks a current-row path, and the row grouping already identifies it. KeePass 2 and
  WinForms rows are untouched (not re-measured here).
- 2026-11-19 — limit 500 rows, 10 ms between keys: row 100 costs ~1 s, not 5 s.
- 2026-11-19 — the "keys landed elsewhere" check reads `IsSelected` on the row's first cell
  (Qt reports no `HasKeyboardFocus` on a cell even after a real move, measured).
- No ADR: the v0.2 rows ADR's semantics ("afterwards only that row is selected") still hold;
  this adds the current row. Documented in `docs/agent-rpc.md` (SelectRow section).

## Status
- [x] `make_current`, `not_current`, runner wiring; 7 rows tests + 3 runner tests
- [x] Windows test `agent/tests/test_playback_qt_select_row.py` (by value and by index): 3/3
      passes; with `make_current` stubbed out both cases fail (control). All 25 `-m windows` pass.
- [x] #62 pre-flight R13–R16 pass, R14 included (was failing)
- [ ] PR
- Next step: open the PR; when #264 merges first, resolve `agent/tests/conftest.py` by keeping
  both fixtures.

## Manual checks
- 2026-11-19 · hasan's machine (agent) · Windows tests above · pass

## Open issues
- KeePass 2 / WinForms DataGridView: does `SelectionItem.Select` set *their* current row? Not
  measured; worth a check at the next pilot-app session (#23 apps).
- `agent/tests/conftest.py` is also created by #264 (PR #266): whichever merges second keeps both.

## Handoff

## Outcome (fill when the issue closes)
