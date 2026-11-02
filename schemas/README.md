# schemas/

JSON Schemas shared by every component: test steps, repository elements and UI snapshots. These are frozen contracts; changing one needs an ADR and approval from all three members.

Owners: all three. Rules: [AGENTS.md](AGENTS.md).

## Step schema (`step.schema.json`, version 0.1)

A document `{"version": "0.1", "steps": [...]}`; one step is `step.schema.json#/$defs/step`. Decision and reasons: [`2026-10-27-step-schema-v0`](../memory-bank/decisions/2026-10-27-step-schema-v0.md).

| Keyword | `target` | `value` | `checkpoint` | Meaning |
|---|---|---|---|---|
| Click | required | — | — | Click the target |
| Type | required | required (may be empty) | — | Replace the target's text with `value` |
| Select | required | required, non-empty | — | Choose the item whose text is `value` |
| Verify | required | — | required | Check `checkpoint` on the target |
| Wait | required | — | — | Wait until the target exists, is visible and enabled |

Every step may have `id` (UUID, set by the server) and `timeoutMs` (longest smart wait before acting). Checkpoint properties: `name`, `value` (string `expected`; `equals`, `notEquals`, `contains`) and `enabled`, `visible`, `checked`, `selected` (boolean `expected`; `equals` only).

Examples: [`examples/step/login-and-customer.json`](examples/step/login-and-customer.json) (a saved test; the login part matches the trial app of #9, the customer part is made up) and [`examples/step/cases.json`](examples/step/cases.json) (named valid and invalid cases used by the tests).

## Healing proposal (`healing-proposal.schema.json`, version 0.2 proposed)

The top candidates the agent proposes when a step's target matches nothing; the document rides inside the failing step's result to the server. Exact fractions as strings, per-element `dpi`, and the feature versions that derived the target's and the candidates' properties. Decisions: [`2026-10-28-healing-proposal-transport`](../memory-bank/decisions/2026-10-28-healing-proposal-transport.md) (0.1, accepted) and [`2026-10-31-healing-proposal-schema-0-2`](../memory-bank/decisions/2026-10-31-healing-proposal-schema-0-2.md) (0.2, proposed). Field reference: `docs/agent-rpc.md`, "Proposed (#149)".

Examples: [`examples/healing-proposal/`](examples/healing-proposal/) (numbers produced by the scorer of #49) and its `cases.json`. Tests: `ai/tests/test_healing_proposal_schema.py`.

## Element descriptor (`element.schema.json`, version 0.1)

A document `{"version": "0.1", "element": {...}}`: one UI element as the agent captured it — what it is (`automationId`, `name`, `controlType`, `className`, `frameworkId`), where it sits (`parentPath`, `siblingIndex`), what is around it (`nearestLabel` with `nearestLabelSource`, `windowTitle`), its geometry (`bounds` in physical pixels with `dpi`) and its state (`enabled`, `offscreen`). Every property is optional, because no framework fills them all in, and a blank string is never stored. The set is a superset of the healing proposal's `scoredElement`, so a stored element can always be rebuilt into a scorer input. Decision and the normative rules for the three computed properties: [`2026-10-31-element-descriptor-v0`](../memory-bank/decisions/2026-10-31-element-descriptor-v0.md). Code: `agent/ayna_agent/model.py`. Tests: `agent/tests/test_model.py`.

Examples: [`examples/element/cases.json`](examples/element/cases.json) (named valid and invalid cases, every element taken from a real dump).

## Window snapshot (`snapshot.schema.json`, version 0.1 proposed)

One window's whole subtree at one moment: `{version, snapshotId, capture, app, window, elements}`. `elements` is a **flat array in pre-order** — the window's own root element first, a parent always before its children — of `{id, parentId, element}`, where `element` is the descriptor above. So one pass builds the tree, which is what the server's import (#15) and the Spy's tree (#24) do. `id` is opaque: a healing proposal's `candidates[].elementId` resolves against it.

`capture` records what the walk cost (`startedAt`, `durationMs`, `budgetMs`, `elementCount`, `readErrors`, `agentVersion`, `featureVersion`), because a UIA walk can be 100× slower than normal when the application stops pumping messages (#161, measured in `eval/spikes/uia-walk-cost.md`, which lands with PR #170). A walk that passes its budget is the error `-32002` and produces **no document at all**: a partial tree would let healing rank candidates it must not rank (RS 0.6 FR-29/FR-35, "search incomplete").

Decision: [`2026-11-01-snapshot-schema-v0`](../memory-bank/decisions/2026-11-01-snapshot-schema-v0.md). Transport: `docs/agent-rpc.md`, method `snapshot`. Code: `agent/ayna_agent/recognition/snapshot.py` (`build`, `dumps`, `loads`, `read`, `write`). Tests: `agent/tests/test_snapshot.py`.

Examples: [`examples/snapshot/trial-login.json`](examples/snapshot/trial-login.json) (the trial app's login window, 14 elements, rebuilt by the tests from the tree captured on Windows for #11, so the example cannot drift from the agent) and [`examples/snapshot/cases.json`](examples/snapshot/cases.json).
