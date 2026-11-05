# #196 Step editor: undo and redo

- Issue: https://github.com/galipdg/AYNA/issues/196
- Owner: omer · Branch: `omer/196-step-undo` (from `omer/195-demo-fix`, so it stacks on the demo and the UI stack)
- Started: 2026-11-05 · Last update: 2026-11-05

## Approach
`shared/history.ts` holds the plain undo and redo logic, tested without React. `TestEditor` keeps its rows in a `History<DraftStep[]>` instead of a plain array, so "Unsaved changes" still comes from comparing the document with the saved one, and undoing back to it clears the mark by itself.

## Decisions (small, local to this task)
- 2026-11-05 — The key listener is on the window, not on `.test-editor`: the Delete button that had the focus disappears with its row, so focus drops to `body` exactly when undo is wanted. It acts only if the editor is visible (Tests stays mounted behind other places), the rename form is closed, and the key came from the editor or from `body`. The test search keeps its native undo.
- 2026-11-05 — Undo also works across a save. A save maps row keys to stored ids through the whole history, and a row whose step is gone loses its id, so restoring it creates a new step. Otherwise the server answers "Step … is not a step of this test".
- 2026-11-05 — Typing joins one change per field while the gaps stay under 1 s. Selects, add, delete and reorder are one change each.
- 2026-11-05 — History lives in memory: opening another test or reloading starts a new one. Limit 100 changes.

## Status
- [x] `shared/history.ts`, `withStoredIds`, 14 new tests (189 client tests)
- [x] Editor wiring, buttons, en/tr texts
- [x] Real Electron with real key events, on a throwaway stack: 27 of 27
- [x] omer's check of a physical ⌘Z
- Next step: push and PR, with #195 (ask first).

## Manual checks
- 2026-11-05 · agent · Electron over CDP, keys sent with `Input.dispatchKeyEvent` · pass 27/27: Ctrl+Z, ⌘Z, Ctrl+Y, ⇧⌘Z, Ctrl+Shift+Z and the buttons; focus on `body` after a delete; undo back to saved clears the mark; typing as one change; reorder; action change; test search and other places untouched; undo after save and saving the restored step; a new history per test.
- A mutation run without the id fix was inconclusive: the script's login step typed into a step field, so its failures say nothing about the fix.
- CDP goes straight to the renderer, so it does not cover the macOS menu's own Edit > Undo path.
- 2026-11-05 · omer · physical ⌘Z and ⇧⌘Z on macOS · pass, reported in the session; the main folder was on `aad8771`, which has the undo code.

## Open issues
- A `Wait` row's first input is the timeout; nothing to do here, but scripts that fill "the first input" hit it.

## Handoff

## Outcome (fill when the issue closes)
