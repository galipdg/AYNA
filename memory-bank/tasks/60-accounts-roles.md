# #60 Basic local accounts and roles

- Issue: https://github.com/galipdg/AYNA/issues/60
- Owner: omer · Branch: `omer/60-accounts-roles` (stacked on `omer/31-openapi-contract`, PR #160, until it merges)
- Started: 2026-10-31 · Last update: 2026-10-31

## Approach
ADR `2026-10-31-accounts-and-tokens` (Proposed): opaque Bearer tokens hashed in Neo4j for both login sessions and CI API tokens, Spring Security filter chain, BCrypt. Server package `auth/`. Client: login screen after the server settings, admin-only user management.

## Decisions (small, local to this task)
- 2026-10-31 — Scope: storing the user id on runs and approvals moved to #44 and #74 (omer's choice; neither API exists yet). #60 does edits (tests) and the rule in the ADR.
- 2026-10-31 — Session over cookie or JWT, `spring-boot-starter-security`, first admin from env vars: omer's choices.
- 2026-10-31 — Usernames ASCII `[a-z0-9._-]{1,64}`, stored lower-case: avoids Turkish İ/ı case-folding surprises in a unique key. Passwords 8 chars to 72 UTF-8 bytes (BCrypt's limit; Spring refuses longer).
- 2026-10-31 — `UserDetailsServiceAutoConfiguration` excluded: otherwise Boot creates an unused in-memory user and logs its password.
- 2026-10-31 — Tests: `SignedIn` (test config) sends every MockMvc request as a tester principal that is not in the database; `AuthIntegrationTest` uses real logins. `@PublicEndpoint` drives the contract's `security: []`; a test checks it matches `SecurityConfig`.

## Status
- [x] Branch, task note, board → In progress, ADR draft
- [x] Server: `spring-boot-starter-security` (+ `-security-test`), V0003, `auth/` (login/logout/me, Bearer filter, first admin, 401/403 problems), `/api/users`, API tokens, `createdBy`/`updatedBy` on tests, OpenAPI regenerated, `graph-model.md` v0.2, `.env.example` + Compose. 54 server tests green; Compose smoke test (first admin, 401 without token, login 200) 2026-10-31
- [x] Client: session token in the main process memory only, tied to the server URL; login screen after the server check; "Logged in as" + Log out; a 401 anywhere → login screen with "session ended". 40 client tests, lint, typecheck, build green 2026-10-31
- [ ] Client: admin user management screen (list, create, role, password, remove, API tokens); a tester sees "only admins manage users" (SC-03)
- Next step: user management screen (renderer `Users.tsx`, main `users.ts` with the same `request` helper); then manual check, PR (stacked on #160).

## Manual checks
- Login screen on macOS with `npm run dev` against `docker compose up`: pending (omer). Same at the weekly Windows session.

## Open issues
- RS NFR-32 should name the public exceptions (health, API docs) → galip's inbox.
- `.env.example` (#82) needs `AYNA_ADMIN_USERNAME` / `AYNA_ADMIN_PASSWORD`.

## Handoff
- `server/AGENTS.md` should get a rule "every write API stores the acting user id (ADR accounts-and-tokens)": needs omer's OK (AGENTS.md change).
- Client: a 401 clears the main-process session (`track()` in `src/main/index.ts`); new API calls must go through `server()` + `track()`.
- Inbox notes to galip (NFR-32 exceptions) and hasan (CLI Bearer token) are on this branch.

## Outcome (fill when the issue closes)
