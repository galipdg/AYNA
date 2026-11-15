# #44 client half — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The test editor's Run button plays the saved test through the local agent one step at a time, shows each result in its row live, stores the run on the server through a durable outbox, and shows a run started by another client live too.

**Architecture:** Everything that talks to the agent, the server or the disk lives in the Electron main process, in modules free of Electron imports so `node --test` drives them with stubs (the pattern of `spy.ts`, `runs.ts`). `runner.ts` plays a run through a swappable `StepPlayer`; `outbox.ts` delivers results; `runEvents.ts` holds the `/ws/runs` subscription. Both feed one stream of `LiveRun` states to the renderer, merged by `src/shared/liveRun.ts`.

**Tech Stack:** TypeScript, Electron main + preload + React renderer, Node's built-in `fetch` and `WebSocket`, `node:test`. No new dependency.

**Spec:** `memory-bank/tasks/44-run-from-editor.md`, section "Client half design". Server contract: ADR `memory-bank/decisions/2026-11-05-runs-api-and-live-updates.md`; agent contract: `docs/agent-rpc.md` § `runSteps`.

## Global Constraints

- No new dependency; no runtime call to anything but the configured AYNA server and the local agent (closed network).
- Every text in both `src/renderer/src/i18n/en.ts` and `tr.ts` (`i18n.test.ts` fails otherwise); dates and numbers through the language's formatters.
- Main-process modules import nothing from `electron`; `index.ts` wires them.
- Window title match is exact string equality. Poll interval 250 ms. Default step time 10 000 ms.
- Outbox file `run-outbox.json` in `app.getPath('userData')`, written temp file + rename. Retry waits 1 s doubling to at most 30 s.
- Run statuses `running | passed | failed | aborted`; step statuses `passed | failed | notRun`. Stop and agent disconnect finish `aborted`.
- Failure category words (from #240's report): `elementNotFound` Element not found / Öğe bulunamadı · `unexpectedWindow` Unexpected window / Beklenmeyen pencere · `assertionFailed` Check failed / Kontrol tutmadı · `timeout` Timed out / Zaman aşımı · `searchIncomplete` Search incomplete / Arama tamamlanamadı. An unknown category is shown as sent.
- `client/`: `npm run lint`, `npm run typecheck`, `npm test` clean before every commit. Conventional Commits with `(#44)` and the `Co-Authored-By` trailer.

## Review Focus

1. **The server is down when the run starts** (`POST /api/runs` fails): nothing is played, the run bar says why; no outbox entry without a run id. → Task 6 test `does not play when the run cannot be created`.
2. **The agent restarts between steps** (`AgentNotConnectedError` on step k): step k `failed` with the agent's message, later steps `notRun`, finish `aborted`; the agent is not called again for this run. → Task 6 test `finishes aborted when the agent goes away`.
3. **The user signs out or the session expires mid-run**: the run keeps playing, results stay in the outbox (401 → wait), and are delivered after the next sign-in to the same server. → Task 5 test `keeps entries on 401 until resumed`.
4. **The test is deleted by someone else mid-run**: `PUT` answers 404; the entries of that run are set aside, the runner keeps playing to the end, and the run bar says the run could not be stored. → Task 5 test `sets a run aside on 404` + Task 6 test `reports a run the server no longer has`.
5. **A step's target was renamed or deleted in the repository after the run started**: the step fails before the agent is called with a message naming the target; it does not stall the run. → Task 6 test `fails a step whose target is not in the repository`.

---

## File map

| File | Responsibility |
|---|---|
| `src/shared/liveRun.ts` (new) | `StepOutcome`, `LiveRun`, `WindowChoice` types; pure merge and display helpers |
| `src/shared/api.ts` (modify) | IPC names, `AynaApi` methods, result types for run start |
| `src/main/runs.ts` (modify) | Server calls: create, get, running list, put result, finish |
| `src/main/runWindows.ts` (new) | Title of a target; finding its window by polling `listWindows` |
| `src/main/stepPlayer.ts` (new) | `StepPlayer` interface and the per-step `runSteps` player |
| `src/main/outbox.ts` (new) | Durable ordered delivery of results and finishes |
| `src/main/runner.ts` (new) | One run: create, play step by step, stop, window choice, finish |
| `src/main/runEvents.ts` (new) | `/ws/runs` connection, subscribe, catch-up |
| `src/main/index.ts`, `src/preload/index.ts` (modify) | Wiring and IPC |
| `src/renderer/src/RunBar.tsx` (new), `StepTable.tsx`, `Tests.tsx`, `i18n/*.ts` (modify) | Run bar, Result column, read-only during a run |
| `dev/mock/ayna_agent/rpc.py`, `dev/demo/seed.mjs` (modify) | `runSteps` in the demo agent; seed elements carry a window title |

---

### Task 1: Shared run state and merge

**Files:** Create `src/shared/liveRun.ts`; Test `src/main/__tests__/liveRun.test.ts`

**Interfaces — Produces:**
```ts
export type StepStatus = 'passed' | 'failed' | 'notRun'
export interface StepOutcome {
  stepIndex: number; stepId: string | null; status: StepStatus
  durationMs: number | null; message: string | null; category: string | null
}
export interface WindowChoice { title: string | null; windows: WindowInfo[] }   // title null: target has none
export interface LiveRun {
  runId: string; testId: string; status: RunStatus; stepCount: number
  startedBy: string; startedAt: string; durationMs: number | null
  mine: boolean                       // started by this client: Stop, timer
  outcomes: StepOutcome[]             // sorted by stepIndex, at most one per index
  current: { stepIndex: number; startedAt: number; timeoutMs: number } | null  // mine only
  choosing: WindowChoice | null       // mine only
  problem: 'not-stored' | null        // the server refused the run's writes (404/409)
}
export function fromSummary(run: RunSummary, mine: boolean): LiveRun
export function withOutcome(run: LiveRun, outcome: StepOutcome): LiveRun   // idempotent per stepIndex; first one wins
export function withSummary(run: LiveRun, summary: RunSummary): LiveRun    // status/duration from server; never back to running
export function stepOutcomeFrom(value: unknown): StepOutcome | null        // reads agent result, REST result or ws event
```

- [ ] **Step 1: failing tests** in `liveRun.test.ts`:
  - `withOutcome keeps the first result for an index` — add `{stepIndex:1,status:'passed'}` then `{stepIndex:1,status:'failed'}` → one outcome, `passed`; order by index after adding 2 then 0.
  - `withSummary never moves a finished run back to running` — finished `failed` + summary `running` → stays `failed`.
  - `stepOutcomeFrom reads all three shapes` — agent `{stepIndex,status,durationMs,message,category}`, REST `StepResultResponse` (extra `id`, `receivedAt`), ws `run.stepResult` (extra `type`, `testId`, `runId`); missing optional fields → `null`; `status:'skipped'` or no `stepIndex` → `null`.
- [ ] **Step 2:** `npm test` → the three fail (module missing).
- [ ] **Step 3:** implement in `src/shared/liveRun.ts` (no imports beyond `shared/api.ts` types).
- [ ] **Step 4:** `npm test` → pass; `npm run lint && npm run typecheck` clean.
- [ ] **Step 5:** commit `feat(client): shared live-run state and merge (#44)`.

### Task 2: Server calls for a run

**Files:** Modify `src/main/runs.ts`; Test `src/main/__tests__/runs.test.ts`

**Interfaces — Consumes:** `request`, `Options`, `Answer` from `apps.ts`; `stepOutcomeFrom` (Task 1). **Produces:**
```ts
export interface CreatedRun { run: RunSummary; document: StepDocument }
export type WriteAnswer = 'stored' | 'retry' | 'unauthorized' | 'gone' | 'conflict'
export function createRun(baseUrl, testId, appVersionId, options): Promise<{ ok: true; created: CreatedRun } | RunsError>
export function getRun(baseUrl, runId, options): Promise<{ ok: true; run: RunSummary; outcomes: StepOutcome[] } | RunsError>
export function listRunningRuns(baseUrl, testId, options): Promise<RunsResult>   // GET /api/tests/{id}/runs?status=running
export function putResult(baseUrl, runId, body: Record<string, unknown>, options): Promise<WriteAnswer>
export function finishRun(baseUrl, runId, status: RunStatus, options): Promise<WriteAnswer>
```
`WriteAnswer`: 200/201 → `stored`; `unauthorized` → `unauthorized`; 404 → `gone`; 409 → `conflict`; 400 → `conflict` (a body the server will never take must not be retried forever); network, timeout, 5xx, `no-server` → `retry`.

- [ ] **Step 1: failing tests** with a fake `fetch` (pattern already in `runs.test.ts`):
  - `createRun posts the test and version and returns the copied document` — asserts method `POST`, path `/api/runs`, body `{testId, appVersionId}`; 201 with `document` → `created.document.steps.length`; 400 → `invalid`; 404 → `not-found`.
  - `putResult maps statuses` — table: 201→stored, 200→stored, 401→unauthorized, 404→gone, 409→conflict, 400→conflict, 503→retry, fetch throws→retry; path `/api/runs/r%2F1/results/3` for `runId 'r/1'`, `stepIndex 3`.
  - `finishRun posts the status` — body `{status:'aborted'}`, same mapping.
  - `getRun reads results` — two results → two `StepOutcome`s in index order.
- [ ] **Step 2:** run, see fail. **Step 3:** implement. **Step 4:** pass + lint + typecheck.
- [ ] **Step 5:** commit `feat(client): server calls to create, write and finish a run (#44)`.

### Task 3: Finding a step's window

**Files:** Create `src/main/runWindows.ts`; Test `src/main/__tests__/runWindows.test.ts`

**Interfaces — Consumes:** `AgentCaller`, `listWindows` from `spy.ts`. **Produces:**
```ts
export interface Clock { now(): number; sleep(ms: number): Promise<void> }
export const systemClock: Clock
export function windowTitleOf(object: { primary: PropertySet; fallback: PropertySet }, captured?: Partial<ElementDescriptor>): string | null
  // primary.windowTitle ?? fallback.windowTitle ?? captured?.windowTitle ?? null; '' counts as none
export type WindowFound = { handle: number } | { many: WindowInfo[] } | { none: true } | { failed: string }
export function findWindow(agent: AgentCaller, title: string, timeoutMs: number, clock?: Clock, stopped?: () => boolean): Promise<WindowFound>
```
Polls `listWindows` every 250 ms until one or more windows have `title` exactly, or `timeoutMs` passes, or `stopped()` is true (→ `none`). A failing `listWindows` that is `not-connected` returns `failed` at once; other failures keep polling.

- [ ] **Step 1: failing tests** (fake clock that advances on `sleep`, agent stub returning a scripted sequence of window lists):
  - `takes the one window with the title` → `{handle}`; a window titled `"AYNA Trial - Login (2)"` does not match `"AYNA Trial - Login"`.
  - `waits for a window that opens late` — empty twice, then present → `{handle}`, and `sleep` called with 250 twice.
  - `gives up after the step's time` — never present, `timeoutMs 1000` → `{none:true}` after 4 polls.
  - `returns every window when two match` → `{many}` of length 2, no further polling.
  - `stops polling when stopped` → `{none:true}` after the first poll.
  - `windowTitleOf prefers primary, then fallback, then the capture` and returns `null` for `''`.
- [ ] **Steps 2–4** as above. **Step 5:** commit `feat(client): find each step's window by its title (#44)`.

### Task 4: The per-step player

**Files:** Create `src/main/stepPlayer.ts`; Test `src/main/__tests__/stepPlayer.test.ts`

**Interfaces — Consumes:** `AgentCaller`, error classes from `agent.ts`, `stepOutcomeFrom`. **Produces:**
```ts
export interface PlayRequest {
  step: Step; stepIndex: number; stepId: string | null; version: string
  handle: number; target: { properties: PropertySet; fallback?: PropertySet } | null
  runId: string; appVersionId: string
}
export interface PlayedStep { outcome: StepOutcome; agentGone: boolean }   // agentGone: AgentNotConnectedError; never sent to the server
export interface StepPlayer { play(request: PlayRequest): Promise<PlayedStep> }
export function perStepPlayer(agent: AgentCaller): StepPlayer
export const STEP_MARGIN_MS = 10_000   // client waits step time + this for the agent's answer
```
Sends `runSteps {handle, steps:{version, steps:[step]}, targets:{[step.target]: target}, runId, appVersionId}` with call timeout `(step.timeoutMs ?? 10_000) + STEP_MARGIN_MS`. Result `results[0]` → outcome with `stepIndex` and `stepId` replaced by the request's. Any thrown error, an empty `results` or an unreadable result → `failed` with a message (`describeFailure` detail, or `"the agent answered something unexpected"`), `category` null, except `-32002` → `searchIncomplete`.

- [ ] **Step 1: failing tests:**
  - `sends one step with its one target` — asserts params shape and timeout `10_000 + 10_000` for a step without `timeoutMs`, `2_000 + 10_000` with `timeoutMs: 2000`.
  - `puts the run's index on the result` — agent answers `stepIndex 0`, request `stepIndex 4`, `stepId 's5'` → outcome `stepIndex 4`, `stepId 's5'`, `durationMs`, `category` passed through.
  - `turns agent errors into a failed step` — `AgentNotConnectedError` (→ `agentGone: true`), `AgentTimeoutError`, `AgentRpcError(-32000)`, `AgentRpcError(-32002)` (→ category `searchIncomplete`), answer `{results: []}` → each `outcome.status:'failed'` with a non-empty message, `agentGone: false` except the first.
- [ ] **Steps 2–4.** **Step 5:** commit `feat(client): play one step through runSteps (#44)`.

### Task 5: The outbox

**Files:** Create `src/main/outbox.ts`; Test `src/main/__tests__/outbox.test.ts`

**Interfaces — Consumes:** `putResult`, `finishRun`, `WriteAnswer` (Task 2); `Clock` (Task 3). **Produces:**
```ts
export type OutboxEntry =
  | { kind: 'result'; serverUrl: string; runId: string; stepIndex: number; body: Record<string, unknown> }
  | { kind: 'finish'; serverUrl: string; runId: string; status: RunStatus }
export interface OutboxFile { entries: OutboxEntry[]; setAside: (OutboxEntry & { answer: 'gone' | 'conflict' })[] }
export interface OutboxSender { put(entry: OutboxEntry): Promise<WriteAnswer> }  // index.ts binds server + token
export class Outbox {
  static open(file: string, sender: OutboxSender, clock?: Clock, log?: (line: string) => void): Promise<Outbox>
  add(entry: OutboxEntry): Promise<void>            // written to disk before it returns
  resume(): void                                    // after sign-in or server change: try now
  unfinishedRuns(serverUrl: string): string[]       // runIds with entries but no finish entry
  onSetAside(listener: (runId: string) => void): () => void
  close(): Promise<void>
}
```
Delivers the oldest entry of the current server first, one at a time; a run's finish goes only after that run's results. `stored` → removed and saved. `retry` → wait 1 s, 2 s, 4 s … 30 s, reset after a success. `unauthorized` → stop until `resume()`. `gone`/`conflict` → this entry and every later entry of the same run move to `setAside`, listener called, log line with the run id. Entries for another `serverUrl` are kept and skipped. A missing or unreadable file starts empty (log the unreadable case and keep the bad file as `run-outbox.json.bad`).

- [ ] **Step 1: failing tests** (temp dir from `mkdtemp`, fake clock, scripted sender):
  - `delivers in order and empties the file`.
  - `writes an entry to disk before add returns` — read the file right after `await add()`.
  - `retries with growing waits` — sender answers retry, retry, stored → sleeps `[1000, 2000]`.
  - `keeps entries on 401 until resumed` — after `unauthorized`, no more sends until `resume()`.
  - `sets a run aside on 404` — results 0,1 and finish of run A; 404 on result 0 → all three in `setAside`, listener called once with `A`; a following run B still delivered.
  - `survives a restart` — add two, close before delivery (sender pending), `open` again → both delivered.
  - `skips another server's entries` and `unfinishedRuns` lists a run with results but no finish.
- [ ] **Steps 2–4.** **Step 5:** commit `feat(client): durable outbox for run results (#44)`.

### Task 6: The runner

**Files:** Create `src/main/runner.ts`; Test `src/main/__tests__/runner.test.ts`

**Interfaces — Consumes:** Tasks 1–5. **Produces:**
```ts
export interface RunnerDeps {
  createRun(testId: string, appVersionId: string): Promise<{ ok: true; created: CreatedRun } | RunsError>
  repoObjects(): Promise<RepoObjectSummary[] | null>
  capturedElement(objectId: string): Promise<Partial<ElementDescriptor> | undefined>
  agent: AgentCaller; player: StepPlayer; outbox: Pick<Outbox, 'add'>
  serverUrl: string; clock?: Clock
}
export type StartAnswer = { ok: true; runId: string } | { ok: false; reason: 'busy' | 'agent-not-connected' | 'no-steps' } | RunsError
export class Runner {
  constructor(deps: RunnerDeps)
  start(testId: string, appVersionId: string): Promise<StartAnswer>   // resolves once the run exists; plays in the background
  stop(): void
  choose(handle: number | null): void   // answers the window chooser; null = Stop
  current(): LiveRun | null
  onChange(listener: (run: LiveRun) => void): () => void
  markNotStored(runId: string): void    // outbox set a run aside
}
```
Loop per step: target lookup → window (cached per title for the run; chooser on `many` or a null title, cached choice per title) → `player.play` → `outbox.add` result → emit. After a `failed` step or Stop: `notRun` outcome for every later index, each added to the outbox. Finish `passed` / `failed` / `aborted` → `outbox.add` finish → emit. A missing window after the wait → `failed`, `category 'unexpectedWindow'`, message naming the title. A `findWindow` answer `failed` (agent not connected) or a `PlayedStep` with `agentGone` fails that step with the message, marks the rest `notRun`, and finishes `aborted` without calling the agent again (Review Focus 2).

- [ ] **Step 1: failing tests** (stub deps, fake clock, a scripted player):
  - `plays every step and finishes passed` — 3 steps, all pass → outbox gets results 0,1,2 then finish `passed`; emitted states end `status:'passed'`, 3 outcomes.
  - `marks the rest notRun after a failure` — step 1 fails → results 0 passed, 1 failed, 2 notRun, finish `failed`.
  - `stops between steps` — `stop()` while step 0 plays → step 0's real result, 1 and 2 `notRun`, finish `aborted`; player called once.
  - `asks when two windows match and remembers the choice` — `current().choosing.windows.length === 2`; `choose(42)` → played with handle 42; the next step on the same title plays without asking.
  - `fails a step whose window never appears` — category `unexpectedWindow`.
  - `fails a step whose target is not in the repository` (Review Focus 5) — player not called for it.
  - `finishes aborted when the agent goes away` (Review Focus 2).
  - `does not play when the run cannot be created` (Review Focus 1) — `start` answers the `RunsError`; outbox untouched.
  - `refuses a second run` → `busy`.
  - `reports a run the server no longer has` (Review Focus 4) — `markNotStored(runId)` → emitted `problem:'not-stored'`; play continues.
- [ ] **Steps 2–4.** **Step 5:** commit `feat(client): run a test step by step in the main process (#44)`.

### Task 7: Live runs from the server

**Files:** Create `src/main/runEvents.ts`; Test `src/main/__tests__/runEvents.test.ts`

**Interfaces — Consumes:** `listRunningRuns`, `getRun` (Task 2); `fromSummary`, `withOutcome`, `withSummary`, `stepOutcomeFrom` (Task 1). **Produces:**
```ts
export interface RunEventsDeps {
  connect(url: string, token: string): WebSocketLike      // index.ts: new WebSocket(url, { headers }) as in agent.ts
  catchUp: { running(testId: string): Promise<RunsResult>; get(runId: string): ReturnType<typeof getRun> }
  clock?: Clock
}
export class RunEvents {
  constructor(deps: RunEventsDeps)
  setServer(serverUrl: string | null, token: string | null): void   // (re)connects; null → closed
  watch(testId: string | null): void                                // one test at a time: unsubscribe old, subscribe new
  onRun(listener: (run: LiveRun) => void): () => void               // runs of the watched test, mine: false
}
```
URL: `serverUrl` with `http`→`ws`, path `/ws/runs`. After `subscribed` and after every reconnect: `catchUp.running(testId)`, then `get` each, emit merged. `run.started` / `run.finished` → `withSummary`; `run.stepResult` → `withOutcome`. Close or error → reconnect with the outbox's waits (1 s … 30 s); close code 1008 → wait for the next `setServer`. Events for another test are ignored.

- [ ] **Step 1: failing tests** (a fake socket object with `send`, `close`, and emitters):
  - `subscribes to the watched test and moves on` — `watch('a')` → `{type:'subscribe',testId:'a'}`; `watch('b')` → unsubscribe a, subscribe b.
  - `catches up after subscribed` — running list with one run + its two results → one emitted run with two outcomes.
  - `merges live events` — `run.stepResult` twice for the same index → one outcome; `run.finished` → status `failed`.
  - `reconnects and catches up again` — socket closes → after 1000 ms a new connect, re-subscribe, catch-up called twice in total.
  - `waits for a new token after 1008`.
- [ ] **Steps 2–4.** **Step 5:** commit `feat(client): live runs of the open test over /ws/runs (#44)`.

### Task 8: Wiring and IPC

**Files:** Modify `src/shared/api.ts`, `src/main/index.ts`, `src/preload/index.ts`; Test `src/main/__tests__/agentContract.test.ts` (only if the `runSteps` request is checked against `schemas/agent-rpc.schema.json` there — add one case for Task 4's request shape).

**Produces (renderer API, `AynaApi`):**
```ts
startRun(testId: string, appVersionId: string): Promise<StartAnswer>
stopRun(): Promise<void>
chooseRunWindow(handle: number | null): Promise<void>
watchRuns(testId: string | null): Promise<LiveRun | null>   // returns this client's current run of that test, if any
onRun(listener: (run: LiveRun) => void): () => void          // IPC.run; both mine and others'
```
`index.ts`: one `Outbox` opened at startup on `join(userData, 'run-outbox.json')`, sender bound to the current `server()` (skip entries whose `serverUrl` differs); `resume()` after login and server change; at startup and after login, every `unfinishedRuns(serverUrl)` not owned by the live runner gets `add({kind:'finish', status:'aborted'})` (spec §9). One `Runner` with `perStepPlayer(agent)`. One `RunEvents`; `setServer` on login/logout/server change. Both `onChange`/`onRun` → `webContents.send(IPC.run, run)` to every window. Outbox `onSetAside` → `runner.markNotStored`. Track 401s with the existing `track()` where a call returns a result type.

- [ ] **Step 1:** add the contract test case (`runSteps` params of Task 4 validate against the schema's `runStepsRequest`); run → it fails only if the shape is wrong, otherwise note it passes from the start.
- [ ] **Step 2:** wire as above; `npm run typecheck` clean; `npm test` all pass.
- [ ] **Step 3:** commit `feat(client): wire the runner, outbox and live runs into the app (#44)`.

### Task 9: Run bar and Result column

**Files:** Create `src/renderer/src/RunBar.tsx`; Modify `src/renderer/src/StepTable.tsx`, `src/renderer/src/Tests.tsx`, `src/renderer/src/Shell.tsx` (pass `version` to `Tests`), `src/renderer/src/i18n/en.ts`, `tr.ts`, `src/renderer/src/strings.ts` if it re-exports keys; Test `src/main/__tests__/i18n.test.ts` (existing, catches missing keys) and `src/main/__tests__/liveRun.test.ts` (display helpers).

**Interfaces — Consumes:** `AynaApi` run methods (Task 8), `LiveRun` (Task 1). **Produces in `liveRun.ts`:** `runBarState(run: LiveRun, now: number): { kind: 'running' | 'choosing' | 'passed' | 'failed' | 'aborted'; stepNumber: number; elapsedMs: number; failed?: StepOutcome }` and `rowState(run: LiveRun | null, stepIndex: number, now: number): { kind: 'none' | 'pending' | 'playing' | 'passed' | 'failed' | 'skipped'; outcome?: StepOutcome; waitedMs?: number; timeoutMs?: number }`.

UI (wireframe 8, style guide components only):
- `Tests.tsx` header: **Run** button (`btn-main`), enabled when saved (`!dirty`), no problems, agent `connected`, a version chosen and no `mine` run is `running`; its `title` says which of these is missing. While a run of this test is `running`, steps read-only (`StepTable` gets `readOnly`), Save/Undo/Redo/Rename disabled.
- `RunBar` above the table: running → `runRunning(step, of, elapsed)` / `runRunningBy(user, step, of)` + **Stop** (mine); choosing → `runChooseWindow(title)` with one button per window (title and class name) + Stop; passed → `runPassed` + **Run details** (`openReport`); failed → `runFailedAt(n)` · category word · message + Run details; aborted → `runStopped(n)`; `problem: 'not-stored'` → warning `runNotStored`. `role="status"` on the bar.
- `StepTable` Result column only when a run is shown: ✓ `duration`, ● `runWaiting(waited, of)` (mine), ✕ with the message on its own line under the row, `– runSkipped`, `·` pending.
- `watchRuns(testId)` on editor open and test change; `watchRuns(null)` on unmount; a 1 s ticker only while a mine run is running.

- [ ] **Step 1: failing tests** in `liveRun.test.ts`: `runBarState names the failed step`, `rowState shows skipped after a failure and playing for the current step`.
- [ ] **Step 2:** run → fail. **Step 3:** implement helpers, components, texts (EN and TR, category words from Global Constraints). **Step 4:** `npm test`, lint, typecheck clean; `npm run build` succeeds.
- [ ] **Step 5:** commit `feat(client): run bar and live step results in the editor (#44)`.

### Task 10: Demo agent, seed, memory and the by-hand checks

**Files:** Modify `dev/mock/ayna_agent/rpc.py`, `dev/demo/seed.mjs`, `memory-bank/tasks/44-run-from-editor.md`, `memory-bank/people/omer/active.md`, `journal.md`.

- [ ] **Step 1:** `rpc.py`: `runSteps` answers one `passed` result per step after 300 ms per step (`durationMs: 300`, `matched: 'primary'`, `performedWith: 'Invoke'`); a step whose `value` is `"fail"` answers `failed` with `message: "mock failure"`, `category: "assertionFailed"`.
- [ ] **Step 2:** `seed.mjs`: every seeded object's captured element carries `windowTitle` equal to `dev/demo/windows.json`'s first title (`"AYNA Trial - Login"`).
- [ ] **Step 3:** macOS check with `npm run demo` (§10 shape, recorded in the task note's "Manual checks"): run the seeded login test → rows go ✓ one by one, bar ✓ Passed, Run details opens the report, the run is in Runs; a step with value `fail` → ✕ with the category word, later rows – Skipped; Stop mid-run → Stopped at step n; second client window (`npm run demo` second instance or a second machine) on the same test sees the run live; `docker compose -p <demo> stop server` mid-run then start → the run still completes on the server (outbox). Stop the stack after (memory: stop stacks after checks).
- [ ] **Step 4:** Windows check text for the weekly session (after #237 merges) as an issue comment draft in the task note: real agent, trial app, login test across the login and main windows, two clients (SC-17), 100 % and 150 %.
- [ ] **Step 5:** task note Status / Next step, `active.md`, `journal.md`; commit `docs(memory): #44 client half built, checks planned (#44)`.

---

## Self-review notes (2026-11-15)

- Spec coverage: §1 start → T6/T9; §2 targets → T6; §3 window → T3/T6; §4 one step → T4; §5 notRun/Stop/aborted → T6; §6 player → T4; §7 outbox → T5/T8; §8 live → T7/T8; §9 restarts → T5 `unfinishedRuns` + T8 + `watchRuns` returning the current run; §10 screen → T9; testing and manual check → T10.
- Types used across tasks: `StepOutcome`, `LiveRun`, `WindowChoice` (T1); `CreatedRun`, `WriteAnswer` (T2); `Clock`, `WindowFound` (T3); `StepPlayer`, `PlayRequest` (T4); `OutboxEntry`, `Outbox` (T5); `Runner`, `StartAnswer` (T6); `RunEvents` (T7).
- Fixed in review: "agent gone" is `PlayedStep.agentGone` (T4), read by T6; only `outcome` goes to the outbox.
