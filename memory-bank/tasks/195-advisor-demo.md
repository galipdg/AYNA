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
- 2026-11-05 — `.step-check` wraps (separate commit). The check controls were 35 px wide at the default window and only readable from about 1728 px. Narrowing Action and Element would bring back the truncation omer reported on #38. The commit belongs to #38 and sits here because the demo needs it.

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
- 2026-11-05 · agent · `eval/apps/trial/app.py` on macOS with PySide6 6.12.0 · pass, platform `cocoa`, window opens · this showed the sample tests expected texts the app never shows; fixed.

## Open issues
- At the default 1280 px window the step table still overflows by 138 px and the page by 8 px, so the row buttons need scrolling. `DEMO.md` says to use full screen; worth a follow-up on #38.
- omer asked for Ctrl+Z in the step editor; not built yet.
- `DEMO.md` will go stale as the stack merges; it is for this meeting, and #91 is the real guide.

## Handoff
- This branch is stacked on the #38 branch. Do not merge it into `main` before the stack.
- The fake agent makes a new `snapshotId` per capture, so a live add never hits the 409 for one snapshot in two versions.

## Outcome (fill when the issue closes)
