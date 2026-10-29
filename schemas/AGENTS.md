# schemas/ — Shared JSON Schemas (frozen contracts)

Owner: all three. Read `/AGENTS.md` first; this file adds only what is specific to `schemas/`.

## Layout
- `step.schema.json`, `element.schema.json`, `snapshot.schema.json`

## Commands
The schemas have no build of their own. The step schema's tests run in the `ai/` module (CI job `ai`):
- from `ai/`: `pytest tests/test_step_schema.py` (setup: see `ai/AGENTS.md`)
- examples and named valid/invalid cases: `examples/step/`; add a case there for every rule you change

## Rules
- Any change needs an ADR and approval from all three owners.
- Bump the `version` field on every change and update examples and tests in all consumers.
