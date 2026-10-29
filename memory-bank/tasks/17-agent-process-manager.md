# #17 Agent process manager in Electron main

- Issue: https://github.com/galipdg/AYNA/issues/17
- Owner: omer · Branch: `omer/17-agent-process-manager`
- Started: 2026-10-29 · Last update: 2026-10-29

## Approach
`client/src/main/agent.ts` (`AgentManager`, no Electron imports, so `node --test` drives it): spawns `python -m ayna_agent.rpc --port 0` with a fresh 32-byte token in `AYNA_AGENT_TOKEN`, reads the one `{"event":"listening","port":n}` stdout line, connects to `ws://127.0.0.1:<port>` with `Authorization: Bearer`, pings, then keeps a heartbeat. Crash or failed heartbeat → kill tree → restart with backoff, at most 3 times, counter reset after 60 s connected → `failed` (UI offers "Start again"). Quit: `before-quit` waits for `stop()`: stdin closed (agent exits on EOF, #135), process tree killed after 3 s. Status goes to the renderer over IPC (`agent:status` event, `agent:get-status`, `agent:retry`); `AgentStatusBar.tsx` shows it under the tagline. Contract: `docs/agent-rpc.md` on #135.

Tests: `src/main/__tests__/agent.test.ts` against `fixtures/fake-agent.ts`, a dependency-free Node stand-in that follows the contract (token check, 401, listening line, ping) with misbehaviour modes.

## Decisions (small, local to this task)
- 2026-10-29 — Node's built-in WebSocket (undici), no `ws` dependency — it sends handshake headers through its init object (checked in Node 23.5 and Electron 45's Node 24.22).
- 2026-10-29 — Heartbeat is the contract's JSON-RPC `ping`, not WebSocket ping frames as said in the #135 review — the built-in WebSocket cannot send ping frames; no contract change. It is sent only while no other call is pending, because replies come in request order and a long call (a Wait step, up to 600 s) would otherwise look like a hang.
- 2026-10-29 — Python: `AYNA_AGENT_PYTHON`, else `../agent/.venv` next to the client, else `python`/`python3` from PATH — the installer (#84) sets the variable for the bundled interpreter.
- 2026-10-29 — Windows stop/kill uses `taskkill /F /T` — a venv `python.exe` is a launcher; killing it alone leaves the interpreter (learnings 2026-10-25).
- 2026-10-29 — While stopping, launch failures (heartbeat, socket close) are ignored — found with the real agent: the heartbeat killed it during the EOF grace period; regression test added.
- 2026-10-29 — #127 review notes done here: `AppPicker` shows an error when saving the choice fails (also after a successful create); every IPC handler goes through `handle()`, which refuses senders other than the entry page (`isTrustedSender`).

## Status
- [x] `agent.ts` + fake agent + 17 tests; IPC + status bar; #127 notes. lint, typecheck, format, 52 tests, build green.
- [x] Real agent from #135 (throwaway venv, macOS): connect, ping, heartbeat, kill → restart, stop (kill after 3 s, since EOF exit is not in #135 yet).
- [ ] Manual UI check on macOS (below), then Windows session (`taskkill /T` path, venv launcher).
- Next step: omer's manual check; then PR (`Closes #17` only after the Windows run, otherwise `Refs #17` + `needs-windows-test`).

## Manual checks
- pending · omer · status bar with fake failure + real agent on macOS (`npm run dev`)
- pending Windows session · agent starts with the app, kill in Task Manager restarts it, quit leaves no `python.exe`

## Open issues
- #135 still lacks "exit on stdin EOF" (asked of galip in the #135 review). Until then quitting AYNA waits 3 s and then kills the agent.
- `../agent/.venv` on main has no `websockets` and no `rpc.py` until #135 merges, so `npm run dev` shows the agent as `failed` with "No module named ayna_agent.rpc" — expected.

## Handoff
- `AgentManager.call(method, params, timeoutMs)` is the entry point for later issues (Spy #24, playback #44); give long calls a timeout that covers them, since the heartbeat pauses while a call is pending.
- The packaged app has no venv next to it; #84 must set `AYNA_AGENT_PYTHON` (or extend `resolveAgentCommand`).

## Outcome (fill when the issue closes)
