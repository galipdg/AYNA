# #147 Step schema v0.2: select and check a grid/list row

- Issue: https://github.com/galipdg/AYNA/issues/147
- Owner: galip · Branch: `galip/147-step-schema-rows` (stacked on `galip/13-step-schema`, PR #134)
- Started: 2026-10-28 · Last update: 2026-10-28

## Approach
Smallest additive change that the #37 derivation accepts unchanged: a new keyword **SelectRow** with a required `row`, and three checkpoint properties (`cell`, `rowExists`, `rowCount`) that carry their own `row` / `column` inside the checkpoint. A row is `{index}` (1-based) or `{value, column?}` (exact cell text, first match from the top). Every rule is an `if`/`then` on `keyword` or on checkpoint `property`, so the schema enforces all of them. Version `"0.2"`; 0.1 documents migrate by relabelling. Decision, options, consequences and sources: ADR `2026-10-28-step-schema-v0-2-rows` (Proposed).

## Decisions (small, local to this task)
- 2026-10-28 — Row inside the checkpoint for Verify, on the step only for SelectRow — a step-level `row` for every keyword would tie two fields ("cell needs row", "Select needs value or row"), which neither an `if` on `keyword` nor the #37 derivation can express.
- 2026-10-28 — New keyword SelectRow rather than Select + row — Select requires `value` in v0; "value or row" needs a step-level `anyOf`, which #37 does not derive. The editor shows one more keyword.
- 2026-10-28 — `column` optional in the row key (any cell) — "the Yılmaz row" works without column metadata, which the NL assistant does not have yet; `column` required for `cell` checks, so lists (no headers, UIA List never has the Table pattern) get no `cell` check in 0.2 (relaxing later is compatible).
- 2026-10-28 — `cell` is a new property, not v0 `name` on a cell — WinForms cell Name is "header + row index", its Value is the text; cell text = ValuePattern value if present, else Name.
- 2026-10-28 — `rowCount` and `rowExists` allow only `equals` — the derivation cannot narrow an `enum` operator with another `enum`; "not empty" is `rowExists {index: 1}`.
- 2026-10-28 — Row checks re-read until they hold within `timeoutMs`; SelectRow waits for its row — grids fill after the grid itself is ready (SC-18). v0 checks unchanged.
- 2026-10-28 — Bounds: `index` 1–100000, `rowCount` 0–100000 (the #37 sampler needs a min and max on integers), `column` 1–100 chars, key `value` 1–1000.
- 2026-10-28 — `version` stays a `const` ("0.2"), not `enum ["0.1","0.2"]` — v0 ADR rule, and the generator reads `version.const`. No stored documents exist (#134 unmerged).
- 2026-10-28 — New cases carry `"since": "0.2"` so the tests can find the 0.1 cases and prove they still pass; consumers that read `cases.json` ignore the extra key (checked with #37's tests).

## Status
- [x] Branch, task note, board In progress
- [x] ADR (Proposed) + `decisions/README.md` line
- [x] `schemas/step.schema.json` 0.2, `schemas/README.md`, examples (`customer-search-grid.json`: 9 steps; `cases.json`: 7 + 12 valid, 29 + 37 invalid), `ai/tests/test_step_schema.py` (117 tests; 16 mutations drop a 0.2 rule each and a named invalid case gets through)
- [x] #37 compatibility (below)
- [ ] PR, reviews by hasan and omer; all three approve (criterion 1)
- [ ] After approval: #37, #36, #40, #38 adopt it (criterion 3)
- Next step: answer review comments on the PR; when all three approve, set the ADR to Accepted in the same PR; then open the follow-ups on #37 and #36.

## #37 compatibility check (2026-10-28, `origin/galip/37-constrained-generation` 95de284, scratch copy)
- `generation_schema()` derives the 0.2 schema with **no code change**: 6 keyword branches (SelectRow: keyword, target, row, timeoutMs), 5 checkpoint variants (name/value, booleans, cell, rowExists, rowCount), `row` as a nested `anyOf` of two closed objects, strings capped, no `if`/`then`/`allOf`/boolean subschemas left.
- New schema only, #37's tests as they are: 17 failed, 117 passed. Causes: tests and examples hard-code `"version": "0.1"` (15), the exact per-keyword field sets (1), the two-way checkpoint split (1).
- Schema + 0.2 examples + this branch's `test_step_schema.py`, `"0.1"` → `"0.2"` in `test_generate.py` / `test_generation_schema.py`: **2 failed, 243 passed**. The two are the v0 shape assertions (`test_fields_follow_the_per_keyword_rules`, `test_checkpoint_is_split_by_property_kind`). The "never wider" sampling test, "valid examples fit" and "invalid examples rejected" pass with the new cases.
- Live probe (Ollama local, 3 Turkish grid sentences, prompt + 4 lines on SelectRow/row checks, grid description with its columns): Ollama accepted the derived grammar; qwen3:8b and gemma4:e4b-it-qat 3/3 valid each; "2 kayıt, ilk satırın Şehir'i Ankara" and "Soyad'ı Yılmaz olan satırı seç" exactly right in both. "Tabloda Yılmaz listelenmeli": both chose `cell` instead of `rowExists`; qwen3 filled `column` with 100 characters of garbage (free string). Raw: scratch only, not committed.
- #37 follow-up after approval: read the version from the schema in tests; update the two shape tests; prompt lines for SelectRow and the three properties ("listelenmeli" → `rowExists`); narrow `column` to an `enum` of the known column headers.

## Manual checks
- none for the schema itself (no UI). The UIA assumptions are for hasan to check on #33 at a Windows session (cell text ValuePattern vs Name on a `QTableView`; RowCount without headers; SelectRow on a cell selects the row) — listed in hasan's inbox, not a criterion of #147.

## Open issues
- Asymmetry: row checks retry within `timeoutMs`, v0 checks read once after the smart wait. Whether v0 checks should retry too is a #40 question (v0 semantics), not decided here.
- RS FR-11 names the five keywords; add SelectRow on #35 once the ADR is accepted. SDD AI-3 known limit 2 then points to #37's adoption.
- WinForms grids with a new-record row ("(Create New)"): does Grid RowCount include it? Hasan, if a pilot app uses DataGridView (D1).

## Handoff
- `leaf_errors` flattens `anyOf` context, so an invalid row reports `required` / `additionalProperties` / `minimum` from inside the branches; name those as the case's `rule`.
- To find a rule in the tests use `rule_index(schema, definition, selector, test)` (matches the `if`'s const or enum), not a list position.

## Outcome (fill when the issue closes)
