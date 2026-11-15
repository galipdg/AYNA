# A failed step's category in the agent, WebSocket and REST contracts (FR-35)

- Date: 2026-11-15
- Status: Proposed (#63). Needs Galip's and Hasan's approval: it changes two files in `schemas/`.
- Deciders: Ömerfaruk (server, client, contracts), Hasan (playback, #63 triage), Galip (agent RPC)
- Issue: #63 (FR-35, TBD-5). Extends: ADR *Contracts v1* (`2026-11-08-contracts-v1-freeze`), ADR *Runs API and live run updates* (`2026-11-05`).

## Context
- FR-35: the agent puts every failed step in exactly one category (element not found, unexpected window, assertion failed, timeout, search incomplete; TBD-5 closed 2026-10-29), and the client shows the category with the step.
- The contracts froze as 1.0 on 2026-11-15 (#224). None of them has a place for the category. The agent's `stepResult` has `additionalProperties: false`, so the agent cannot send one until the schema allows it.
- Hasan's playback v1 (#40, PR #237) already knows the boundary in code: `NotFound` and `Ambiguous` are "element not found", but it fails some steps that are in no category: a step it refuses (`Unsupported`) and an action the application rejects (`ActionFailed`).
- No client screen shows step results yet. That screen is #44's client half.

## Options considered
1. **Category in `message` text** (for example `"[timeout] …"`). + No contract change. − Every reader parses text, and a translated report cannot label it.
2. **A new `status` per category** (`failedTimeout`, …). + One field. − Every reader that checks `status == failed` breaks, and the run's pass/fail logic (`finishRun`) has to learn five statuses.
3. **An optional `category` beside `status`, only on a failed step.** + Additive, so a minor version under the freeze. Old readers ignore it. − One more field to keep in step across three contracts.

## Decision
**Option 3.**

- Values (camelCase, as other enums): `elementNotFound`, `unexpectedWindow`, `assertionFailed`, `timeout`, `searchIncomplete`. Meanings as TBD-5. "More than one element matched" is `elementNotFound` (as #40's code says). New values come in a minor version, and readers show an unknown value as it is.
- **Only with `status: failed`**, at most one. The agent leaves it out when it cannot tell (a refused step, a rejected action). FR-35 says "every failed step"; whether those two cases get a category of their own, or one of the five, is Hasan's call in #63. Until then, absent means "not classified".
- Contracts:
  - `schemas/agent-rpc.schema.json` **1.1**: `stepResult.category`, `$defs/failureCategory`.
  - `schemas/ws-runs.schema.json` **1.1**: `runStepResult.category`, nullable, not required (a 1.0 server leaves it out).
  - REST (additive, stays 1.x): `StepResultResponse.category`, nullable. `PUT /api/runs/{runId}/results/{stepIndex}` takes it from the agent's `stepResult`.
- Server: refuses an unknown category and a category on a step that did not fail (400, path `$.category`). Stores it as the StepResult property `category` (graph model v0.6, no migration: older results simply have none). The HTML report shows it in bold above the message, in the report's language.
- Client: shows it with the step on the run screen (#44's client half), with the same words as the report.

## Consequences
- Hasan's #63 fills the field in playback. `docs/agent-rpc.md` (Hasan and Galip) needs `category` in the `runSteps` result list and in the `run.stepResult` draft, which today says #63 "adds its own fields": requested in their inboxes.
- A 1.0 client accepts a 1.1 agent, which is why the client's `rpcVersion` check is `^1\.`.
- Revisit if triage (#63) finds a failure that fits none of the five. A sixth value is a minor version.
