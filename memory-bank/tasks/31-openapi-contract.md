# #31 OpenAPI contract v0

- Issue: https://github.com/galipdg/AYNA/issues/31
- Owner: omer · Branch: `omer/31-openapi-contract`
- Started: 2026-10-29 · Last update: 2026-10-29

## Approach
springdoc-openapi 3.2.0 (built on Boot 4.1.2, same as ours) serves `/v3/api-docs` and Swagger UI. `OpenApiContractIntegrationTest` boots the app (Testcontainers Neo4j), fetches `/v3/api-docs.yaml` and rewrites `docs/api/openapi.yaml` when it differs; the CI server job fails if the file is modified or untracked after `./mvnw verify`. No Maven plugin and no running server needed.

## Decisions (small, local to this task)
- 2026-10-29 — Started before #15 (formal dependency) with the user's OK: springdoc covers existing endpoints now; #15's endpoint lands in the contract through the same CI check.
- 2026-10-29 — Error body (RFC 9457) split out to #158 with the user's OK; #31 does not change error behaviour.
- 2026-10-29 — v0 has no `@Operation`/`@Tag` annotations (tags are `app-controller`, `test-controller`); richer docs and error responses belong to #158 / #52 (contract freeze v1).
- 2026-10-29 — `@ResponseStatus(CREATED|NO_CONTENT)` added on create/import/delete handlers only so the contract shows 201/204; runtime unchanged (`ResponseEntity` already set them).
- 2026-10-29 — `JsonNode` bodies shown as `type: object` (`SpringDocUtils.replaceWithSchema`); `schemas/step.schema.json` stays the real step contract.
- 2026-10-29 — Swagger UI stays enabled in every profile (dev and prod); can be turned off with `springdoc.swagger-ui.enabled=false` once auth (#60) exists, if wanted.
- 2026-10-29 — Only `/api/**` is documented (`springdoc.paths-to-match`).

## Status
- [x] Dependency, `OpenApiConfig`, properties, generation test, CI step; `./mvnw verify` 34 tests green
- [x] Generated twice in separate JVMs: byte-identical. CI check simulated locally: exit 0 when clean, 1 when stale.
- [x] `docker compose up --build`: `/swagger-ui.html` → 302 → `/swagger-ui/index.html` 200; assets local; no petstore URL; served `/v3/api-docs.yaml` equals the committed file
- [x] Committed; `server/AGENTS.md` regeneration rule and galip's inbox note (RS.md status) added with the user's OK
- [x] PR #160 opened 2026-10-29 (`Closes #31`), review requested from galip
- [x] CI green on #160 (all four jobs; Linux-generated contract matched the macOS one) 2026-10-29
- [x] galip approved #160 (2026-10-29); #163 (#158) merged into this branch; 2026-10-31 `origin/main` merged in (conflict on GitHub, clean locally), both ADRs (graph schema v0.1, problem details) Accepted as galip asked
- Next step: after merge, check #31 and #158 closed and Done on the board.

## Manual checks
- 2026-10-29 · omer (agent, curl) · Swagger UI on the dev server · pass · see Status. A look in a browser (operations listed, "Try it out" on `GET /api/health`) is optional.

## Open issues
- `docs/rs/RS.md` (galip's) lists `docs/api/openapi.yaml` as "planned"; note in galip's inbox (2026-10-29).

## Handoff
- Any REST change: run `./mvnw test` in `server/` and commit the regenerated `docs/api/openapi.yaml` with it, or CI fails.

## Outcome (fill when the issue closes)
