# server/ — Spring Boot server and Neo4j migrations

Owner: omer. Read `/AGENTS.md` first; this file adds only what is specific to `server/`.

## Layout
- packages by feature: `apps`, `repository`, `tests`, `runs`, `healing`, `impact`, `auth`
- `src/main/resources/neo4j/migrations/` — graph schema migrations

## Commands
To be filled in when the module is scaffolded (build, test, lint, run). Until then, ask before inventing tooling.

## Rules
- Graph schema changes only through a new migration + ADR (contract).
- Validate steps against `schemas/step.schema.json` on every write.
- REST changes must keep `docs/api/openapi.yaml` generation green.
