# #14 Neo4j graph schema v0 + migrations

- Issue: https://github.com/galipdg/AYNA/issues/14
- Owner: omer · Branch: `omer/14-graph-schema`
- Started: 2026-10-25 · Last update: 2026-10-26

## Approach
- neo4j-migrations Spring Boot starter applies `server/src/main/resources/neo4j/migrations/V*.cypher` on start (ADR `2026-10-25-graph-schema-migrations.md`).
- `V0001__graph_schema_v0.cypher`: a unique `id` constraint for each of the 11 labels in `architecture.md`, plus 5 lookup indexes.
- `docs/graph-model.md`: Mermaid diagram, node table, one sample query per relationship (relationships taken unchanged from `architecture.md`).
- `GraphSchemaMigrationIntegrationTest` (Testcontainers) checks constraints, indexes and the recorded migration.

## Decisions (small, local to this task)
- 2026-10-25 — indexes: `Application.name`, `RepoObject.name`, `Element.snapshotId`, `Element.automationId`, `Run.startedAt` — the lookups #15, #25, #39 and #68 need first; omer OK.
- 2026-10-25 — `RESOLVES_TO.version` holds the `AppVersion.id` — the architecture names only `{version}`.
- 2026-10-25 — `docs/graph-model.md` is in hasan's `docs/` area but the issue names it; FYI sent to hasan's inbox.

## Status
- [x] Dependency `neo4j-migrations-spring-boot-starter:4.2.0` (omer OK), migration, integration test
- [x] `./mvnw test` green locally (5 tests)
- [x] `docker compose up --build`: server log "Applied migration 0001"; `SHOW CONSTRAINTS` lists the 11 `id` constraints; all 14 sample queries pass `EXPLAIN`; after `docker compose restart server` the log says "Skipping already applied migration 0001"
- [x] `docs/graph-model.md`, ADR
- [x] PR #124 (`Closes #14`); CI run 40290795067 all four jobs green (server job ran the new integration test)
- Next step: review + merge by a human; then pick the next issue (#32 has its deps done).

## Manual checks
None needed; nothing user-visible.

## Open issues
- None yet.

## Handoff
- Tests or queries that list constraints/labels must skip `__`-prefixed names (neo4j-migrations' own lock and history nodes).

## Outcome (fill when the issue closes)
