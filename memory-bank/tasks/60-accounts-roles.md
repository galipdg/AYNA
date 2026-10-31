# #60 Basic local accounts and roles

- Issue: https://github.com/galipdg/AYNA/issues/60
- Owner: omer · Branch: `omer/60-accounts-roles` (stacked on `omer/31-openapi-contract`, PR #160, until it merges)
- Started: 2026-10-31 · Last update: 2026-10-31

## Approach
ADR `2026-10-31-accounts-and-tokens` (Proposed): opaque Bearer tokens hashed in Neo4j for both login sessions and CI API tokens, Spring Security filter chain, BCrypt. Server package `auth/`. Client: login screen after the server settings, admin-only user management.

## Decisions (small, local to this task)
- 2026-10-31 — Scope: storing the user id on runs and approvals moved to #44 and #74 (omer's choice; neither API exists yet). #60 does edits (tests) and the rule in the ADR.
- 2026-10-31 — Session over cookie or JWT, `spring-boot-starter-security`, first admin from env vars: omer's choices.

## Status
- [x] Branch, task note, board → In progress, ADR draft
- [ ] Server: deps, V0003, `auth/` (login/logout/me, bearer filter, bootstrap admin), 401/403 problems
- [ ] Server: `/api/users`, tokens; `createdBy`/`updatedBy` on tests; OpenAPI regenerated
- [ ] Client: login screen, user management
- Next step: server deps + V0003 + login.

## Manual checks
- Client login screen at the weekly Windows session (pending).

## Open issues
- RS NFR-32 should name the public exceptions (health, API docs) → galip's inbox.
- `.env.example` (#82) needs `AYNA_ADMIN_USERNAME` / `AYNA_ADMIN_PASSWORD`.

## Handoff

## Outcome (fill when the issue closes)
