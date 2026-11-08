# Run screenshots, idle timeout and retention

- Date: 2026-11-08
- Status: Proposed (#51). Needs Galip's and Hasan's approval.
- Deciders: Ömerfaruk (server, client, graph), Hasan (playback screenshots #54, CLI runner #61), Galip (healing transport)
- Issue: #51 (builds on #44; consumers #54, #59, #61, #68, #74, #75)
- Extends: ADR *Runs API and live run updates* (`2026-11-05`). Changes one point of it and of the transport ADR (`2026-10-28`): `repairProposed` moves from #51 to #74.

## Context
- FR-21 and SC-24: a run's report shows a screenshot per step. NFR-40: screenshots are files on the server disk with only their path in the graph, and retention removes them with their run. NFR-28: 100 consecutive runs with retrievable screenshots, and only the last N runs kept, N configurable. NFR-43: those settings are environment variables in `.env.example`.
- The RS already treats screenshot uploads as their own requests (NFR-07 leaves them out of the 500 ms target), and the SDD says "screenshot uploaded separately". Neither says how.
- #54 (Hasan) makes the agent return a PNG with each step result; how it travels from the agent to the client is #54's and #40's. The client (#44) and the CLI runner (#61) forward it to the server.
- The runs ADR left a run whose client never comes back `running` forever, until "#51's idle timeout".
- The transport ADR gave #51 the `repairProposed` write (snapshot import and HealingProposal creation in one transaction). That needs #74's proposal graph (`CANDIDATE` edges, decision fields), and nothing can send one before #73 (week 10).

## Options considered

**1. How a screenshot reaches the server**
- a. *Its own request: `PUT /api/runs/{runId}/results/{stepIndex}/screenshot` with the raw PNG, after the result.* + Matches the RS and the SDD; the JSON result stays small and its repeat check (hash of canonical JSON) unchanged; no base64 overhead (a third more bytes). − Two writes per step; the outbox orders them.
- b. *Base64 inside the step result,* stripped by the server. + One write. − Megabytes of JSON in the outbox and in every repeat comparison; the stored `body` would have to drop it, so "the body as received" is no longer true.

**2. What retention counts**
- a. *The newest N runs of the whole server.* + The literal NFR-28; disk use has a clear bound (N × steps × image size). − A test run rarely loses its history once others run often.
- b. *The newest N runs of each test.* + Every test keeps a history. − Disk grows with the number of tests (NFR-08: 500 tests per application).

**3. A run whose client never comes back**
- a. *Abort it after a configurable time with no write* (default 60 min). + The run list stops showing it as running; watchers get `run.finished`. − A client that comes back later has its results refused (409), which its outbox already handles by dead-lettering (transport ADR).
- b. *Leave it running.* − A stuck "running" entry in every history, forever.

**4. Where `repairProposed` is built**
- a. *In #74,* with the proposal endpoints and graph. + One change defines the proposal's storage, its creation and its decisions; built when #73 can send one. − The result write changes again in week 10.
- b. *In #51 now.* − Defines #74's graph before #74, and nothing exercises it for weeks.

## Decision
**1a, 2a, 3a, 4a.**

### REST
Every endpoint needs an account; any role may use them (ADR accounts). Errors are RFC 9457 problems.

| Call | Body | Success | Errors |
|---|---|---|---|
| `PUT /api/runs/{runId}/results/{stepIndex}/screenshot` | the PNG, `Content-Type: image/png` | 201 first write · 200 the same image again, both `{stepResultId}` | 400 not a PNG (signature check) · 404 unknown run, or no result for the step yet · 409 another image for the step · 413 over the size limit · 415 another content type |
| `GET /api/runs/{runId}/results/{stepIndex}/screenshot` | | 200 `image/png`, `Cache-Control: private, max-age=86400` | 404 unknown run, result or screenshot |

- **The result comes first.** The client and the CLI runner send the screenshot after the step's result has been accepted, through the same outbox. A screenshot without a result is a 404, which the transport ADR's outbox rules treat as dead-letter, so the order matters.
- **A finished run still takes the screenshot of a stored result**, because the outbox may deliver it after the finish call of a run that crashed. It never takes a new result (runs ADR).
- **Repeat.** Compared by the SHA-256 of the bytes, like a result body.
- **Size limit** `AYNA_SCREENSHOT_MAX_SIZE`, default 8 MB (the transport ADR's figure for a result with snapshot and screenshot).
- `StepResultResponse` gains `screenshotUrl`: the GET path above, or `null` while the step has none. Additive.
- A screenshot sends no WebSocket event. The client that plays the run has the image already; a watcher reads it from `screenshotUrl` when it needs it.

### Files
- One folder per run, one file per step: `<AYNA_SCREENSHOT_DIR>/<runId>/<stepIndex>.png`. Compose mounts the named volume `screenshots` at `/data/screenshots`; a server started without Compose uses `data/screenshots` under its working folder.
- The graph claims the image first (hash and relative path on the StepResult), the file is written after the commit, to a temporary name and moved into place. A repeat writes the file again if it is missing, so a crash between the two is healed by the client's retry.
- Deleting a run (its test deleted, or retention) deletes its folder after the commit. A folder that could not be deleted, or that an upload created after its run was deleted, is removed by the next housekeeping sweep: a folder named by a UUID that is not a run id. Other names in the folder are never touched.

### Idle timeout
- A `running` run with no write for `AYNA_RUN_IDLE_TIMEOUT` (default `60m`) ends as `aborted`, with `finishedAt` and `durationMs` like any finish, and `endedBy: "idleTimeout"` on the node. Watchers get `run.finished`.
- A write is the run's creation, a new result or a new screenshot (`Run.lastActivityAt`). A repeat is not, since it changes nothing.

### Retention
- `AYNA_RUN_RETENTION` (default 1000; 0 keeps every run) keeps the newest N runs of the server by `startedAt`. Older runs that have ended are deleted with their results and screenshot folders. A running run is never deleted, but it counts toward N.
- At 1000 runs of 50 steps and about 200 KB per PNG that is about 10 GB; the install guide (#91) states it.
- Deleting runs sends no event; a client showing an old run gets 404 on its next read.

### Housekeeping
One sweep every 60 s: idle timeout, then retention (in transactions of 100 runs), then orphan folders. A failed sweep is logged and tried again at the next one.

### Graph (v0.5, no migration)
- `Run` gains `lastActivityAt` and, for runs the idle timeout ended, `endedBy`.
- `StepResult` gains `screenshotHash` and `screenshotReceivedAt` next to the existing `screenshotPath` (now the path relative to the screenshot folder).
- Properties only; the existing `Run.startedAt` index serves retention.

### `repairProposed` moves to #74
#74 adds the `repairProposed` step and run statuses, the snapshot import and the HealingProposal creation inside the result write, as the transport ADR and the runs ADR describe them. Until then a `repairProposed` result is still a 400. Nothing else in those ADRs changes.

## Consequences
- **Ömerfaruk:** #44's client half sends each screenshot after its result through the outbox (a separate outbox item), and shows it from `screenshotUrl`. #59 reads the files to embed them in the report. #74 takes over `repairProposed`. #91 documents the volume, its backup with Neo4j (NFR-44) and the disk estimate.
- **Hasan:** #54 decides how the PNG travels from the agent to the client; the server takes it as raw `image/png` bytes, at most 8 MB by default. #61 uploads each screenshot after its result with the same endpoint and the same retry rules.
- **Galip:** `docs/agent-rpc.md` "What the client does with a result" may name the separate upload when #54 adds the screenshot field; no change to the healing payload.
- **Freeze (#52):** the two screenshot calls and `screenshotUrl` join the frozen REST contract at G1.
