# #74 Healing proposals API

- Issue: https://github.com/galipdg/AYNA/issues/74
- Owner: omer · Branch: `omer/74-healing-api`
- Started: 2026-11-19 · Last update: 2026-11-19

## Approach
The shape is set by two ADRs: `2026-10-28-healing-proposal-transport` (Accepted) and `2026-10-31-healing-proposal-schema-0-2` (Proposed; `schemas/healing-proposal.schema.json` on `main` is already `"0.2"`).

- **Create.** No create endpoint. `PUT /api/runs/{runId}/results/{stepIndex}` takes `status: repairProposed` with `snapshot` and `healingProposal`. `RunService.store` calls `HealingService.createFromResult` in the same transaction, which checks the proposal, imports the snapshot (`SnapshotService.importInto`) and creates the proposal with its `CANDIDATE` edges. The answer is `{stepResultId, healingProposalId}`. The result's stored `body` leaves out the two members, because they live in the graph; the repeat hash still covers them.
- **Check.** `HealingProposalSchema` = schema 0.2 + the arithmetic of `ai/tests/test_healing_proposal_schema.py`, with the same rule names (message prefix `[sum]` etc.), exact `BigInteger` fractions. `cases.json` drives `HealingProposalSchemaTest`. Then it is checked against the result: runId, stepIndex, stepId, appVersionId, the step's target = `logicalName`, snapshotId, and every candidate in the snapshot. All errors are reported together, sorted by path.
- **Decide.** `GET /api/healing/proposals?status=&appVersionId=`, `GET …/{id}`, `POST …/{id}/approve {rank}`, `POST …/{id}/reject`. The proposal's write lock is taken before its status is read, so a second decision is a 409.
- **Graph.** `V0006` adds indexes `HealingProposal.status`, `createdAt`; `docs/graph-model.md` is now v0.7.

## Decisions (small, local to this task)
- 2026-11-19 — approve rewrites `primary`/`fallback` as well as `RESOLVES_TO` (omer). The keys stay; the values become the candidate Element's, and keys the element lacks are dropped. If no primary key is left, the answer is 409 ("edit the object instead"). Reason: playback finds objects by `primary/fallback`, not by `RESOLVES_TO`.
- 2026-11-19 — Rule = `objectId, appVersionId, elementId, previousElementId, previous/new primary+fallback, createdBy/At`, with `LEARNED_FROM` to the proposal and `FOR` to the object (omer).
- 2026-11-19 — a proposal outlives its run (retention, test delete): it is the decision's record. `stepResultId` is then null.
- 2026-11-19 — a `repairProposed` result may carry `category: elementNotFound` and no other category.
- 2026-11-19 — `bestScore` in the list is the exact string; screens convert it only to draw.

## Status
- [x] Branch from `main`, board In progress (2026-11-19)
- [x] Design OK from omer (approve rewrites primary/fallback; Rule; V0006)
- [x] `healing/` package, `RunService` write path, `V0006`, graph-model v0.7, OpenAPI regenerated; 187 server tests pass (20 new: `HealingProposalSchemaTest` 4, `HealingIntegrationTest` 16)
- [ ] `ws-runs` contract: a `repairProposed` result goes out on `/ws/runs` with a status that 1.1's `stepStatus` enum does not list (see Open issues)
- Next step: settle the ws-runs bump with omer, then push and open the PR (`Closes #74`; reviewers galip, hasan).

## Manual checks
- None needed: the API is fully covered by the integration tests. #75 (approval screen) will need a by-hand check.

## Open issues
- **ws-runs 1.1** `$defs/stepStatus` is `passed|failed|notRun`; its description says "#74 adds repairProposed" (minor bump). `schemas/` is shared, so it needs omer's OK and a note to galip/hasan.
- **agent-rpc** `runSteps` result `status` does not list `repairProposed` either. That is #73's bump (hasan/galip), not this issue's.
- ADR `2026-10-31-healing-proposal-schema-0-2` is still Proposed although its schema is on `main`; this code accepts only `"0.2"`.
- #73 (producer) is open, so there is no end-to-end run yet; the tests use the shared examples with the trial-login snapshot plus the three candidates.
- Not tested: approve after the object was deleted (409 by code).

## Handoff
- `HealingService.createFromResult` runs inside `RunService.store`'s transaction; a constraint race on the snapshot id is retried by `writeResult` like a result race.

## Outcome (fill when the issue closes)
