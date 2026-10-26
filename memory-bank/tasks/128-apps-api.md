# #128 Applications and versions API (create + list)

- Issue: https://github.com/galipdg/AYNA/issues/128
- Owner: omer · Branch: `omer/128-apps-api`
- Started: 2026-10-26 · Last update: 2026-10-26

## Approach
Package `server/src/main/java/com/ayna/server/apps/`: `AppController` (REST, input checks) → `AppService` (plain Cypher through the Neo4j `Driver`, like `HealthController`; no Spring Data entities yet). Errors are exceptions with `@ResponseStatus` (400 / 404 / 409). Integration test `AppIntegrationTest` (Testcontainers, MockMvc) clears domain nodes before each test and keeps the `__Neo4jMigration` nodes.

## Decisions (small, local to this task)
- 2026-10-26 — Duplicate app names and duplicate versions are checked in the same write transaction as the create, not by a constraint (user chose option (a)) — keeps the graph schema contract unchanged. Two concurrent creates of the same name can both succeed; a "version unique per app" rule cannot be a Community constraint anyway.
- 2026-10-26 — `technology` is a free, non-blank string (user's choice); no list of allowed values exists yet.
- 2026-10-26 — No `spring-boot-starter-validation`: blank/missing `name`, `technology`, `version` → 400 by a small check in the controller, so no new dependency. Values are trimmed.
- 2026-10-26 — `POST` returns 201 with a `Location` header. `GET /api/apps/{id}/versions` returns 404 for an unknown app, the same as `POST`.
- 2026-10-26 — Versions are listed by their `version` string (lexicographic: "1.10" before "1.9"). There is no `createdAt` in the graph model; revisit if the picker needs creation order.

## Status
- [x] four endpoints + integration test (7 cases); `./mvnw -B verify` green on 2026-10-26
- [x] pushed; PR #129 open (`Closes #128`) on 2026-10-26
- Next step: wait for #129 CI + review; meanwhile build #32's application picker on `GET /api/apps` on `omer/32-server-settings`

## Manual checks
- None needed: everything is covered by `AppIntegrationTest`.

## Open issues
- Acceptance criterion "`docs/api/openapi.yaml` generation stays green" cannot be checked yet: generation does not exist until #31 (Week 4). Leave it unticked and say so in the PR.
- Race on duplicate names (see Decisions). If it ever matters, a V0002 migration can turn the `Application.name` index into a uniqueness constraint (needs an ADR).

## Handoff
- Response shapes: app `{id, name, technology}`, version `{id, version}`. The 4xx bodies are Spring's default error JSON; the client should rely on the status code only.

## Outcome (fill when the issue closes)
