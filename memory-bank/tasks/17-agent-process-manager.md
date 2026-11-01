# #17 Agent process manager in Electron main

- Issue: https://github.com/galipdg/AYNA/issues/17
- Owner: omer · Branch: `omer/17-agent-process-manager`
- Started: 2026-10-29 · Last update: 2026-11-01

## Approach
`client/src/main/agent.ts` (`AgentManager`, no Electron imports, so `node --test` drives it): spawns `python -m ayna_agent.rpc --port 0` with a fresh 32-byte token in `AYNA_AGENT_TOKEN`, reads the one `{"event":"listening","port":n}` stdout line, connects to `ws://127.0.0.1:<port>` with `Authorization: Bearer`, pings, then keeps a heartbeat. Crash or failed heartbeat → kill tree → restart with backoff, at most 3 times, counter reset after 60 s connected → `failed` (UI offers "Start again"). Quit: `before-quit` waits for `stop()`: stdin closed (agent exits on EOF, #135), process tree killed after 3 s. Status goes to the renderer over IPC (`agent:status` event, `agent:get-status`, `agent:retry`); `AgentStatusBar.tsx` shows it under the tagline. Contract: `docs/agent-rpc.md` on #135.

Tests: `src/main/__tests__/agent.test.ts` against `fixtures/fake-agent.ts`, a dependency-free Node stand-in that follows the contract (token check, 401, listening line, ping) with misbehaviour modes.

## Decisions (small, local to this task)
- 2026-10-29 — Node's built-in WebSocket (undici), no `ws` dependency — it sends handshake headers through its init object (checked in Node 23.5 and Electron 45's Node 24.22).
- 2026-10-29 — Heartbeat is the contract's JSON-RPC `ping`, not WebSocket ping frames as said in the #135 review — the built-in WebSocket cannot send ping frames; no contract change. It is sent only while no other call is pending, because replies come in request order and a long call (a Wait step, up to 600 s) would otherwise look like a hang.
- 2026-10-31 — Superseded: since #135 merged, the agent answers requests concurrently and in any order, so the heartbeat now pings even during a long call (galip's #155 review); the fake agent's `block` no longer blocks its thread.
- 2026-10-29 — Python: `AYNA_AGENT_PYTHON`, else `../agent/.venv` next to the client, else `python`/`python3` from PATH — the installer (#84) sets the variable for the bundled interpreter.
- 2026-10-29 — Windows stop/kill uses `taskkill /F /T` — a venv `python.exe` is a launcher; killing it alone leaves the interpreter (learnings 2026-10-25).
- 2026-10-29 — While stopping, launch failures (heartbeat, socket close) are ignored — found with the real agent: the heartbeat killed it during the EOF grace period; regression test added.
- 2026-11-01 — Exit message (`describeExit`): Windows reports a killed child as `signal === null` with a non-zero code, so the stderr tail is appended only when it is not a DEBUG/INFO/WARNING record in `rpc.py`'s log format, and codes above 0x7FFFFFFF are shown in hex (NTSTATUS). No "we killed it" flag: our own kills always set `reason` first, and an external kill (Task Manager) cannot be told from a crash on Windows. The restart test expects `exited with code 1` on win32 (Node's kill = `TerminateProcess(…, 1)`). From hasan's Windows run, 2026-10-31.
- 2026-10-29 — #127 review notes done here: `AppPicker` shows an error when saving the choice fails (also after a successful create); every IPC handler goes through `handle()`, which refuses senders other than the entry page (`isTrustedSender`).

## Status
- [x] `agent.ts` + fake agent + 17 tests; IPC + status bar; #127 notes. lint, typecheck, format, 52 tests, build green.
- [x] Real agent from #135 (throwaway venv, macOS): connect, ping, heartbeat, kill → restart, stop (kill after 3 s, since EOF exit is not in #135 yet).
- [x] Manual UI check on macOS passed (below).
- [x] Windows session 2026-10-31 (hasan): 6/7 steps pass; `agent.test.ts:160` and the "failed" message wrong on Windows → fixed 2026-11-01 (`describeExit`), 56 tests green on macOS.
- [ ] Windows re-run of `npm test` + the "failed" message check; `needs-windows-test` stays on #17 until then.
- Next step: after the Windows re-run passes, switch the PR body to `Closes #17` and mark it ready.

## Manual checks
- 2026-10-29 · omer · status bar on macOS (`npm run dev`, 7 steps: failure path with retry and quick quit; real #135 agent connected, kill → restart ×3, 4th kill → failed, Start again, quit leaves no `ayna_agent.rpc` process) · pass · evidence: omer's report in session
- 2026-10-31 · hasan · Windows 7-step check (PR #154) · 6/7 pass; unit test 51/52 and "failed" message showed an INFO log line · evidence: #17 issue comment 2026-10-31
- pending Windows session (re-run after the 2026-11-01 fix) · `npm test` all green; kill the agent 4× → "failed" message has no INFO line · earlier: agent starts with the app, kill in Task Manager restarts it, quit leaves no `python.exe`

## Open issues
- Electron's renderer is not exposed to UI Automation on Windows (hasan, 2026-10-31): a UIA walk finds only the menu bar. Matters for #24/#44 manual checks and if AYNA should ever test its own client; candidate for an issue.

## Handoff
- `AgentManager.call(method, params, timeoutMs)` is the entry point for later issues (Spy #24, playback #44); give long calls a timeout that covers them, since the heartbeat pauses while a call is pending.
- The packaged app has no venv next to it; #84 must set `AYNA_AGENT_PYTHON` (or extend `resolveAgentCommand`).

## Outcome (fill when the issue closes)
