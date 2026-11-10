# #207 Demo seed backups, DEMO.md capture note, minimum window width

- Issue: https://github.com/galipdg/AYNA/issues/207
- Owner: omer · Branch: `omer/207-demo-seed-window` (from `omer/memory-2026-11-08-end`, so the 2026-11-08 session-end memory ships here)
- Started: 2026-11-08 · Last update: 2026-11-08

## Approach
Four points from hasan's reviews of #188 and #197. Seed: `repoObjects(snapshot)` in `client/dev/demo/seed.mjs` builds the POST bodies; `src/main/__tests__/demoSeed.test.ts` checks each set against the trial capture with the shared `matchCount`.

## Decisions (small, local to this task)
- 2026-11-08 — Backup set `name` + `controlType` (the issue's reading of #187's suggestion), not the full `suggestUses` result: every one of the four is unique in the trial window with those two. `statusLabel` (no Name) gets `{}`.
- 2026-11-08 — A rerun PATCHes the sample objects' sets back, as it already does for the sample tests, so a database seeded before #207 is fixed by the next `npm run demo`. Objects with other names are not touched.
- 2026-11-08 — Minimum width stays 960; the style guide now says the step table scrolls below ~1280. A 1280 minimum would push the window off a 1366 × 768 screen at 125 % (~1090 px).
- 2026-11-08 — The test loads `seed.mjs` by URL: `dev/` is outside the type-checked tree and has no `.d.ts`.

## Status
- [x] Seed backups + test (client lint, typecheck, 203/203 tests)
- [x] End-to-end on a throwaway Compose project (port 8097, Neo4j ports reset): old seed then new seed fixes the sets, rerun adds nothing; fresh database gets the new sets. Stack and volume removed.
- [x] DEMO.md capture note, `client/AGENTS.md` Chromium 125+ line, style guide width note
- Next step: push and open the PR (`Closes #207`) on omer's OK; ask hasan to review (his points).

## Manual checks
- None needed: the backup sets are checked against the Windows capture of the trial window. omer's own `ayna` stack still has the old sets until the next `npm run demo`.

## Open issues
- A rehearsal that renames `login.loginButton` (DEMO.md §4 step 3) makes the next seed create a second object with the same AutomationId. Older than #207; worth a line in DEMO.md or a seed that skips an AutomationId already saved.
