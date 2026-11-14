# schemas/

JSON Schemas shared by every component: test steps, repository elements, UI snapshots and healing proposals, and the messages of the live run status and agent JSON-RPC contracts. These are frozen contracts; changing one needs an ADR and approval from all three members.

**Frozen at G1 (#52, ADR [`2026-11-08-contracts-v1-freeze`](../memory-bank/decisions/2026-11-08-contracts-v1-freeze.md)).** Every change to a schema's rules bumps its version: minor for additions (a new optional property, enum value or rule for a new value), major for anything that removes or narrows. Readers ignore what they do not know. The `contracts` CI job compares every schema with the base branch and fails on a breaking change without a new major version; run it locally from the repository root with `python .github/contracts/schema_compat.py --base origin/main`.

Owners: all three. Rules: [AGENTS.md](AGENTS.md).

## Step schema (`step.schema.json`, version 0.2)

A document `{"version": "0.2", "steps": [...]}`; one step is `step.schema.json#/$defs/step`. Decisions and reasons: [`2026-10-27-step-schema-v0`](../memory-bank/decisions/2026-10-27-step-schema-v0.md) and [`2026-10-28-step-schema-v0-2-rows`](../memory-bank/decisions/2026-10-28-step-schema-v0-2-rows.md) (grid and list rows).

| Keyword | `target` | `value` | `row` | `checkpoint` | Meaning |
|---|---|---|---|---|---|
| Click | required | — | — | — | Click the target |
| Type | required | required (may be empty) | — | — | Replace the target's text with `value` |
| Select | required | required, non-empty | — | — | Choose the item whose text is `value` (list, combo box) |
| SelectRow | required (grid or list) | — | required | — | Select that row of the target; afterwards only it is selected |
| Verify | required | — | — | required | Check `checkpoint` on the target |
| Wait | required | — | — | — | Wait until the target exists, is visible and enabled |

Every step may have `id` (UUID, set by the server) and `timeoutMs` (longest smart wait before acting; for SelectRow and row checks it also covers waiting for the row or the check).

**Checkpoint properties**

| `property` | Reads | Needs | `operator` | `expected` |
|---|---|---|---|---|
| `name`, `value` | the target's UIA Name / ValuePattern value | — | `equals`, `notEquals`, `contains` | string |
| `enabled`, `visible`, `checked`, `selected` | the target's state | — | `equals` | boolean |
| `cell` | the text of one cell of a grid | `row`, `column` | `equals`, `notEquals`, `contains` | string |
| `rowExists` | whether a row of a grid or list matches | `row` | `equals` | boolean |
| `rowCount` | number of rows of a grid or list (headers not counted) | — | `equals` | integer 0–100000 |

**Rows.** `row` is either `{"index": n}` — the n-th row from the top, counted from 1 — or `{"value": "Yılmaz", "column": "Soyad"}` — the first row with a cell whose text is exactly `value`, in that column if `column` is given, else in any column. `column` is the column header's text. A cell's text is its ValuePattern value when that value is non-empty, else its Name (Qt cells: empty Value, text in Name; WinForms cells: Name is the header and row index, text in Value). For a list, the row is the list item itself: `cell` is grid-only (a list has no columns), and `rowCount` of a list counts its items.

**From 0.1.** Every 0.1 step is a valid 0.2 step; a 0.1 document becomes 0.2 by changing only `version`.

Examples: [`examples/step/login-and-customer.json`](examples/step/login-and-customer.json) (a saved test written for 0.1; the login part matches the trial app of #9, the customer part is made up), [`examples/step/customer-search-grid.json`](examples/step/customer-search-grid.json) (search, check and select grid rows on the sample app's list screen; names and column headers are assumptions until #33 lands) and [`examples/step/cases.json`](examples/step/cases.json) (named valid and invalid cases used by the tests).

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

## Live run status (`ws-runs.schema.json`, version 1.0)

Every message on the WebSocket `/ws/runs`: `subscribe` and `unsubscribe` from the client; `subscribed`, `run.started`, `run.stepResult`, `run.finished` and `error` from the server, told apart by `type`. The root schema accepts any one of them; each is also a `$defs` entry. The version is `$defs/version`; it is not sent on the wire. Decision: [`2026-11-05-runs-api-and-live-updates`](../memory-bank/decisions/2026-11-05-runs-api-and-live-updates.md). Code: `server/src/main/java/com/ayna/server/runs/RunEvents.java`. Tests: `RunEventsIntegrationTest` checks every message it sends and receives against this file.

## Agent JSON-RPC (`agent-rpc.schema.json`, version 1.0)

The shapes of the client ↔ agent messages: the five requests (`ping`, `listWindows`, `snapshot`, `elementFromPoint`, `runSteps`), success and error replies, a `<method>Result` per method (a reply does not name its method), the error codes, and the agent's `listening` line on stdout. `snapshotResult` only names the snapshot document's top level; the document itself is `snapshot.schema.json`. Version 1.0 is v0.1 as built plus `runSteps`; `ping` answers `rpcVersion`, and a 1.x client accepts any 1.y agent. The prose contract (start-up, token, ordering, behaviour) stays in [`docs/agent-rpc.md`](../docs/agent-rpc.md). Tests: `client/src/main/__tests__/agentContract.test.ts` (client side).
