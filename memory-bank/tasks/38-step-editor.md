# #38 Codeless step editor v0

- Issue: https://github.com/galipdg/AYNA/issues/38
- Owner: omer · Branch: `omer/38-step-editor` (stacked on `omer/30-repo-view`, PR #191)
- Started: 2026-11-04 · Last update: 2026-11-04

## Approach
- Tests place (wireframe §6): test list (search, new) | editor (rename, delete, steps table, Save). `client/src/renderer/src/Tests.tsx`, `StepTable.tsx`.
- Row model `DraftStep` in `client/src/shared/steps.ts`: every field is kept while the action changes; `documentFrom` sends only what the action uses. `draftsFrom` → `documentFrom` is the identity on stored documents (tested on every valid example in `schemas/examples/step/`).
- Validation = the shared `schemas/step.schema.json` through Ajv (2020-12 build) **in the main process** (`client/src/main/testCases.ts`, IPC `validateSteps`), plus two checks the schema cannot make (`localProblems`: wait not a number, element not in the repository) and the server's refused fields after a save (`serverProblems`).
- Server calls through main like the repository (#30): `listTests`, `createTest`, `getTest`, `renameTest`, `deleteTest`, `saveSteps` (PUT the whole document; the answer's ids replace the rows' ids).

## Decisions (small, local to this task)
- 2026-11-04 — Ajv runs in main, not the renderer — Ajv compiles with `new Function`; the renderer CSP is `script-src 'self'` (no `unsafe-eval`), and loosening the CSP is worse than one IPC round trip per edit.
- 2026-11-04 — `ajv` added as a devDependency (omer approved in session; it was already in the lockfile as a transitive dependency, 8.20.0).
- 2026-11-04 — Reorder with native HTML5 drag and drop on a handle + Alt+↑/↓ + ↑/↓ buttons; no drag library.
- 2026-11-04 — Element menu is a native `<select>` grouped by screen (`optgroup`); not searchable yet. An element no longer in the repository stays shown as "(not in the repository)" and is marked.
- 2026-11-04 — "Wait up to" is typed in seconds (decimal point or comma, ms precision) and stored as `timeoutMs`; empty = the run's default.
- 2026-11-04 — New row defaults to Click (most common), element empty → "Choose an element." shows at once, as in the wireframe.
- 2026-11-04 — The Tests place stays mounted while hidden (Shell `hidden` wrapper), so unsaved steps survive a visit to another place; switching tests with unsaved changes asks first (Leave / Keep editing). The element list reloads each time the place is shown.
- 2026-11-05 — Step table uses a fixed layout; Action and Element widths can be dragged (or ←/→ on the handle, double-click resets); widths are kept in memory while the app runs, not saved — omer found the columns truncated.
- 2026-11-04 — Terms follow the style-guide glossary (Type text / Choose item / Check / Wait for; Text / Field content; "Wait up to (s)").

## Status
- [x] Shared row model, schema check, server calls, IPC, Tests + StepTable screens, en/tr texts, styles
- [x] `npm run lint`, `typecheck`, `test` (175 pass), `electron-vite build` (schema bundled in main, no Ajv in the renderer)
- [x] Smoke run against the real server (below)
- [ ] Manual check of the screen by omer (below)
- Next step: run the manual check below with omer; fix what it finds; then push and open the PR (base `omer/30-repo-view`).

## Manual checks
- 2026-11-04 · agent · API-level smoke (client main modules → server on :8080, app "Repo View Check"): 6 rows (Type, Type with empty text, Click, Verify text contains, Verify enabled = no, Wait 2,5 s) → schema clean → create, save, reload: identical apart from the new ids; reorder → identical, ids kept; unknown element → 400 shown on step 7 as `target-unknown`; test deleted afterwards · pass · evidence: this session's output (script in the session scratchpad, not kept).
- 2026-11-05 · omer · editor screen on macOS against the real server · partial: login test built and saved (5 steps); action and element columns were truncated ("Kont", "login.kulla") → fixed in `3d532a1` (fixed layout, resizable columns); rest of the check pending

## Open issues
- Import / Export buttons (FR-14, wireframe §6) are not in #38's criteria; the server has them (#39). Suggest a small follow-up issue or fold into #38 if omer wants.
- "Pick in Object Spy…" in the element menu and a searchable element menu (wireframe §6) are not built.
- Changing the application in the top bar while a test has unsaved changes drops them without asking (Shell remounts Tests by app id).
- Save is last-write-wins: two people saving the same test overwrite each other; a step deleted by someone else makes the next save fail with "Step … is not a step of this test" (shown as "Someone else changed this test…").
- Running a test from the editor is #44 (AYNA-043, Week 6), not #38; omer asked for it on 2026-11-05.
- Row menu "duplicate / insert above" (wireframe) not built; rows are added at the end.

## Handoff
- The server's 400 for steps has `errors[].path` like `$.steps[3].target`; `serverProblems` maps them back to rows.
- `strings.serverMessages` gained four test messages; `i18n.test.ts` has a real example of each.

## Outcome (fill when the issue closes)
