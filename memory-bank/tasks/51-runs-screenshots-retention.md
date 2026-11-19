# #51 Runs, step results and screenshot storage

- Issue: https://github.com/galipdg/AYNA/issues/51
- Owner: omer · Branch: `omer/51-screenshots-retention` (from `main` at `3bf3f15`)
- Started: 2026-11-08 · Last update: 2026-11-08

## Approach
Server only; builds on #44's server half (runs API, merged in #193). Design: ADR `2026-11-08-run-screenshots-and-retention` (Proposed).

- `runs/ScreenshotStore`: PNG files under `AYNA_SCREENSHOT_DIR`, `<runId>/<stepIndex>.png`, temp file + atomic move.
- `RunService.writeScreenshot` / `readScreenshot`: the graph claims the image (hash, path) first, the file is written after the commit; a repeat rewrites a missing file.
- `RunHousekeeping`: one `@Scheduled` sweep (60 s): idle timeout → retention → orphan folders.
- `TestService.deleteTest` deletes the run folders after its commit.

## Decisions (small, local to this task)
- 2026-11-08 — omer chose all four recommended options: separate PNG upload; global retention (default 1000, 0 = keep all); abort after 60 min idle; `repairProposed` moves to #74. Recorded in the ADR.
- 2026-11-08 — A finished run still takes the screenshot of a stored result: an outbox may deliver it after the finish of a crashed run.
- 2026-11-08 — Upload after the result, else 404 (dead-letter in the outbox), so the client must keep the order.
- 2026-11-08 — No WebSocket event for a screenshot, and none for retention deletes.
- 2026-11-08 — 413 and 415 added as shared OpenAPI error responses (`ContentTooLarge`, `UnsupportedMediaType`); `TooLargeException` in `error/ApiExceptions`.
- 2026-11-08 — The GET has no `produces`, so a 404 can still answer with a problem body.
- 2026-11-08 — Tests get a temporary screenshot folder through a `DynamicPropertyRegistrar` in `TestcontainersConfiguration`, so the context cache key does not change.
- 2026-11-08 — `docs/graph-model.md` lacked the v0.4 bullet (`V0005`, #15); added with v0.5.

## Status
- [x] Branch, #51 In progress on the board
- [x] Screenshot store, upload/download, idle timeout, retention, orphan sweep, test delete removes folders
- [x] `RunStorageIntegrationTest` (15), incl. 100 consecutive runs × 3 screenshots; server 134/134
- [x] Compose volume `screenshots`, env vars in `docker-compose.yml` and `.env.example`, OpenAPI regenerated
- [x] ADR, `docs/graph-model.md` v0.5, SDD rows (§2 deployment, §3 files, §4 runs)
- [ ] PR (`Closes #51`), reviewers galip and hasan (ADR approval)
- Next step: push and open the PR on omer's OK; comment on #74 that it takes over `repairProposed`.

## Manual checks
- 2026-11-08 · agent · real Docker image (`docker compose -p ayna51` beside omer's running `ayna` stack, ports overridden) · pass, 25/25: login, two runs × two steps, upload 201, repeat 200, read back byte-equal as `image/png`, `screenshotUrl`, 401 without token, 409 for another image; files on the `screenshots` volume; after restart with `AYNA_RUN_RETENTION=1` the first sweep deleted the older run (404) and its folder, the newer run's screenshot still served · evidence: session log; script was in the scratchpad.
- No Windows step: server only.

## Open issues
- Acceptance criterion "every step result has a retrievable screenshot" is met for any result whose screenshot is sent; producing one per step is #54 (hasan), sending it is #44's client half and #61.
- Files are written with mode 600 (`Files.createTempFile`); fine for the server, worth knowing for backups (#91).
- `docs/agent-rpc.md` (galip) still says the REST contract is #51's and #74's; inbox note sent.

## Handoff
- SSH to GitHub times out; fetch and push over HTTPS (see `people/omer/active.md`).
- A second Compose stack beside the running one: `docker compose -p <name> -f docker-compose.yml -f override.yml` with `ports: !reset []` for neo4j and `ports: !override ["28080:8080"]` for the server.
- #222 (SDD v0.4) touches other SDD rows; expect at most a small conflict in `docs/sdd/SDD.md` §4.

## Outcome (fill when the issue closes)
