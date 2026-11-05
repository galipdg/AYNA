# #44 Run tests from the editor with live status

- Issue: https://github.com/galipdg/AYNA/issues/44
- Owner: omer · Branch: `omer/44-run-api` (server half, from `main`)
- Started: 2026-11-05 · Last update: 2026-11-05

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

## Decisions (small, local to this task)
- 2026-11-05 — Follow schema 0.2 ADR point 7 (409 for a repeat with another body), not the SDD row "never 409". The ADR is still Proposed in the index, but it came from omer's own review and `docs/agent-rpc.md` already says the same. Fix the SDD row here.
- 2026-11-05 — The plain `PUT` moves from #51 to this PR, because #44's criteria need it. #51 keeps `repairProposed`, screenshots, retention, idle timeout.
- 2026-11-05 — No block on deleting a test with a `running` run: with no idle timeout yet, a run whose client died would block the delete forever.

## Status
- [x] Branch from `main`, #44 In progress on the board
- [x] ADR, `V0004`, `spring-boot-starter-websocket` (omer's OK 2026-11-05)
- [x] REST (`runs/RunController`, `RunService`), test delete removes runs; `RunIntegrationTest`
- [x] `/ws/runs` (`RunEvents`, `RunEventsConfig`), 60 s token re-check; `RunEventsIntegrationTest` (real port, real client)
- [x] `docs/graph-model.md` v0.3, SDD rows, OpenAPI regenerated; 86 server tests
- [ ] Push and PR `Part of #44`, reviewers galip and hasan (ask omer first)
- [ ] Client half: Run panel, outbox, `runSteps` (needs #38 on `main` and #40)
- Next step: on omer's OK, `git fetch`, merge `origin/main` if it moved, push `omer/44-run-api`, open the PR.

## Manual checks
- 2026-11-05 · agent · real Docker image on a fresh volume, Node's WebSocket as in `client/src/main/agent.ts` · pass, 15/15: bad or missing token refused, no `Origin` header needed, all three events reach the watcher, repeat not broadcast, 409 as a problem, step to watcher 69 ms (NFR-06: 1 s), logout closes with 1008 after 58.7 s through the real scheduler · evidence: run log in this session; the first run's one failure was the smoke script's stale waiter, not the server.
- Retry path checked by removing it: `overlappingRetriesStoreOneResult` then fails with `ConstraintValidationFailed`.
- Server half: no human step needed. Plan a check for the client half (two clients on one test, SC-17) while designing that screen.

## Open issues
- `docs/agent-rpc.md` says the REST contract is #51's and #74's. Galip's file: note on the PR.
- A run whose client never comes back stays `running` until #51's idle timeout.

## Handoff
- SSH to GitHub times out: fetch with `git -c url."https://github.com/".insteadOf="git@github.com:" fetch origin`.
- This work runs in the worktree `.claude/worktrees/pr-review-merge-stack-a13b07`; the main checkout is on `omer/38-step-editor`.
- Expect conflicts with the stack only in generated or shared docs: `docs/api/openapi.yaml`, `docs/graph-model.md`, `OpenApiConfig.java`. The stack adds no migration, so `V0004` is free.

## Outcome (fill when the issue closes)
