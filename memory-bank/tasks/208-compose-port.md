# #208 Compose: server host port from .env, clear error when Neo4j refuses the password

- Issue: https://github.com/galipdg/AYNA/issues/208
- Owner: omer · Branch: `omer/208-compose-port`
- Started: 2026-11-08 · Last update: 2026-11-08

## Approach
From hasan's 2026-11-07 inbox item (#28 Windows session).
- Port: `docker-compose.yml` publishes `"${AYNA_SERVER_PORT:-8080}:8080"`; `.env.example` lists `AYNA_SERVER_PORT`; `server/AGENTS.md` says what a held port looks like.
- Password: `Neo4jAuthFailureHint` (an `ApplicationFailedEvent` listener) logs one ERROR line with the URI, the user and `docker compose down -v` when `AuthenticationException` is anywhere in the start failure's cause chain. Spring Boot's own "Application run failed" + trace still follows it.

## Decisions (small, local to this task)
- 2026-11-08 — Listener, not a `FailureAnalyzer` — Boot logs an analysed failure's stack trace only at DEBUG, and the issue says keep the original exception in the log. The cost: the hint comes just before the trace, not after it.
- 2026-11-08 — Registered in `META-INF/spring.factories` — tried as a `@Component` (no factories entry): the integration test failed because the line was logged twice, and a bean listener only hears about the failure if it was created before the bean that failed. Through `spring.factories` it is logged once (test asserts a single line; the jar run too).
- 2026-11-08 — The integration test has its own Neo4j container — Neo4j locks a user after repeated failed logins, which would break the shared test container's other tests.

## Status
- [x] Issue #208 (Week 3, owner:omer, area:devops, area:server), board In progress
- [x] Port mapping + `.env.example` + `server/AGENTS.md`; `docker compose config` checked with and without `AYNA_SERVER_PORT`
- [x] Hint + unit test (other failures stay quiet, no context) + integration test (real Neo4j, wrong password)
- [x] Full server suite: 106 tests, 0 failures (`./mvnw package`); `openapi.yaml` unchanged
- [ ] Push and PR (on omer's OK)
- Next step: open the PR with `Closes #208` once omer agrees to push.

## Manual checks
- 2026-11-08 · omer's agent · jar against a separate Neo4j with a wrong password, before the change · 111 log lines, `AuthenticationException` at line 55, no hint · scratchpad log, not kept
- 2026-11-08 · omer's agent · same, after the change · pass: hint at line 25 of 112, then `Application run failed` and `Caused by: …AuthenticationException` at line 56 · scratchpad log, not kept
- 2026-11-08 · omer's agent · jar with no Neo4j at all (connection refused) · pass: no hint, 1279 lines of retries
- Windows: not needed. The port behaviour (another program holding IPv4 8080) was hasan's own finding; the fix is plain Compose interpolation, checked with `docker compose config`.

## Open issues
- None yet.

## Handoff
- The hint only matches `org.neo4j.driver.exceptions.AuthenticationException`. Neo4j's lock after repeated failed logins (`Neo.ClientError.Security.AuthenticationRateLimit`) probably reaches the driver as a plain `SecurityException` and gets no hint (not tested); with no restart policy in Compose it needs several `up`s within seconds.

## Outcome (fill when the issue closes)
