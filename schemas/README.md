# schemas/

JSON Schemas shared by every component: test steps, repository elements and UI snapshots. These are frozen contracts; changing one needs an ADR and approval from all three members.

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
