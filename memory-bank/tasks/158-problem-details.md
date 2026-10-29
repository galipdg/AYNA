# #158 REST error body: RFC 9457 problem details for all APIs

- Issue: https://github.com/galipdg/AYNA/issues/158
- Owner: omer · Branch: `omer/158-problem-details` (branched from `omer/31-openapi-contract`, PR #160)
- Started: 2026-10-29 · Last update: 2026-10-29

## Approach
One global `@RestControllerAdvice` (`server/.../error/ApiErrorHandler`) extending `ResponseEntityExceptionHandler`, so Spring's own errors share the shape. Shared exceptions in `error/ApiExceptions`; the per-package `tests/TestErrorHandler`, `TestExceptions` and `apps/AppExceptions` are gone. Contract: ADR `2026-10-29-rest-error-problem-details`.

## Decisions (small, local to this task)
- 2026-10-29 — milestone Week 4 (same as #31) — user's choice
- 2026-10-29 — branch from #31's branch, not `main` — #158 changes the generated `openapi.yaml` that #31 introduces; merge `main` in once PR #160 is merged
- 2026-10-29 — OpenAPI errors via `@ErrorResponses` + an `OperationCustomizer`, not swagger `@ApiResponse` — springdoc drops the generated 200 of an operation that has `@ApiResponse` but no `@ResponseStatus`
- 2026-10-29 — `server/AGENTS.md` gets the error rule — user OK
- 2026-10-29 — PR base `omer/31-openapi-contract` until #160 merges — user OK; diff shows only #158
- 2026-10-29 — apps API 400s also list `errors[{path}]` — criterion 2; same `required()` helper as the tests API

## Status
- [x] global handler, shared exceptions, apps + tests migrated (42936d7)
- [x] integration tests: apps errors, Spring errors (`error/ApiErrorIntegrationTest`), 38/38 green locally
- [x] `openapi.yaml` lists 400/404/409 per operation with the `Problem` schema
- [x] ADR (Proposed)
- [ ] push + PR (ask user); PR base: `main` once #160 is merged, otherwise `omer/31-openapi-contract`
- Next step: ask to push and open the PR; request galip's and hasan's review of the ADR

## Manual checks
None needed: everything is covered by integration tests (no UI, no Windows).

## Open issues
- 5xx keeps Spring Boot's default body (noted in the ADR; revisit with #52).
- Client (`client/src/main/apps.ts`) judges errors by status only; showing `detail` / `errors[].path` belongs to the screens (#24, #30, #38), not here.

## Handoff
- `@ErrorResponses` may only name statuses that `OpenApiConfig` defines a response component for (400, 404, 409); otherwise the `$ref` dangles.
- #25 (repository) should throw the shared exceptions; duplicate logical name → `ConflictException`.
