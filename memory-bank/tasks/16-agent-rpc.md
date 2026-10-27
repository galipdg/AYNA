# #16 Agent JSON-RPC server (localhost only)

- Issue: https://github.com/galipdg/AYNA/issues/16
- Owner: galip · Branch: `galip/16-agent-rpc`
- Started: 2026-10-27 · Last update: 2026-10-27

## Approach
`agent/ayna_agent/rpc.py`: JSON-RPC 2.0 over a WebSocket on `127.0.0.1` (library `websockets`, asyncio API). The token is checked during the opening handshake, so an unauthenticated client never gets a socket. UI Automation stays out of `rpc.py`: the server takes a `Desktop` object (`list_windows()`, `snapshot(handle)`) that hasan's recognition layer will provide; tests use a fake one, so everything runs on macOS. Contract for the client: `docs/agent-rpc.md`.

## Decisions (small, local to this task)
- 2026-10-27 — Do #16 now although it depends on #12: only `snapshot` needs #12; transport, auth, `ping` and `listWindows` do not — galip's choice. PR says `Refs #16`; the issue closes when the real backend answers `snapshot`.
- 2026-10-27 — `websockets~=17.3` as a runtime dependency of `agent/` — galip approved.
- 2026-10-27 — The real UIA backend lives in `recognition/` (hasan, ADR `2026-10-25-windows-work-to-hasan`), not in `rpc.py` — galip's choice; request in hasan's inbox.

## Status
- [x] Branch, task note, board In progress
- [ ] `rpc.py`, tests, `docs/agent-rpc.md`
- Next step: write `rpc.py` and its tests

## Manual checks
- none yet

## Open issues

## Handoff

## Outcome (fill when the issue closes)
