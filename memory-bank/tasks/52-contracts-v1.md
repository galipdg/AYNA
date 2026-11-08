# #52 Freeze REST, WebSocket and JSON-RPC contracts v1

- Issue: https://github.com/galipdg/AYNA/issues/52
- Owner: omer · Branch: `omer/52-contracts-v1`
- Started: 2026-11-08 · Last update: 2026-11-08

## Approach
Decision and reasons: ADR `memory-bank/decisions/2026-11-08-contracts-v1-freeze.md`. In short: v1 is today's shape, and afterwards only additions; breaking changes need a major version.
- REST: `OpenApiConfig.CONTRACT_VERSION = "1.0"`; `.github/contracts/rest_compat.sh` runs oasdiff 1.34.1 `breaking --fail-on WARN` (levels in `oasdiff-levels.txt`) against the base branch.
- WebSocket: new `schemas/ws-runs.schema.json` 1.0; `RunEventsIntegrationTest` validates every message.
- Agent JSON-RPC: new `schemas/agent-rpc.schema.json` 1.0; client side `client/src/main/__tests__/agentContract.test.ts`; agent side requested from galip (inbox).
- All `schemas/*.schema.json`: `.github/contracts/schema_compat.py` (stdlib, unittest tests next to it).
- CI: new `contracts` job in `.github/workflows/ci.yml`.

## Decisions (small, local to this task)
- 2026-11-08: the user chose all four recommendations (additions-only freeze, oasdiff, JSON Schema plus a diff script, an inbox request for the agent side).
- 2026-11-08: the two new schemas live in `schemas/`, not `docs/api/`. They are shared contracts and fall under the same rules as the others.
- 2026-11-08: the document schemas keep 0.x. A breaking change takes them to 1.0, because renumbering would invalidate stored data.
- 2026-11-08: oasdiff fails on WARN. In 1.34.1, `response-optional-property-removed` is only INFO, and our generated OpenAPI has no `required` on responses, so `oasdiff-levels.txt` raises that one check to ERR (found by trying it). The 19 WARN checks are all real risks, and none fires on an addition.
- 2026-11-08: the checker fails closed. It understands `$ref` refactors and per-keyword `if/then` rules that only fire on new values, because the step schema's 0.1 → 0.2 change was additive and must pass.
- 2026-11-08: the oasdiff version is pinned to a release at least two weeks old (1.34.1, 2026-10-21), and CI checks its SHA-256.

## Status
- [x] Checker + 28 tests; no false positives on any of the 6 past schema commits
- [x] ws-runs and agent-rpc schemas; server WS test validates (and fails when the schema is broken)
- [x] Client contract test; it found the null `processId` that the Spy's window list dropped (fixed)
- [x] REST 1.0, OpenAPI regenerated; server 119/119, client 207/207, lint and typecheck clean
- [x] oasdiff 1.34.1 run locally: a removed response field and a removed endpoint fail, an added field passes, and v0 → 1.0 is allowed
- Next step: commit, then push and open the PR on omer's OK (reviewers galip and hasan for the ADR).

## Manual checks
None: everything here runs in CI.

## Open issues
- SDD §4.1 / §4.3 / §6.2 still say "v0" and "at #52". `docs/sdd/SDD.md` is changed by the open #222, so update it after #222 merges (or in #53).
- Agent side (RPC_VERSION 1.0, reply validation, doc title) is galip's. Requested in his inbox on 2026-11-08.
- The AI service API (`ai/API.md`) is not covered by the job yet (ADR Consequences).
- A git tag `contracts-v1` after merge: the team's call.

## Handoff
- The `contracts` job compares with `origin/<base>` on PRs and with `github.event.before` on pushes. Local runs: `python3 .github/contracts/schema_compat.py --base origin/main` and `.github/contracts/rest_compat.sh origin/main <oasdiff>`.

## Outcome (fill when the issue closes)
