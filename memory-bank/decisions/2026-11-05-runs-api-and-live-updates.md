# Runs API and live run updates

- Date: 2026-11-05
- Status: Accepted (#44). Ömerfaruk proposed; Hasan approved it on #193 (2026-11-07) with two amendments, both applied here (`durationMs`; `repairProposed` as a run status); Galip approved it on #240 (2026-11-15).
- Deciders: Ömerfaruk (server, client, graph), Galip (agent RPC, healing transport), Hasan (playback, CLI runner)
- Issue: #44 (builds on #39, #60; consumers #40, #51, #61, #68, #74)
- Extends: ADR *Healing proposal transport* (`2026-10-28`), ADR *Healing proposal schema 0.2* (`2026-10-31`). Answers SDD open item 5 (how live updates are framed).

## Context
- FR-20 and SC-17: a run is shown live in the author's client, stored on the server, and shown live in every other client that has the test open. NFR-06 gives 1 s for that.
- The transport ADR fixes `POST /api/runs` and `PUT /api/runs/{runId}/results/{stepIndex}`, but not the bodies, how a run is finished, or the WebSocket messages.
- The transport ADR hands the `PUT` to #51, while #44's criteria need Run and StepResult stored. The plain write therefore comes first here; #51 keeps `repairProposed`, screenshots and retention.
- The agent's request is #40's, and #40 and #26 have not started. The server half can be built and tested now without them.
- The accounts ADR already says WebSocket handshakes authenticate like REST. A CI service account is an ordinary tester account, so `startedBy` (a user id) also covers runs started with an API token.
- The client's main process already sends `Authorization` on a WebSocket handshake to the agent (Node's WebSocket), so no client library is needed for the same thing here.

## Options considered

**1. How other clients get live status**
- a. *Plain Spring WebSocket with small JSON messages.* + What RS §3.5.4, NFR-32 and the SDD already say; one new starter; a client needs no library. − We write a small subscription registry.
- b. *STOMP over WebSocket.* + Topics and a broker come ready-made. − A framing layer and a client library for one kind of event on one server.
- c. *Server-sent events.* + No new dependency; runs through the normal HTTP filter chain. − Changes the RS, the SDD and the issue; one stream per test, or a new request for every subscription change.

**2. What a run's `stepIndex` points into**
- a. *A copy of the step document taken when the run starts, stored on the Run and returned by `POST /api/runs`.* + Stays true when the test is edited during or after the run; a report (#59) can still show what was played. − A JSON string per run.
- b. *The test's current steps.* + Nothing stored. − An edit silently changes what old results mean; `StepResult -FOR-> Step` disappears when a step is deleted.

**3. Who decides a run's final status**
- a. *The client says, the server checks it against the stored results.* + Matches the transport ADR ("finish the run as failed"); catches a client bug. − A small rule on the server.
- b. *The server works it out.* + One source of truth. − `aborted` still has to come from the client.

**4. A `repairProposed` result before #51 and #74**
- a. *400 until they exist.* + No half state: the transport ADR rejects a "repair proposed" step without its proposal. Nothing can send one before #73.
- b. *Store the status and drop the proposal.* − Silent loss of the proposal.

## Decision
**1a, 2a, 3a, 4a.**

### REST
Every endpoint needs an account, and any role may use them (ADR accounts). Errors are RFC 9457 problems.

| Call | Body | Success | Errors |
|---|---|---|---|
| `POST /api/runs` | `{testId, appVersionId}` | 201 `Run` with `document` | 400 blank field, test without steps, version of another application · 404 unknown test or version |
| `GET /api/runs/{runId}` | | 200 `Run` with `document` and `results` by `stepIndex` | 404 |
| `GET /api/tests/{testId}/runs?status=` | | 200 newest first, at most 20, no results | 400 unknown status · 404 |
| `PUT /api/runs/{runId}/results/{stepIndex}` | `params` of `run.stepResult`, unchanged | 201 first write · 200 identical repeat, both `{stepResultId}` | 400 · 404 unknown run · 409 another body for the key, or a new result on a finished run |
| `POST /api/runs/{runId}/finish` | `{status}` | 200 `Run` | 400 · 404 · 409 status does not fit the results, or the run ended with another status |

`Run`: `id`, `testId`, `appVersionId`, `status`, `stepCount`, `startedBy` (`UserRef`), `startedAt`, `finishedAt`, `durationMs`.

Rules:
- **Run status:** `running`, then `passed`, `failed` or `aborted`. **Step status:** `passed`, `failed`, `notRun`; `repairProposed` is added by #51 and #74.
- **A run stopped by a repair proposal** (TBD-6: the test stops after it) finishes as **`repairProposed`**, a fifth run status that #51 adds with the step status. It is allowed when at least one result is `repairProposed` and none is `failed`. `aborted` keeps meaning a crash, so RQ5 (#86) can count runs that ended in a proposal, and the run list shows "Needs review" (`docs/ui/style-guide.md`). #66's JUnit mapping of such a run is galip's to settle; this ADR fixes only the stored status.
- **Result body.** Required: `runId` and `stepIndex` equal to the path, and `status`. `stepId` is null or the id at that position in the run's copy. `stepIndex` is inside the copy. `durationMs` and `message` are read when present (Hasan settled the names for #40 on #193: a unit in the name, like `timeoutMs` and the snapshot's `durationMs`). Unknown members are kept, because #40, #54 and #63 add their own, and the stored body is what a repeat is compared with.
- **Repeat.** Compared by a SHA-256 hash of canonical JSON (sorted keys), as the schema 0.2 ADR says. This replaces "first write wins, never 409" in the SDD row for runs.
- **Finish.** `passed` needs a result for every step and all of them `passed`. `failed` needs at least one `failed` result. `aborted` is always allowed: the client uses it after an agent or client crash, also for a run with gaps. The same status again answers 200. `durationMs` is `finishedAt - startedAt`.
- **Any account may write a run's results**, not only the one that started it: an outbox may deliver after a sign-in as someone else. For the same reason results and the finish store no user of their own. Who sent a write says nothing about who ran the test, so `startedBy` is the record FR-40 asks for.

