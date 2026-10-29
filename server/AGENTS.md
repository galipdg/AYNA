# server/ — Spring Boot server and Neo4j migrations

Owner: omer. Read `/AGENTS.md` first; this file adds only what is specific to `server/`.

## Layout
- packages by feature: `apps`, `repository`, `tests`, `runs`, `healing`, `impact`, `auth`
- `src/main/resources/neo4j/migrations/` — graph schema migrations

## Commands
Java 21 and Docker are required. Run from `server/` unless noted; if `JAVA_HOME` is wrong, prefix with `JAVA_HOME=$(/usr/libexec/java_home -v 21)` (macOS).
- Test (unit + Testcontainers integration, Docker must be running): `./mvnw test`
- Build the jar: `./mvnw package`
- Whole backend (from the repo root): `docker compose up --build`, then `curl localhost:8080/api/health`

## Rules
- Graph schema changes only through a new migration + ADR (contract).
- Validate steps against `schemas/step.schema.json` on every write.
- REST changes must keep `docs/api/openapi.yaml` generation green: `./mvnw test` regenerates the file (`OpenApiContractIntegrationTest`); commit it with the change, or CI fails. Swagger UI: `localhost:8080/swagger-ui.html`.
