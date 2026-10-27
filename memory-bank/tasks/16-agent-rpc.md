# #16 Agent JSON-RPC server (localhost only)

- Issue: https://github.com/galipdg/AYNA/issues/16
- Owner: galip · Branch: `galip/16-agent-rpc`
- Started: 2026-10-27 · Last update: 2026-10-27

## Approach
`agent/ayna_agent/rpc.py`: JSON-RPC 2.0 over a WebSocket on `127.0.0.1` (library `websockets`, asyncio API). The token is checked during the opening handshake, so an unauthenticated client never gets a socket. UI Automation stays out of `rpc.py`: the server takes a `Desktop` object (`list_windows()`, `snapshot(handle)`) that hasan's recognition layer will provide; tests use a fake one, so everything runs on macOS. Contract for the client: `docs/agent-rpc.md`; decisions that bind omer and hasan: ADR `2026-10-27-agent-rpc-v0` (Proposed).

## Decisions (small, local to this task)
- 2026-10-27 — Do #16 now although it depends on #12: only `snapshot` needs #12; transport, auth, `ping` and `listWindows` do not — galip's choice. PR says `Refs #16`; the issue closes when the real backend answers `snapshot`.
- 2026-10-27 — `websockets~=17.3` as a runtime dependency of `agent/` — galip approved.
- 2026-10-27 — The real UIA backend lives in `recognition/` (hasan, ADR `2026-10-25-windows-work-to-hasan`), not in `rpc.py` — galip's choice; request in hasan's inbox.
- 2026-10-27 — Results are objects (`{"windows": [...]}`), not bare arrays, so fields can be added without breaking clients.
- 2026-10-27 — Requests on one connection are handled one after another; UIA calls are serialised on one thread anyway, and WebSocket keepalive pings still run because the event loop never blocks.
- 2026-10-27 — Tests use `asyncio.run` in plain pytest functions instead of adding `pytest-asyncio`.

## Status
- [x] Branch, task note, board In progress
- [x] `rpc.py` + `tests/test_rpc.py` (50 tests pass on Python 3.11.13 and 3.15.1, ruff clean); manual run of `python -m ayna_agent.rpc` matched the doc's examples
- [x] `docs/agent-rpc.md`, ADR (Proposed), requests in hasan's and omer's inboxes
- [ ] PR (`Refs #16`), reviews by omer and hasan
- [ ] Real backend from hasan (#12) wired into `rpc.main()`; then a success example for `snapshot` in the doc and a Windows manual check
- Next step: open the PR after galip's OK; then wait for #12

## Acceptance criteria (state on this branch)
- Binds only 127.0.0.1, token-less requests refused: met (`test_binds_to_loopback_only`, `test_handshake_without_the_token_is_refused`, query-string token test).
- ping, listWindows and snapshot work from a test client: met with the fake backend over a real WebSocket; on a real desktop only after #12.
- Every method documented with examples: `ping`, `listWindows` yes; `snapshot` has error examples only until the #12 schema exists.

## Manual checks
- none yet — nothing Windows-specific in this branch; CI's `agent` job runs the tests on `windows-latest`. Plan one for the Spy flow once the recognition backend is wired in.

## Open issues
- `agent/README.md` still says "Owners: galip (recognition, heal, RPC) · hasan (playback, CLI)", stale since ADR `2026-10-25-windows-work-to-hasan`; not in scope, tell hasan/omer.
- `memory-bank/decisions/README.md` gets a line here and in PR #134; whichever merges second has a one-line conflict (keep both lines).
- `memory-bank/people/galip/active.md` is overwritten here and in PR #133; keep the newer one on merge.

## Handoff
- `serve_rpc()` is an async context manager; `bound_port(server)` gives the port when started with `port=0`.
- Python 3.11 raises `RecursionError` on deeply nested JSON (handled as a parse error); 3.15 parses it. The test accepts either error.
- `websockets` logs "connection handler failed" with a traceback for any exception escaping the handler; `ConnectionClosed` is caught so a vanished client does not spam stderr.

## Outcome (fill when the issue closes)
