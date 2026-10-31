# #60 Basic local accounts and roles

- Issue: https://github.com/galipdg/AYNA/issues/60
- Owner: omer · Branch: `omer/60-accounts-roles` (stacked on `omer/31-openapi-contract`, PR #160, until it merges; first PR #168 reverted, see Status)
- Started: 2026-10-31 · Last update: 2026-10-31

## Approach
ADR `2026-10-31-accounts-and-tokens` (Proposed): opaque Bearer tokens hashed in Neo4j for both login sessions and CI API tokens, Spring Security filter chain, BCrypt. Server package `auth/`. Client: login screen after the server settings, admin-only user management.

## Decisions (small, local to this task)
- 2026-10-31 — Scope: storing the user id on runs and approvals moved to #44 and #74 (omer's choice; neither API exists yet). #60 does edits (tests) and the rule in the ADR.
- 2026-10-31 — Session over cookie or JWT, `spring-boot-starter-security`, first admin from env vars: omer's choices.
- 2026-10-31 — Usernames ASCII `[a-z0-9._-]{1,64}`, stored lower-case: avoids Turkish İ/ı case-folding surprises in a unique key. Passwords 8 chars to 72 UTF-8 bytes (BCrypt's limit; Spring refuses longer).
- 2026-10-31 — `UserDetailsServiceAutoConfiguration` excluded: otherwise Boot creates an unused in-memory user and logs its password.
- 2026-10-31 — User management errors pass on the server's problem `detail` (NFR-15) instead of fixed client texts: 400 and 409 have several causes (name format vs password length, name taken vs last admin).
- 2026-10-31 — A new API token's secret is shown in a read-only field to select and copy by hand: the session's permission handler denies every permission, clipboard writes included.
- 2026-10-31 — An admin who changes their own password or removes themselves goes to the login screen (the server ended their sessions); demoting themselves switches the client to the tester view.
- 2026-10-31 — Tests: `SignedIn` (test config) sends every MockMvc request as a tester principal that is not in the database; `AuthIntegrationTest` uses real logins. `@PublicEndpoint` drives the contract's `security: []`; a test checks it matches `SecurityConfig`.

## Status
- [x] Branch, task note, board → In progress, ADR draft
- [x] Server: `spring-boot-starter-security` (+ `-security-test`), V0003, `auth/` (login/logout/me, Bearer filter, first admin, 401/403 problems), `/api/users`, API tokens, `createdBy`/`updatedBy` on tests, OpenAPI regenerated, `graph-model.md` v0.2, `.env.example` + Compose. 54 server tests green; Compose smoke test (first admin, 401 without token, login 200) 2026-10-31
- [x] Client: session token in the main process memory only, tied to the server URL; login screen after the server check; "Logged in as" + Log out; a 401 anywhere → login screen with "session ended". 40 client tests, lint, typecheck, build green 2026-10-31
- [x] Client: admin user management screen (`Users.tsx`, `ApiTokens.tsx`, main `users.ts`): list, create, role, password, remove, API tokens; a tester (or a 403) sees "only admins manage users" (SC-03). 51 client tests, lint, typecheck, build green 2026-10-31
- 2026-10-31 — PR #168 was squash-merged into `omer/31-openapi-contract` with no reviews (10:51 UTC); reverted there in `48dfd5a` (omer's choice), so #160 merges with its own scope only. This branch still holds every #60 commit.
- Next step: when #160 merges, `git merge origin/main` here, rerun server + client tests, open a **new** PR to `main` (`Closes #60`, reviewers galip + hasan for the ADR); answer reviews; Windows session check.

## Manual checks
- 2026-10-31 · agent · macOS · built app driven over CDP (`--remote-debugging-port`, throwaway `--user-data-dir`) against a fresh Compose stack: login, user list, add tester, API token (secret shown once), last-admin refusal (409 shown, select reverts), log out, tester login, "Manage users" refused. Pass; screenshots not kept. Also `users.ts` against the real server: every status mapped as expected.
- 2026-10-31 · omer · macOS · `npm run dev` + `docker compose up` (fresh volume): login; Manage users list; add tester; API token shown once; last-admin refusal (select reverts); tester sees "only admins manage users". All pass, reported by omer in the session (no screenshots).
- Weekly Windows session: pending.

## Open issues
- RS NFR-32 should name the public exceptions (health, API docs) → galip's inbox.
- `.env.example` (#82) needs `AYNA_ADMIN_USERNAME` / `AYNA_ADMIN_PASSWORD`.

## Handoff
- `server/AGENTS.md` has the "who did it" rule for every later write API (omer's OK 2026-10-31).
- Client: a 401 clears the main-process session (`track()` in `src/main/index.ts`); new API calls must go through `server()` + `track()`.
- Inbox notes to galip (NFR-32 exceptions) and hasan (CLI Bearer token) are on this branch.

## Outcome (fill when the issue closes)
