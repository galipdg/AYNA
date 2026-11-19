# The step status repairProposed on /ws/runs (ws-runs 1.2)

- Date: 2026-11-19
- Status: Proposed (#74). Needs Galip's and Hasan's approval: it changes a file in `schemas/`.
- Deciders: Ömerfaruk (server, client, contracts), Galip (agent RPC, healing), Hasan (playback)
- Issue: #74. Extends: ADR *Healing proposal transport* (`2026-10-28`), ADR *Contracts v1* (`2026-11-08-contracts-v1-freeze`), ADR *A failed step's category* (`2026-11-15`).

## Context
- The transport ADR gives a step result the status `repairProposed`: no element matched, the agent proposed candidates and acted on none. #74 makes the server accept and store such a result (`PUT /api/runs/{runId}/results/{stepIndex}`).
- The server forwards every new result live as `run.stepResult` on `/ws/runs`. In ws-runs 1.1, `$defs/stepStatus` is `passed | failed | notRun`, so this message would break the contract. The schema already says "#74 adds repairProposed".
- The transport ADR (#63 consequence) says a `repairProposed` step's category is "element not found". In 1.1 `category` is described for failed steps only.

## Options considered
1. **Send `failed` on the socket, `repairProposed` only over REST.** + No contract change. − Live and stored status disagree; the client cannot show "repair proposed" until it reloads.
2. **Add `repairProposed` to `stepStatus` (minor, 1.2).** + Live and stored status agree. Readers already show an unknown status as it is, so a 1.1 reader keeps working.

## Decision
**Option 2.** `schemas/ws-runs.schema.json` **1.2**:
- `$defs/stepStatus` adds `repairProposed`: the step was not performed, the run fails, and the proposal waits for review (`GET /api/healing/proposals/{id}`).
- `runStepResult.category` may be `elementNotFound` on a `repairProposed` step; the server refuses any other category there (400, `$.category`).
- `runStatus` is unchanged: a run with a `repairProposed` step ends as `failed` (the server's finish check counts it as a failed step).

## Consequences
- Client (omer): `client/src/shared/liveRun.ts` `STEP_STATUSES` lists only the three 1.1 statuses and drops a result with another one. It has to accept `repairProposed` and show it before #73 produces such results; this belongs with #75 (approval screen) or #73's client half.
- `agent-rpc.schema.json` `stepResult.status` needs the same value when #73 ships the producer (Galip and Hasan's bump, agent-rpc 1.3).
- No server change beyond #74: `RunEvents` already forwards the stored status.
