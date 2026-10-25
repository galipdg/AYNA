# schemas/ — Shared JSON Schemas (frozen contracts)

Owner: all three. Read `/AGENTS.md` first; this file adds only what is specific to `schemas/`.

## Layout
- `step.schema.json`, `element.schema.json`, `snapshot.schema.json`

## Commands
To be filled in when the module is scaffolded (build, test, lint, run). Until then, ask before inventing tooling.

## Rules
- Any change needs an ADR and approval from all three owners.
- Bump the `version` field on every change and update examples and tests in all consumers.
