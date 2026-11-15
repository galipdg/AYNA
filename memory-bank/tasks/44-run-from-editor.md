# #44 Run tests from the editor with live status

- Issue: https://github.com/galipdg/AYNA/issues/44
- Owner: omer · Branches: `omer/44-run-api` (server half, merged as PR #193) · `omer/44-run-from-editor` (client half, from `main` 2026-11-15)
- Started: 2026-11-05 · Last update: 2026-11-15

## Approach
Two halves, because #40 (and #26 under it) has not started and `runSteps` is #40's to define.

1. **Server half, now** (`omer/44-run-api`, PR `Part of #44`): Run and StepResult storage, finish call, live updates over WebSocket. Package `server/.../runs/`. Design: ADR `2026-11-05-runs-api-and-live-updates` (Proposed). Testable with no agent.
2. **Client half, later**: Run panel, durable outbox, `runSteps`. Needs #38 on `main` and #40.

Branching from `main` keeps this out of the #182 → #192 stack, so it stays small and reviewable alone.

Acceptance criteria against the halves:
- "Login test shows step-by-step status live": client half + #40.
- "Run and StepResults are stored in Neo4j": server half; end to end with the client half.
- "A second client watching the same test sees the run live": server half sends it; the screen is the client half.
- "The Run stores the id of the user (or API token)": server half. A CI service account is an ordinary tester account (ADR accounts), so a user id covers tokens.

## Client half design (2026-11-15, approved by omer)

**Intent.** The Run button in the test editor plays the saved test through the local agent, shows each step's result in its row as it arrives, and stores the run on the server; another client with the same test open sees the same run live (FR-20, SC-17, NFR-06 1 s). The screen is wireframe 8 (`docs/ui/wireframes.md`): a run bar above the step table, a Result column, Stop.

**Goals.** #44's criteria 1 and 3 on the client side; criterion 2 end to end with the server half already on `main`. Show FR-35's failure `category` in plain words when the result has one (#240's words).
**Non-goals.** Screenshots (#54), healing and `repairProposed` (#73, #74), the CLI runner (#61), the machine name in the run bar (the `Run` has none), a run of unsaved steps.
**Anti-goals.** A run reported as passed although a step did not run. A result lost because the server or the network was away. Playback acting on a window AYNA guessed when two match.

**Approaches considered.**
- *How steps reach the agent* — (a) one `runSteps` call per step (**omer chose, 2026-11-15**): live status with no contract change, and each step can go to its own window; costs a window read per step and the client marks the rest `notRun` after a failure. (b) Wait for `run.stepResult` notifications from the agent: needs a `schemas/` bump and an owner, date unknown. (c) One call for the whole test with fake progress: not live, rejected.
- *How each step's window is found* — (A) automatically from the target's `windowTitle` (**omer chose**); (B) the user picks one window before the run: cannot play a login → main-window test.
- *Where the run loop lives* — (1) Electron main process (**omer chose**): token, agent, files and the WebSocket are already there (ADR runs: only the main process connects), a reload of the screen does not stop a run, `node --test` can drive it with the fake agent. (2) The renderer: less code, but a reload kills the run and the outbox has to live in main anyway.

**Design.**
1. **Start.** Run is enabled when the steps are saved and valid, the agent is `connected` and no run of this client is going. `POST /api/runs {testId, appVersionId}` (the version chosen in the top bar). The steps played are the returned `document`, so `stepIndex` points into the server's copy (ADR runs 2a). The steps are read-only during the run.
2. **Targets.** One `listRepoObjects(appId)`; `targets[name] = {properties: primary, fallback}` for every target the document uses. A target missing from the repository fails its step before the agent is called.
3. **Window per step.** The title is the target's `windowTitle` from `primary`, else `fallback`, else the object's last capture (`getRepoObject(id).element`, read once per object per run). Before each step, `listWindows` and take the windows whose title equals it exactly. One → its handle. None → poll every 250 ms until the step's time (`timeoutMs` or 10 000 ms) runs out, then fail the step with `category: unexpectedWindow` (a login window that closes and a main window that opens late both work). Two or more → the run pauses and the run bar asks the user to choose among them; the choice is kept for that title for the rest of the run. No title at all → the same chooser over every window. Stop also answers the chooser.
4. **One step.** `runSteps {handle, steps: {version, steps: [step]}, targets: {its one target}, runId, appVersionId}`. The single result's `stepIndex` 0 becomes the real index; `stepId` comes from the document. An agent error (`-32000`, `-32002`, `-32602`, timeout, disconnect) becomes a `failed` result with its message, so it is stored like any other failure.
5. **After a failure or Stop.** Every later step gets a `notRun` result (what the agent itself does in one call, TBD-6), then finish: `passed` if all passed, `failed` if one failed, `aborted` after Stop or an agent disconnect. Stop takes effect between steps; the step being played finishes first (the agent cannot cancel a call). *My call:* Stop finishes as `aborted`, the only status the ADR allows for a run with gaps; to be written in the ADR's consequences if galip or hasan object.
6. **A swappable player.** `runner.ts` talks to a `StepPlayer` (`play(step, index, target, handle) → StepResult`). The per-step player is the only one now; agent notifications later replace that one module.
7. **Outbox.** Every result and the finish go first to `run-outbox.json` in `userData` (temp file + rename, like `settings.ts`), then to the server in order: `PUT /api/runs/{runId}/results/{stepIndex}` with the result as the body, then `POST /api/runs/{runId}/finish`. Delivered entries are removed. Network failure or 5xx → retry with growing waits (1 s doubling to 30 s), and on start of the client. 401 → wait for the next sign-in. 404 or 409 → set aside in the file with the problem and log it (the ADR: test deleted, or a different body). A repeat answers 200, so a retry after a lost answer is safe. The outbox belongs to a server URL; entries for another server wait.
8. **Live view.** Main opens `/ws/runs` with the session token while a test is open in the editor and sends `subscribe`/`unsubscribe` as the open test changes; reconnects with the same waits and after a sign-in. After `subscribed` and after every reconnect it catches up: `GET /api/tests/{testId}/runs?status=running`, then `GET /api/runs/{id}`, merged by `stepIndex`. The renderer gets one stream of run states, whoever started the run; this client's own results reach the screen at once from the runner and again from the server, merged by `runId` + `stepIndex`. Only the client that started the run shows Stop and the step timer.
9. **Restarts.** A reloaded screen asks main for the current run state and carries on. A client that quits mid-run keeps its outbox: on the next start, a run in the outbox with no finish entry and no loop playing it gets a finish `aborted` after its results are delivered, so it does not wait for the server's idle timeout (#51).
10. **Screen.** Run bar: running → "Running · step n of m · m:ss" (author) or "Running by <user> · step n of m" (others); passed → "✓ Passed · Run details"; failed → "✕ Failed at step n · <category> · <message> · Run details"; aborted → "Stopped at step n". Run details opens the report (#59). Result column per row: ✓ duration, ● waiting… s of s (author only), ✕ with the message under the row, – Skipped, · not yet. Every text in `i18n/en.ts` and `tr.ts`.

**Left to the builder.** File and function names past `runner.ts`, `StepPlayer` and `run-outbox.json`; the IPC channel names; how much of the merge lives in `src/shared/` so the renderer can test it; the backoff's exact numbers within the bounds above.

**Testing.** `node --test`: the runner against the fake agent (window found, window late, two windows, failure → `notRun` and `failed`, Stop → `aborted`, disconnect); the outbox against a fake `fetch` (order, retry, 401 wait, 404/409 set aside, survives a restart); the merge of live events. Manual check (§10), at the Windows session after #237 merges: the trial app's login test from two clients on one test (SC-17), one run stopped, one run with the server stopped mid-run and started again.

## Decisions (small, local to this task)
- 2026-11-05 — Follow schema 0.2 ADR point 7 (409 for a repeat with another body), not the SDD row "never 409". The ADR is still Proposed in the index, but it came from omer's own review and `docs/agent-rpc.md` already says the same. Fix the SDD row here.
- 2026-11-05 — The plain `PUT` moves from #51 to this PR, because #44's criteria need it. #51 keeps `repairProposed`, screenshots, retention, idle timeout.
- 2026-11-05 — No block on deleting a test with a `running` run: with no idle timeout yet, a run whose client died would block the delete forever.
- 2026-11-07 — From hasan's #193 review: `duration` → `durationMs` everywhere (result body, `Run`, `StepResult`, event); the ADR asked him to settle the name. The ADR now says a run stopped by a repair proposal finishes as `repairProposed` (added by #51; allowed with ≥ 1 `repairProposed` result and no `failed` one), so `aborted` keeps meaning a crash (user approved the review scope).

- 2026-11-08 — #51's ADR moves `repairProposed` to #74; #51 built screenshots (separate PNG upload after the result), retention and the idle timeout. The client half's outbox must send a step's screenshot after its result.

## Status
- [x] Branch from `main`, #44 In progress on the board
- [x] ADR, `V0004`, `spring-boot-starter-websocket` (omer's OK 2026-11-05)
- [x] REST (`runs/RunController`, `RunService`), test delete removes runs; `RunIntegrationTest`
- [x] `/ws/runs` (`RunEvents`, `RunEventsConfig`), 60 s token re-check; `RunEventsIntegrationTest` (real port, real client)
- [x] `docs/graph-model.md` v0.3, SDD rows, OpenAPI regenerated; 86 server tests
- [x] PR #193 (`Part of #44`), reviewers galip and hasan, 2026-11-05
- [x] 2026-11-15: client half built on `omer/44-run-from-editor` from the plan `44-run-from-editor-plan.md` (Tasks 1–10): `liveRun.ts`, `runs.ts` calls, `runWindows.ts`, `stepPlayer.ts`, `outbox.ts`, `runner.ts`, `runEvents.ts`, IPC, `RunBar.tsx`, Result column; mock agent answers `runSteps`. 288 client tests.
- [ ] Client half: by-hand check of the screen (below), then PR (`Closes #44` only after the Windows check)
- [x] 2026-11-07: hasan's review fixes (`durationMs`, ADR `repairProposed`); 86 server tests, OpenAPI regenerated
- [x] 2026-11-07: PR #193 squash-merged (`4d0c98a`) on omer's yes, before #182
- 2026-11-15: client half started on `omer/44-run-from-editor`; design above, approaches chosen by omer.
- Next step: whole-branch review, then omer's by-hand check of the screen with `npm run demo`, then push + PR.

## Manual checks
- 2026-11-15 · agent · main-process chain end to end, real server (Docker `ayna44`, port 28044) + mock agent through the real `AgentManager`, script in the session scratchpad · **pass 8/8**: run created, 7/7 results stored as `passed`, a second `RunEvents` client saw it live (13 updates), Stop → stored `aborted` with later steps `notRun`, server stopped mid-run → run played to the end and the outbox delivered 7/7 after the server came back. The outage check first **failed** (run hung in the window chooser) and found a bug: titles from the last capture were read from the server step by step; fixed in `78bb137` (read before the first step) with a runner test. Stack torn down after.
- 2026-11-15 · omer · check A on macOS (`npm run demo`), screenshots on omer's Desktop (15.16.52–15.17.07) · **steps 1, 3, 4 (bar and Runs list), 5 pass**: Run next to Save; rows ✓ one by one; "✓ Başarılı"; Stop → "4. adımda durduruldu" with later rows "– Atlandı"; the runs listed as Başarılı / Yarıda kesildi. **Run details fails** with "Sunucuya ulaşılamadı", and so does "Raporu aç" on the Runs screen: a bug in #59's report on `main`, not in #44 (`report.html` streams through `StreamingResponseBody`; Spring Security re-authorizes the async dispatch without the bearer context and throws `AccessDenied` after the body has started, so the client gets a truncated response; `curl` shows 200 and exit 18). Step 8 first used plain `npm run dev`, which starts the real agent (not on macOS); the command is fixed below. Steps 2, 6, 7, 8 not reported yet.
- Pending (omer, macOS): check A steps 2, 6, 7, 8.
- Pending (Windows session, after hasan's #237 merges): real agent and trial app — checklist below; post as an issue comment with `needs-windows-test`.

### By-hand check A — the screen on macOS (`npm run demo`)
**Setup:** in `client/`: `npm ci`, then `npm run demo`; log in as admin; choose "AYNA Deneme Uygulaması"; version 1.0; open Tests → "Geçerli kullanıcıyla giriş".
1. Look at the header. *Expected:* **Run** next to Save, enabled; its tooltip is empty.
2. Change a step without saving. *Expected:* Run disabled, tooltip "Save the steps first." Undo the change.
3. Press **Run**. *Expected:* the bar "Running · step n of 7 · m:ss" with Stop; rows turn ✓ one by one (≈0.3 s each), the current row shows "● waiting…"; the steps cannot be edited or dragged.
4. When it ends. *Expected:* "✓ Passed" + **Run details**, which opens the report; the run is in Runs.
5. Run again and press **Stop** during step 2–3. *Expected:* "Stopped at step n"; later rows "– Skipped".
6. Set one Type step's value to `fail`, save, run. *Expected:* that row "✕ Check failed" with "mock failure" under it; later rows Skipped; bar "✕ Failed at step n · Check failed · mock failure".
7. Switch the language to Türkçe and repeat step 3. *Expected:* "Çalıştır", "Çalışıyor · 7 adımın n. adımı", "Başarılı".
8. Second client: a second instance needs its own data folder (one client per folder, #44) and the demo's fake agent (plain `npm run dev` starts the real one, which is not installed on macOS). From `client/`: `AYNA_AGENT_PYTHON=python3 PYTHONPATH="$PWD/dev/mock" AYNA_MOCK_WINDOWS="$PWD/dev/demo/windows.json" AYNA_MOCK_SNAPSHOT="$PWD/../schemas/examples/snapshot/trial-login.json" npm run dev -- -- --user-data-dir=/tmp/ayna-second`; server `http://127.0.0.1:8080`, log in, open the same test; run from the first window. Also check that a plain second `npm run demo` only brings the first window to the front. *Expected:* the second shows "Running, started by admin · step n of 7" without Stop, and the same ✓ rows within 1 s.
**Report back:** pass/fail per step; for a failure a screenshot and the client console lines.

### By-hand check B — Windows session (real agent, after #237 merges)
**Setup:** Hasan's machine; `git switch omer/44-run-from-editor`; start the trial app (`eval/apps/trial`); server running; in `client/`: `npm ci && npm run dev`; log in; the trial app's application and version; a test that logs in and then checks something in the main window.
1. Run the login test. *Expected:* steps on the login window, then on the main window after it opens (each step finds its own window by title); ✓ Passed.
2. Open two trial app windows with the same title, run. *Expected:* the bar asks which window, one button per window; the choice is kept for the rest of the run.
3. Close the trial app mid-run. *Expected:* the next step fails "Unexpected window" after its wait; later steps Skipped.
4. Second client on another machine or user with the same test open (SC-17). *Expected:* live within 1 s.
5. Repeat step 1 at 100 % and 150 % scaling.
**Report back:** pass/fail per step and scaling; a screenshot, the `[agent]` console lines, Windows version and scaling for a failure.
- 2026-11-05 · agent · real Docker image on a fresh volume, Node's WebSocket as in `client/src/main/agent.ts` · pass, 15/15: bad or missing token refused, no `Origin` header needed, all three events reach the watcher, repeat not broadcast, 409 as a problem, step to watcher 69 ms (NFR-06: 1 s), logout closes with 1008 after 58.7 s through the real scheduler · evidence: run log in this session; the first run's one failure was the smoke script's stale waiter, not the server.
- Retry path checked by removing it: `overlappingRetriesStoreOneResult` then fails with `ConstraintValidationFailed`.
- Server half: no human step needed. Plan a check for the client half (two clients on one test, SC-17) while designing that screen.

## Open issues
- `docs/agent-rpc.md` says the REST contract is #51's and #74's. Galip's file: note on the PR.
- A run whose client never comes back stays `running` until #51's idle timeout.
- 2026-11-15: **Stop finishes `aborted`**, while the runs ADR says `aborted` means a crash. Ask galip and hasan on the PR; if they want a `stopped` status, that is an ADR change and a server change.
- 2026-11-15: the client sets `category: unexpectedWindow` itself when no window has the step's title; #63 says the agent fills categories. Say so on the PR (hasan).
- Screenshots per step (#54) are not sent yet: the agent does not take them.

## Handoff
- 2026-11-15: client half in the worktree `.claude/worktrees/pr-reviews-windows-queue-13fdc7`, branch `omer/44-run-from-editor`. SSH to GitHub works again (port 443).
- The plan and its ledger: `memory-bank/tasks/44-run-from-editor-plan.md`; the ledger itself is git-ignored scratch in `.superpowers/sdd/`.

## Outcome (fill when the issue closes)
