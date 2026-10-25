# #4 Spring Boot + Neo4j skeleton with Docker Compose

- Issue: https://github.com/galipdg/AYNA/issues/4
- Owner: omer · Branch: `omer/4-server-skeleton`
- Started: 2026-10-25 · Last update: 2026-10-25

## Approach
- `server/` generated with start.spring.io (Spring Boot 4.1.2, Java 21, Maven wrapper), package `com.ayna.server`, feature packages under it.
- `GET /api/health` (`health/HealthController`) calls `Driver.verifyConnectivity()`: 200 `{status: UP, db: UP}`, otherwise 503 with `db: DOWN`.
- `docker-compose.yml` at the repo root: `neo4j:5.26-community` + `server` (built from `server/Dockerfile`), server waits for the Neo4j healthcheck.
- Integration test `HealthIntegrationTest` uses Testcontainers with the same image and telemetry setting as compose.

## Decisions (small, local to this task)
- 2026-10-25 — Java 21, Maven wrapper (user). Conventions said "Maven or Gradle (decided in #3)"; decided here instead because #4 needs it first.
- 2026-10-25 — `docker-compose.yml` lives at the repo root (user): one `docker compose up` should later start the whole system (server, Neo4j, AI service, nginx). `architecture.md` updated (user OK).
- 2026-10-25 — Actuator dropped from the generated deps: the custom `/api/health` covers the criterion; add it back if we need metrics.
- 2026-10-25 — Neo4j 5.26 LTS instead of `latest` (calendar 2025.x) for a stable, pinned image.
- 2026-10-25 — Dev password default `ayna-dev-password` in compose and `application.properties` so `docker compose up` needs no manual step; override with `NEO4J_PASSWORD` in `.env`.

## Status
- [x] Skeleton, health endpoint, unit test
- [x] `./mvnw test` locally: 2/2 pass incl. Testcontainers integration test (2026-10-25)
- [x] `docker compose up -d --build` → `/api/health` 200 `{"status":"UP","db":"UP"}`; `dbms.usage_report.enabled=false` confirmed via `SHOW SETTINGS`
- [x] `server/AGENTS.md` Commands filled (user OK)
- [x] Integration test green in CI — server job on `main`, run 40217766040 (2026-10-25)
- [x] PR #114 merged 2026-10-25 (`Refs #4`); board card In progress.
- Next step: in #3, add the server CI job (`cd server && ./mvnw -B test` on ubuntu-latest, Docker available); when green, close #4 with a link to the run.

## Manual checks
- 2026-10-25 · omer's agent · `docker compose up` + `curl localhost:8080/api/health` on omer's Mac · pass · output in session

## Open issues
- `JAVA_HOME` on omer's Mac points to a missing `temurin-21.jdk` path; use `export JAVA_HOME=$(/usr/libexec/java_home -v 21)`.
- Criterion "integration test passes in CI" depends on #3; #4 may need to wait for it or close with a link.

## Handoff

## Outcome (fill when the issue closes)
- 2026-10-25 — closed. Delivered in PR #114 (skeleton, health endpoint, compose, Testcontainers test) + the server CI job from #3 (PR #118). All four criteria met; CI evidence: https://github.com/galipdg/AYNA/actions/runs/40217766040
