# #195 Advisor demo: one command and a Turkish guide

- Issue: https://github.com/galipdg/AYNA/issues/195
- Owner: omer · Branch: `omer/195-advisor-demo` (from `omer/38-step-editor`, because the UI is not on `main`)
- Started: 2026-11-05 · Last update: 2026-11-05

## Approach
`npm run demo` (`client/dev/demo/run.mjs`): checks Docker, `docker compose up -d --build`, waits for health, logs in with the `.env` admin, seeds through the REST API (`seed.mjs`), then opens the client with the fake agent. `DEMO.md` at the repo root is the Turkish guide.

## Decisions (small, local to this task)
- 2026-11-05 — A new `demo` script, not a change to `dev:mock`: the stub server has only health and apps, and `dev:mock` is for working without Docker. omer agreed.
- 2026-11-05 — Own user data folder with `--user-data-dir` (`$TMPDIR/ayna-demo-client`), so a demo never touches normal settings and needs no product code. Electron honours the switch.
- 2026-11-05 — Login stays manual: it is a screen to show.
- 2026-11-05 — Seed through the API, not Cypher, so sample data passes the real checks. Versions 1.0 (captured) and 1.1 (selected, not captured), so a live capture has something to add.
- 2026-11-05 — The sample capture's snapshot id comes from a hash of its version id, not the fixture: the server takes an id into one version only, and a used database may hold the fixture's id. Unique per version and the same on every run, so a repeat is still a no-op.
- 2026-11-05 — Every run puts the two sample tests back: it delivers corrections to a database already seeded, and a rehearsal leaves nothing behind in them. Tests and objects made by hand are not touched.
- 2026-11-05 — A check is a one-line summary that opens a native popover. Wrapping its three controls made rows two and three lines tall, which omer found unbalanced, and one line cannot hold them. The popover sits in the top layer, so the table's scroll area cannot cut it off, and needs no new dependency. Belongs to #38; it sits here because the demo needs it.

## Status
- [x] Issue, board In progress, branch
- [x] `npm run demo`, sample data, shared `fake-agent-env.mjs`
- [x] Client lint, format, typecheck, 175 tests
- [x] End-to-end run on a throwaway stack (below)
- [x] `DEMO.md`, link in `README.md`
- [ ] omer's manual check in the main folder, against the real `.env` and `ayna` stack
- Next step: omer runs the manual check; then push and PR, and the line in `client/AGENTS.md` (asked at the same time, AGENTS §7).

## Manual checks
- 2026-11-05 · agent · real Electron over CDP on a throwaway Compose project · pass: ready in 18 s with cached layers; login, Spy tree, property panel, live "Depoya ekle" on version 1.1 (6 objects), Repository counts and details, Tests with 7 and 4 steps, language switch. Second run through `npm run demo --no-build`: ready in 2 s, no duplicates, clean login. Failure messages checked: Docker missing, Docker not running, wrong password, no admin set. Evidence: screenshots in this session only.
- Not covered: `npm ci` on a fresh checkout, Windows.
- 2026-11-05 · omer · manual check in the main folder · **fail** at the seed: 409, the fixture's snapshot id was already imported into another version on the real volume (the 2026-11-03 "Repo View Check" data). The `.env` login and Docker steps passed. My test had only used fresh volumes. Fixed: the sample capture gets an id derived from its version.
- 2026-11-05 · agent · the same collision reproduced on a throwaway stack, then the fix: pass on that database with the failed run's partial state, on a repeat, on a fresh database and on its repeat; 5 objects, 2 tests, no duplicates each time.
- 2026-11-05 · omer · same manual check again · screens fine, one table shift reported · the screenshot could not be read here (protected temp folder), so the shift is still open.
- 2026-11-05 · omer · the table shift, screenshot received: at 1280 px the table needed sideways scrolling, so Step and Action were cut off to reach the row buttons. Fixed on `omer/196-step-undo`: no scrolling at 1280, 1366, 1440, 1728 and 2200 px, the page scrollbar is gone. A window below 1280 px scrolls the table (34 px at 1180). omer's look at the fix · pending.
- 2026-11-05 · omer · rows 5 and 7 grew to two and three lines, which looked unbalanced, and he asked for a resizable test list. His screenshot was still from `aad8771`, before the table fit. Fixed: a check shows as a one-line summary and opens its controls in a popover; the test list drags between 150 and 420 px. omer's look · pending.
- 2026-11-05 · agent · `eval/apps/trial/app.py` on macOS with PySide6 6.12.0 · pass, platform `cocoa`, window opens · this showed the sample tests expected texts the app never shows; fixed.

## Open issues
- The active item in the side menu draws 2 px wider than the menu (`NAV.nav` scroll width 202 of 200). Cosmetic, not from this work.
- omer asked for Ctrl+Z in the step editor; not built yet.
- `DEMO.md` will go stale as the stack merges; it is for this meeting, and #91 is the real guide.

## Handoff
- This branch is stacked on the #38 branch. Do not merge it into `main` before the stack.
- The fake agent makes a new `snapshotId` per capture, so a live add never hits the 409 for one snapshot in two versions.

## Outcome (fill when the issue closes)
