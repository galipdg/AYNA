# Accounts, roles, sessions and API tokens

- Date: 2026-10-31
- Status: Proposed (needs Galip's and Hasan's approval in the #60 PR)
- Deciders: Ömerfaruk (proposal), Galip, Hasan
- Issue: #60 (FR-39, NFR-32, FR-23, SC-03)

## Context
FR-39 asks for local accounts with the role admin or tester, managed by admins only, and API tokens for a CI service account. NFR-32 refuses every REST and WebSocket request except login without a valid session or API token. FR-23 has the CLI runner send its token from `AYNA_SERVER_TOKEN` as a Bearer token. SC-03 needs the user id on every edit, run and approval. The server runs on a closed network as one instance and talks to an Electron client whose main process makes the calls (agent RPC ADR). Today no API checks anyone.

## Options considered
1. **Opaque random Bearer tokens stored as hashes in Neo4j**, one scheme for interactive sessions and CI tokens. Revocation takes effect immediately, sessions survive a server restart, there is no CSRF exposure (no cookie), and the CLI and the client use the same header.
2. **Servlet session cookie (`JSESSIONID`)**: Spring's default. Sessions are in memory and lost on restart, CSRF protection is needed, and CI tokens need a second path anyway.
3. **JWT**: stateless, but needs a JWT library and a signing key to manage, and revocation needs a deny list, which is a token store again. Nothing gains from statelessness with one server.

## Decision
Option 1, using `spring-boot-starter-security` for the filter chain, BCrypt and the 401/403 handling.

- **Accounts.** `(:User {id, username, passwordHash, role, createdAt})`, `role` is `admin` or `tester`; `username` is unique, case-insensitive (stored lower-case). Passwords are BCrypt hashes (cost 10) and at least 8 characters. A removed account keeps its node with `removedAt` set and can no longer log in, so the ids stored on old edits still resolve to a name. The last active admin cannot be removed or demoted (409).
- **First admin.** On start-up, if there is no active admin and `AYNA_ADMIN_USERNAME` and `AYNA_ADMIN_PASSWORD` are set, the server creates that admin. Otherwise it logs a warning that nobody can log in. The variables go in `.env.example` (#82). They are ignored once an admin exists.
- **Tokens.** `(:User)-[:HAS_TOKEN]->(:AuthToken {id, kind, tokenHash, name, createdAt, expiresAt})`. The secret is 32 random bytes, base64url, shown once and stored only as its SHA-256 hash (unique constraint). `kind: session` comes from login and expires 12 hours after creation (`ayna.auth.session-ttl`). `kind: api` is created by an admin for any account (a CI service account is an ordinary tester account), has a `name` and never expires; it is revoked by deleting it. Every request sends `Authorization: Bearer <token>`.
- **Endpoints.** `POST /api/auth/login {username, password}` → `{token, expiresAt, user}`; the same 401 for an unknown user and a wrong password. `POST /api/auth/logout` deletes the current session. `GET /api/auth/me`. Admin only: `/api/users` (list, create, change role or password, remove) and API tokens (`POST`/`GET /api/users/{id}/tokens`, `DELETE /api/tokens/{id}`).
- **Who may do what.** Public: `POST /api/auth/login`, `GET /api/health` (Compose healthcheck, and the client's "is there an AYNA server here" check of SC-02), the OpenAPI document and Swagger UI. Admin: user and token management. Every other `/api/**` request: any authenticated account. An admin can do everything a tester can. WebSocket handshakes (#44) authenticate the same way.
- **Errors.** 401 (no, unknown, expired or revoked token; bad login) and 403 (tester on an admin endpoint) are RFC 9457 problems (ADR `2026-10-29-rest-error-problem-details`), listed in `docs/api/openapi.yaml` with a `bearerAuth` security scheme.
- **Who did it.** Every write API stores the acting user's id on what it writes: `createdBy`/`createdAt` and `updatedBy`/`updatedAt` on `TestCase` (#60); `startedBy` on `Run` (#44); `decidedBy`/`decidedAt` on `HealingProposal` (#74). Properties, not relationships: they are audit data, never traversed. Responses that show them resolve the id to `{id, username}`.

## Consequences
- NFR-32 holds except for health and the API docs. The RS (galip) should name these two exceptions.
- The client keeps the session token in the main process only (like the agent token) and sends it on every call; on a 401 it shows the login screen again.
- The CLI runner (#61, hasan) sends `Authorization: Bearer $AYNA_SERVER_TOKEN`; a 401 or 403 means the run's results cannot be delivered (exit code 2 under FR-23).
- Graph schema v0.2: `User` and `AuthToken` labels, constraints in migration `V0003`; `docs/graph-model.md` updated in the same PR.
- Tokens in Neo4j mean a database dump contains token hashes, not tokens, and password hashes, not passwords.
- Removing an account keeps its node; there is no hard delete in semester 1.
