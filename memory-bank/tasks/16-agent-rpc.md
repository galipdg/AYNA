# #16 Agent JSON-RPC server (localhost only)

- Issue: https://github.com/galipdg/AYNA/issues/16
- Owner: galip · Branch: `galip/16-agent-rpc`
- Started: 2026-10-27 · Last update: 2026-10-29

## Approach
`agent/ayna_agent/rpc.py`: JSON-RPC 2.0 over a WebSocket on `127.0.0.1` (library `websockets`, asyncio API). The token is checked during the opening handshake, so an unauthenticated client never gets a socket. UI Automation stays out of `rpc.py`: the server takes a `Desktop` object (`list_windows()`, `snapshot(handle, timeout_ms)`, optional `setup()`/`close()`) that hasan's recognition layer will provide; tests use a fake one, so everything runs on macOS. Contract for the client: `docs/agent-rpc.md`; decisions that bind omer and hasan: ADR `2026-10-27-agent-rpc-v0` (Proposed).

## Decisions (small, local to this task)
- 2026-10-27 — Do #16 now although it depends on #12: only `snapshot` needs #12; transport, auth, `ping` and `listWindows` do not — galip's choice. PR says `Refs #16`; the issue closes when the real backend answers `snapshot`.
- 2026-10-27 — `websockets~=17.3` as a runtime dependency of `agent/` — galip approved.
- 2026-10-27 — The real UIA backend lives in `recognition/` (hasan, ADR `2026-10-25-windows-work-to-hasan`), not in `rpc.py` — galip's choice; request in hasan's inbox.
- 2026-10-27 — Results are objects (`{"windows": [...]}`), not bare arrays, so fields can be added without breaking clients.
- 2026-10-27 — Requests on one connection are handled one after another; UIA calls are serialised on one thread anyway, and WebSocket keepalive pings still run because the event loop never blocks. *Superseded 2026-10-29, see below.*
- 2026-10-27 — Tests use `asyncio.run` in plain pytest functions instead of adding `pytest-asyncio`.
- 2026-10-29 — Review of #135 (Auto-fix on; decided by galip's agent, open to galip's veto before merge):
  - One task per request, replies in any order matched by `id` (hasan 2): `ping` must answer during a long snapshot, and going unordered after G1 would break clients, not the other way round. omer's #17 client already matches by id.
  - `snapshot` gets an optional `timeoutMs` (1–600000) and `-32002` Snapshot timeout (hasan 1); unknown params still refused; no partial document in v0.1. The backend enforces the budget, because `run_in_executor` cannot be cancelled.
  - Optional `setup()`/`close()` on the backend, run once on the worker thread; a failing `setup()` stops the server (hasan 4).
  - The agent exits on stdin EOF unless stdin is a terminal (omer 1; his #17 client already closes stdin to stop the agent). A watched terminal would stop a background job with SIGTTIN.
  - Bounds are physical pixels; hasan sets per-monitor-v2 DPI awareness at startup with the backend, as he offered (hasan 3). Only the doc changes here.

## Status
- [x] Branch, task note, board In progress
- [x] `rpc.py` + `tests/test_rpc.py` (50 tests pass on Python 3.11.13 and 3.15.1, ruff clean); manual run of `python -m ayna_agent.rpc` matched the doc's examples
- [x] `docs/agent-rpc.md`, ADR (Proposed), requests in hasan's and omer's inboxes
- [x] PR https://github.com/galipdg/AYNA/pull/135 (`Refs #16`) opened 2026-10-27, reviewers omer and hasan
- [x] omer approved 2026-10-29 (two doc points); hasan commented 2026-10-29 (four points, approves the ADR decisions)
- [x] Review points addressed on 2026-10-29: 64 tests pass on 3.11 and 3.15; reverting to ordered handling makes the `ping` test fail
- [ ] hasan's approval of the PR; then set the ADR to Accepted (and its README line) in the same PR
- [ ] Real backend from hasan (#12) wired into `rpc.main()`; then a success example for `snapshot` in the doc and a Windows manual check
- Next step: get hasan's approval on #135 and flip the ADR to Accepted; after #12 lands, wire the backend in and close #16

## Acceptance criteria (state on this branch)
- Binds only 127.0.0.1, token-less requests refused: met (`test_binds_to_loopback_only`, `test_handshake_without_the_token_is_refused`, query-string token test).
- ping, listWindows and snapshot work from a test client: met with the fake backend over a real WebSocket; on a real desktop only after #12.
- Every method documented with examples: `ping`, `listWindows` yes; `snapshot` has error examples only until the #12 schema exists.

## Manual checks
- none yet — nothing Windows-specific in this branch; CI's `agent` job runs the tests on `windows-latest`. Plan one for the Spy flow once the recognition backend is wired in.

## Open issues
- `agent/README.md` still says "Owners: galip (recognition, heal, RPC) · hasan (playback, CLI)", stale since ADR `2026-10-25-windows-work-to-hasan`; not in scope, tell hasan/omer.
- Every new ADR line in `memory-bank/decisions/README.md` conflicts with this branch (2026-10-29: twice); keep all lines in date order.
- TBD-5 in `docs/rs/scenarios.md` (step "not found" vs "timeout") is playback's boundary, not settled by `-32002`; hasan linked the two in his review.

## Handoff
- `serve_rpc()` is an async context manager; `bound_port(server)` gives the port when started with `port=0`.
- Python 3.11 raises `RecursionError` on deeply nested JSON (handled as a parse error); 3.15 parses it. The test accepts either error.
- `websockets` logs "connection handler failed" with a traceback for any exception escaping the handler; `ConnectionClosed` is caught so a vanished client does not spam stderr.
- `send()` of whole text messages is safe from concurrent tasks in websockets 17 (`send_context`), so request tasks send their own replies.
- The stdin watcher is a daemon thread, not `asyncio.to_thread`: `asyncio.run` would wait for a default-executor thread blocked on `read()` at shutdown.

## Outcome (fill when the issue closes)
