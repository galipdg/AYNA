# #205 Step editor: step schema 0.2 rows (SelectRow, row picker, row checks)

- Issue: https://github.com/galipdg/AYNA/issues/205
- Owner: omer · Branch: `omer/205-selectrow-rows`
- Started: 2026-11-08 · Last update: 2026-11-08

## Approach
- `client/src/shared/steps.ts`: `SelectRow` and the row properties `cell`, `rowExists`, `rowCount` (ADR `2026-10-28-step-schema-v0-2-rows`). One set of row fields on the draft (`rowBy`, `rowIndex`, `rowValue`, `rowColumn`) serves both SelectRow's `row` and a check's `checkpoint.row`, so switching between them keeps the row.
- Numbers typed by the user (row number, row count) are sent as numbers when they are whole numbers and as the typed text otherwise, so the schema check alone says what is wrong (as with every other field; no second, local number check).
- The element picker offers only grids and lists (`DataGrid`, `Table`, `List`) for SelectRow and row checks, only grids for `cell`; a chosen element of another known control type gets a local problem.

## Decisions (small, local to this task)
- 2026-11-08 — Column is free text for now — the server has no `columns` on a RepoObject and the snapshot schema has no column headers, so the ADR's dropdown has nothing to list.
- 2026-11-08 — Objects whose control type is unknown are not offered for rows and not flagged when chosen — "offers only grids and lists" needs a known type; flagging the unknown would block stored tests for no reason.

## Status
- [x] steps model and problem mapping (`client/src/shared/steps.ts`)
- [x] StepTable row picker and check popover, element filter by control type
- [x] en/tr texts, `docs/ui/` vocabulary; client 207/207, lint, typecheck, format green (2026-11-08)
- [x] tried in a throwaway Vite harness (StepTable alone, sample objects, both languages; deleted)
- [x] pushed, PR #220 (reviews requested from galip and hasan)
- Next step: answer the #220 reviews; then #221

## Manual checks
- 2026-11-08 · omer's agent · StepTable in a browser harness (not the Electron app): SelectRow by text with a column, cell check popover, rowCount, element menu lists only tables/lists (cell: tables), Click→SelectRow on a button shows "needs a table or a list", "first" as a row number shows the whole-number text, en/tr summaries · pass · evidence: this session's screenshots only.
- Not done: the real app against a server, since the demo seed has no grid or list object. Playback of SelectRow and row checks on Windows is #40 (hasan).

## Open issues
- Column dropdown needs `columns` on the grid's RepoObject (server, #15/#25) and column headers in the snapshot (hasan's schema, ADR): opened as #221 (Week 6, before the #52 freeze).
- The English action column (124 px) clips "Choose item" (since #38) and now "Choose row"; Turkish labels fit. A wider default (≈136 px) or shorter labels; belongs with #203 wording or a small follow-up.
- The demo seed (#197/#207) has no grid or list object, so SelectRow cannot be shown in `npm run demo` yet.

## Handoff
- Typed numbers (row number, row count) go to the schema as numbers when whole, else as the typed text (an empty count as `''`), so Ajv names the problem and there is no second local check. `schemaProblems` maps `/row` and `/checkpoint/row` errors to `row-invalid`, a missing `row`/`column` to `row-missing`/`column-missing`, and `/checkpoint/expected` type/minimum/maximum to `count-invalid`.
- `localProblems` now takes the object list (name + controlType) instead of a name set.

## Outcome (fill when the issue closes)
