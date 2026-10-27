# #13 Step JSON Schema v0

- Issue: https://github.com/galipdg/AYNA/issues/13
- Owner: galip · Branch: `galip/13-step-schema`
- Started: 2026-10-27 · Last update: 2026-10-27

## Approach
`schemas/step.schema.json` (JSON Schema 2020-12) describes a *step list document* `{version, steps}`; one step is `#/$defs/step`, so APIs that pass a single step can reference it. Keyword-specific fields are enforced with `if`/`then`. Examples live in `schemas/examples/step/`: a saved login test (`login-test.json`) and named valid/invalid cases (`cases.json`). Tests: `ai/tests/test_step_schema.py` with `jsonschema`, so CI's `ai` job runs them. Decisions that bind other people go into the ADR `2026-10-27-step-schema-v0`.

## Decisions (small, local to this task)
- 2026-10-27 — Version at the document root (`"version": "0.1"`), not per step — galip's choice; a test, an NL answer or a `runSteps` call carries one version, same shape as the #7 spike's `{steps: [...]}`.
- 2026-10-27 — `timeoutMs`, not the issue's `timeout_ms` — galip's choice; every other JSON contract (server DTOs, graph properties, client settings) is camelCase.
- 2026-10-27 — `jsonschema~=4.26` added to `ai/` (runtime: `ayna_ai/validate.py` will need it in #71); tests in `ai/tests/` — galip approved the dependency.
- 2026-10-27 — Wait = wait until the target exists, is visible and enabled, at most `timeoutMs`; no fixed sleeps; "wait until gone" is left for a later version — galip's choice.
- 2026-10-27 — Start strict (closed enums, `additionalProperties: false`, exact `screen.element` names): relaxing later does not break stored tests, tightening does.

## Status
- [x] Branch, task note, board In progress
- [x] `schemas/step.schema.json` v0.1, examples (`login-and-customer.json`: 14 steps; `cases.json`: 7 valid, 29 invalid), `ai/tests/test_step_schema.py` (44 tests pass; mutating three rules made 7 fail, so the cases bite), ADR (Proposed), `schemas/README.md` + `schemas/AGENTS.md` Commands
- [x] PR https://github.com/galipdg/AYNA/pull/134 opened 2026-10-27, reviewers omer and hasan
- [ ] Approval by omer and hasan (acceptance criterion 4)
- Next step: address review comments on #134; when all three approve, set the ADR to Accepted (and its README line) in the same PR

## Manual checks
- none (no UI)

## Open issues
- `docs/graph-model.md` (omer) lists Step properties `keyword, value, checkpoint`; it needs `timeoutMs`, and `checkpoint` cannot be a Neo4j map — noted in omer's inbox.
- The issue says `timeout_ms`; v0 uses `timeoutMs` (ADR). Say so in the PR so nobody builds on the issue text.

## Handoff
- `jsonschema` reports a boolean `false` subschema (used for "keyword X does not take field Y") with `validator=None`; the tests map that to the rule name `false`.
- A single step is validated by `$ref` to `urn:ayna:schema:step#/$defs/step` through a `referencing.Registry` (see the test).

## Outcome (fill when the issue closes)
