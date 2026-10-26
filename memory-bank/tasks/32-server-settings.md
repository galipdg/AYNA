# #32 Server connection settings and project picker

- Issue: https://github.com/galipdg/AYNA/issues/32
- Owner: omer · Branch: `omer/32-server-settings`
- Started: 2026-10-26 · Last update: 2026-10-26

## Approach
Two halves: (1) server URL + connection check (done first), (2) application picker, which needs `GET /api/applications` from #15 (not built yet).

- `client/src/main/server.ts` — `normalizeServerUrl` + `checkServer` against `GET /api/health`; never throws, maps every failure to a `ConnectionFailure` (`invalid-url`, `unreachable`, `timeout`, `not-ayna`, `db-down`).
- `client/src/main/settings.ts` — `settings.json` in Electron `userData` (per machine), atomic write.
- IPC: `settings:get`, `server:check` (no save), `server:connect` (check, save only on success). Contract in `client/src/shared/api.ts`.
- Renderer: `ServerSettings.tsx`; `App.tsx` shows it on first run, or when the saved server fails at startup (URL prefilled, error shown).

## Decisions (small, local to this task)
- 2026-10-26 — check runs in main with Node's `fetch`, not in the renderer — the renderer CSP (`connect-src 'self'`) and the session request filter must stay closed; Node's fetch is outside both.
- 2026-10-26 — save the URL only after a successful check — a wrong URL never overwrites a working one.
- 2026-10-26 — missing scheme means `http://`; path prefix kept, query/fragment/credentials rejected.
- 2026-10-26 — #32 stays open until the picker is done after #15 (agreed with omer), instead of splitting the issue.

## Status
- [x] URL setting + connection check, unit tests (`server.test.ts`, `settings.test.ts`), checked against the real backend (`docker compose up`): ok, not-ayna (Neo4j browser on :7474), unreachable (closed port, unknown host), invalid-url, db-down (Neo4j stopped)
- [ ] manual UI check on macOS (below)
- [ ] application picker (blocked by #15), remembered between restarts
- Next step: omer runs the manual UI check; then wait for #15's applications API and add the picker (store `applicationId` in `Settings`).

## Manual checks
- 2026-10-26 · omer · server settings screen (`npm run dev`) · pending

## Open issues
- While Neo4j is shutting down, `/api/health` can take > 5 s (`Driver.verifyConnectivity` has no bound), so the client shows "timeout" instead of "db-down". Once Neo4j is fully stopped it answers 503 in ~50 ms. Possible server fix: bound the health check (driver connection timeout). Not in #32's scope.

## Handoff
- `server:check` exists separately from `server:connect` so the startup check does not rewrite the settings file.
- The renderer has no component tests; all logic worth testing lives in `src/main/` (plain `node --test`).

## Outcome (fill when the issue closes)
