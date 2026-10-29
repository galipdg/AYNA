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
