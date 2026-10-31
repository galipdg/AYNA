# REST error body: RFC 9457 problem details

- Date: 2026-10-29
- Status: Accepted (Hasan approved the #158 PR #163, Galip the #31 PR #160, 2026-10-29; the review points are folded in below)
- Deciders: Ömerfaruk (proposal), Galip, Hasan
- Issue: #158 (split from #31)

## Context
NFR-15 asks every error shown to the user to name what it concerns, so the client needs the server's message. Until #158 only the tests API (#39) returned one, through a handler scoped to its package; the apps API (#128) returned Spring Boot's default error body, which hides the message. The contract must be fixed before the REST, WebSocket and JSON-RPC contracts are frozen (#52), and every later API (repository #25, runs #51, healing #74) should follow it without a new decision.

## Options considered
1. **RFC 9457 problem details** (`application/problem+json`), built into Spring (`ProblemDetail`, `ResponseEntityExceptionHandler`): a standard shape, Spring's own errors (unreadable JSON, unknown path, wrong method) get it for free, and the tests API already uses it.
2. **A project-specific body** such as `{code, message, fields}`: freedom to choose names, but every error Spring raises before a controller runs would need its own mapping, and no tool knows the shape.
3. **Spring Boot's default body with `server.error.include-message=always`**: no code, but no field list, and it leaks exception messages of unexpected errors.

## Decision
Option 1, for every REST API:
- Every 4xx body is a problem: `status`, `title` (HTTP reason phrase), `detail` (the message for the user, naming the field, object or id) and `instance` (the request path).
- `type` is omitted (`about:blank`) unless a caller must tell two problems with the same status apart without reading `detail`, which is English prose. Such a kind is `urn:ayna:error:<kind>` (lower-case, hyphens, e.g. `urn:ayna:error:unknown-run`), added by the API that needs it and listed in that endpoint's response in `docs/api/openapi.yaml`. A kind, once released, is never renamed. It is also the key for a translated client message (TBD-2).
- A 400 caused by validation adds `errors: [{path, message}]`, one entry per failing field, at most the first 50, and `errorCount`, the total. `path` is a JSONPath (RFC 9535) into the request body with member names and array indices only (`$.steps[2].value`), never filter or wildcard expressions, so the same failure always gets the same path.
- Status codes: 400 invalid body or field, 404 an id in the path names nothing, 409 a uniqueness rule is broken (names per application). Repeating an idempotent write (the step-result `PUT` of the healing proposal transport ADR) is a 200 with the stored result, never a 409.
- An expected failure of an upstream service is a problem too: the AI service's 422 / 503 / 504 (#78) keep their status, and its `status` string goes in `code`, its `error` in `detail`, and its `details` / `dropped` stay as extension members.
- Server code throws `ApiExceptions.{InvalidRequest,NotFound,Conflict}Exception` (`server/.../error/`); one global `ApiErrorHandler` writes the body. Endpoints list their error statuses with `@ErrorResponses`, so `docs/api/openapi.yaml` shows them with the `Problem` schema.

## Consequences
- The client can show `detail` directly and highlight fields from `errors[].path`; it may keep judging outcomes by status code alone.
- New APIs need no error code of their own; a new error status (for example 422 with #78 or 403 with accounts in #60) needs a response component in `OpenApiConfig`, and a new kind a `type` as above.
- The CLI runner (#61) can branch on `type` where the healing transport ADR treats 4xx kinds differently (unknown run vs invalid document); #51 defines those kinds.
- 5xx bodies are not covered: unexpected errors keep Spring Boot's default body without the message. Revisit with #52 if the client needs a problem there too.
- Clients must treat an unknown `type` like `about:blank`, so adding a kind never breaks them.
