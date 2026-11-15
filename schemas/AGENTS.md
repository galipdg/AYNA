# schemas/ — Shared JSON Schemas (frozen contracts)

Owner: all three. Read `/AGENTS.md` first; this file adds only what is specific to `schemas/`.

## Layout
- Documents: `step.schema.json`, `element.schema.json`, `snapshot.schema.json`, `healing-proposal.schema.json` (version at `properties/version`)
- Messages: `ws-runs.schema.json` (live run status), `agent-rpc.schema.json` (client ↔ agent) (version at `$defs/version`)
- `examples/`: examples and named valid/invalid cases per schema

## Commands
The schemas have no build of their own. The step schema's tests run in the `ai/` module (CI job `ai`):
- from `ai/`: `pytest tests/test_step_schema.py` (setup: see `ai/AGENTS.md`)
- examples and named valid/invalid cases: `examples/step/`; add a case there for every rule you change
- breaking-change check, as the `contracts` CI job runs it (from the repository root): `python3 .github/contracts/schema_compat.py --base origin/main`

## Rules
- Any change needs an ADR and approval from all three owners.
- Bump the version on every change to the rules: minor for additions, major for anything that removes or narrows (ADR `2026-11-08-contracts-v1-freeze`). Update examples and tests in all consumers.