### Graph (v0.3, migration `V0004`)
- `Run` gains `stepCount`, `document` (JSON string), `startedBy`, `finishedAt`. `StepResult` gains `runId`, `stepIndex`, `stepId`, `message`, `bodyHash`, `body` (JSON string), `receivedAt`.
- New `(Run)-[:ON_VERSION]->(AppVersion)`: a relationship, because history is filtered by version, unlike the audit properties.
- New unique constraint on `(StepResult.runId, StepResult.stepIndex)`, so two overlapping retries cannot both create a result. The loser reads the stored result and answers as a repeat.
- `(StepResult)-[:FOR]->(Step)` is created when the step still exists. If it was deleted, the result keeps its `stepIndex` into the run's copy.
- **Deleting a test deletes its runs and their results.** A Run without its TestCase means nothing. A run still in progress loses its target, so its next write answers 404 and the client's outbox sets it aside.

### WebSocket `/ws/runs`
- The upgrade request passes the same security chain with `Authorization: Bearer <token>`, so no token in a URL. Without a valid token the handshake gets 401. Only the client's main process connects, as with the agent.
- Client to server: `{"type":"subscribe","testId":"…"}`, `{"type":"unsubscribe","testId":"…"}`.
- Server to client:

| `type` | Other fields | When |
|---|---|---|
| `subscribed` | `testId` | After a subscribe |
| `run.started` | `testId`, `run` (`Run` without `document`) | After `POST /api/runs` commits |
| `run.stepResult` | `testId`, `runId`, `stepIndex`, `stepId`, `status`, `durationMs`, `message` | After a first write commits, never for a repeat |
| `run.finished` | `testId`, `run` | After the finish commits, never for a repeat |
| `error` | `detail` | A message the server cannot read |

- **Catch-up.** There is no replay buffer. After `subscribed`, and after every reconnect, the client reads `GET /api/tests/{testId}/runs?status=running` and `GET /api/runs/{id}`, then merges by `stepIndex`. A stored result never changes, so the merge is safe in any order.
- **Token checks.** Every 60 s the server re-checks each connection's token and closes it with 1008 if the token has expired or was revoked. A connection can therefore outlive a revocation by up to 60 s. REST calls are not affected.
- **Slow clients.** A send has 5 s and 512 KB of buffer. Past that the connection is closed, and the client reconnects and catches up.
- **Scope.** The subscription registry lives in the server's memory, which is enough for one central server.

### Not part of this decision
- The client half: Run button, outbox, `runSteps` (#44, after #38 and #40).
- `targets` in the create response. #40 settles the name, and resolving them needs #25's `RESOLVES_TO` on `main`. Adding it later is additive.
- `repairProposed`, screenshots, retention and the server-side idle timeout (#51, #74). Until the timeout exists, a run whose client never comes back stays `running`.

## Consequences
- **Ömerfaruk:** new dependency `spring-boot-starter-websocket` (Apache-2.0, version from the Boot parent, no external calls). `docs/graph-model.md` v0.3; SDD rows for runs and live updates, and open item 5. The client half needs no new library.
- **Hasan:** #40 reads `POST /api/runs`'s `document` as the steps to play, so `stepIndex` is the position in it. #61 uses the same endpoints and finish call. `durationMs` and `message` are the names the server reads (settled on #193). #51 adds the `repairProposed` run status above.
- **Galip:** `docs/agent-rpc.md`, "What the client does with a result" says the REST contract is #51's and #74's. After this ADR the plain write is #44's.
- **Freeze (#52):** the REST calls above and the WebSocket messages join the frozen contracts at G1.
