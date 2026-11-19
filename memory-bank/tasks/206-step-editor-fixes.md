# #206 Step editor: decimal comma and stale test after a rename

- Issue: https://github.com/galipdg/AYNA/issues/206
- Owner: omer · Branch: `omer/206-step-editor-fixes`
- Started: 2026-11-08 · Last update: 2026-11-08

## Approach
Both findings come from hasan's Windows run of #38 (issue comment 2026-11-07; failed steps 7 and 10).
- **Decimal comma**: `secondsText(ms, locale)` in `client/src/shared/steps.ts` formats with the UI language's locale (`strings.locale`), and `draftsFrom(document, locale)` now requires the locale. After a language switch, `withTimeoutsIn` rewrites every timeout that is a number, across the whole undo history (`mapHistory`). Since `documentFrom` stores milliseconds, nothing becomes unsaved.
- **Rename**: `TestEditor` remembers the last loaded element list. When `Tests` reloads it (each time the place is shown), `renamedTargets(before, after)` matches the objects by id and builds an old → new name map. `withRenamedTargets` then applies that map to every history state. `renamedFingerprint` applies it to the `saved` fingerprint, so a clean test stays clean and unsaved edits stay unsaved.

## Decisions (small, local to this task)
- 2026-11-08 — Map renames locally instead of refetching the test, as the issue suggested. A refetch would throw away unsaved edits, or need a second rule for dirty tests. The server renames the stored steps the same way (FR-08), so the local map and a refetch agree for a clean test.
- 2026-11-08 — Formatting uses no digit grouping (`useGrouping: false`). Turkish `1.000` would read back through `parseSeconds` as one second.
- 2026-11-08 — Both adjustments run while rendering ("store info from previous renders"), not in an effect, because `react-hooks/set-state-in-effect` refuses setState in an effect body.

## Status
- [x] Locale-aware seconds and a rewrite on language switch; tests for the round trip in both locales, no grouping, and the switch.
- [x] Rename carried into the open test, including undo history and the saved fingerprint; tests include a swap of two names in one reload.
- [x] Client lint, typecheck, format and 201/201 tests pass on macOS.
- [ ] Not run in the UI yet: the mock server (`dev:mock`) has no repository or tests, so only `npm run demo` (real server) can show it.
- [x] #38 check step 3 now says "click into a field in row 2" (omer's #38 issue comment, edited 2026-11-08).
- [x] PR #215 opened 2026-11-08 (Part of #206; galip and hasan requested). The Windows re-run is posted on #206 (comment 2026-11-08) with `needs-windows-test`.
- [x] #215 merged 2026-11-08 (`2e3f144`).
- Next step: after the Windows re-run on #206 passes, close #206 by hand with the evidence and remove `needs-windows-test` (and from #38 if its other steps passed).

## Manual checks
- pending · omer on macOS (`npm run demo`) · Turkish: Wait up to `2,5` is shown as `2,5` after save, then as `2.5` after switching to English. Rename an element used by an open test in the Repository and return to Tests: the step shows the new name, there is no "not in the repository" mark, no unsaved dot, and undo does not bring the old name back.
- pending Windows session · 6-step re-run posted on #206 (#38 steps 7, 10, 14) · #206 criterion 3

## Open issues
- The rename map only sees renames between two loads of the element list that happen while the editor is mounted. If an edit by someone else changes the steps of an open test, it is still last-write-wins (open issue already listed in `38-step-editor.md`).

## Handoff
- `draftsFrom` needs a locale now; pass `strings.locale` from the renderer.

## Outcome (fill when the issue closes)
