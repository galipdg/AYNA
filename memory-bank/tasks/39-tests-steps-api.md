# #39 Tests and steps API

- Issue: https://github.com/galipdg/AYNA/issues/39
- Owner: omer · Branch: `omer/39-tests-steps-api`
- Started: 2026-10-29 · Last update: 2026-10-29

## Approach
Package `server/src/main/java/com/ayna/server/tests/`. Endpoints: `POST/GET /api/apps/{appId}/tests`, `GET/PATCH/DELETE /api/tests/{id}`, `PUT /api/tests/{id}/steps` (whole step document; a step with `id` keeps its node, one without is new, one left out is deleted; reorder = same ids in a new order), `GET /api/tests/{id}/export`, `POST /api/apps/{appId}/tests/import`. Every step write is validated against `schemas/step.schema.json` (copied onto the classpath by Maven, not duplicated) with networknt json-schema-validator 3.0.8; targets resolve to `(Application)-[:HAS_OBJECT]->(RepoObject)` and only `TARGETS` is stored. Errors are RFC 9457 problem details; a 400 lists `errors: [{path, message}]`.

## Decisions (small, local to this task)
- 2026-10-29 — networknt json-schema-validator 3.0.8 (omer's choice; Apache-2.0, Jackson 3 like Spring Boot 4, 2020-12, meta-schemas bundled) — remote fetching off, locale English, path type JSON_PATH.
- 2026-10-29 — Strict target binding to RepoObject (omer's choice), as promised in the #134 review; tests seed RepoObjects through Cypher until #25.
- 2026-10-29 — Graph change via migration V0002 + Proposed ADR `2026-10-29-graph-schema-application-links` (omer's choice); needs galip's and hasan's approval in the PR.
- 2026-10-29 — The server follows the step schema version on `main` (reads `version` const); tests never hard-code "0.1", so #150's 0.2 needs no server change except storing `row` (already in `JSON_FIELDS`).
- 2026-10-29 — Export format `{format: "ayna-test", name, document}` without step ids; import creates a new test and rejects ids it does not own. Round trip compares the exported files.
- 2026-10-29 — Test names unique per application (409), so an import cannot silently duplicate a test.
- 2026-10-29 — Problem details only in this package (`TestErrorHandler`), not globally: #31 decides for all APIs.
- 2026-10-29 — Server Docker build context moved to the repo root (`server/Dockerfile.dockerignore` allow-list; `server/.dockerignore` removed) so the image build sees `schemas/`.

## Status
- [x] API, validation, migration V0002, ADR, `docs/graph-model.md`; `./mvnw verify` 32 tests green; two mutations caught; `docker compose build` + smoke run against the real container (migration 0002 applied, 400 with `$.steps[0].value`, UTF-8 filename).
- [x] PR #156 opened 2026-10-29 (`Closes #39`), review requested from galip and hasan
- [ ] ADR approvals from galip and hasan → switch ADR + index line to Accepted in this PR
- Next step: check CI on PR #156; then answer the reviews and, on two approvals, mark the ADR Accepted.

## Manual checks
- none needed: everything is covered by tests and the container smoke run above.

## Open issues
- Deleting a test deletes its steps; once runs exist (#51), `StepResult-[:FOR]->Step` and `Run-[:OF]->TestCase` must decide whether history blocks the delete or is kept.
- Re-reading a test stored under an older schema version relabels it with the current version (fine for 0.1 → 0.2, which #150 says is compatible; a breaking release would need a data migration).
- `AppService` still returns Spring's default error body without the message (NFR-15); #31.
- No authorisation yet (#60): every endpoint is open, like `/api/apps`.

## Handoff
- #25 must create `(Application)-[:HAS_OBJECT]->(RepoObject)` and refuse deleting an object that a `TARGETS` points at (FR-09).
- #38 (editor) sends the whole document to `PUT /api/tests/{id}/steps` and shows `errors[].path` next to the step.

## Outcome (fill when the issue closes)
