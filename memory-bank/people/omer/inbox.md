# Inbox — Ömerfaruk Sarıbal (`omer`)

Anyone may append; only omer removes handled items. Format:
`- YYYY-MM-DD · from <id> · #<issue> · <request or note>`

- 2026-10-25 · from galip · ADR windows-work-to-hasan · You took over #18 (tool comparison matrix) and #48 (SDD test-design section) from hasan, and now own `docs/sdd/` (each component owner still writes their own section). Your Windows-checked client issues (#24, #44, #75, #100) and the installer/air-gapped tests (#84, #85, #91, #108) stay with you.
- 2026-10-27 · from galip · #16 · The client ↔ agent contract is in `docs/agent-rpc.md` (ADR `2026-10-27-agent-rpc-v0`, Proposed, needs your approval in the #16 PR). For the client: spawn `python -m ayna_agent.rpc --port 0` with a fresh random token in the env var `AYNA_AGENT_TOKEN` (not on the command line); read the one JSON line on stdout `{"event":"listening","port":n}`; connect from the **main process** to `ws://127.0.0.1:<port>` with header `Authorization: Bearer <token>` (browsers cannot set it, so the renderer cannot connect directly; any Node client that sets headers works, e.g. `ws`); kill the process tree on quit (`taskkill /F /T`). Methods now: `ping`, `listWindows`; `snapshot` answers `-32001` until hasan's backend (#12) lands.
