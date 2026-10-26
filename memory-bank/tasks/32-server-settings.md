# #32 Server connection settings and project picker

- Issue: https://github.com/galipdg/AYNA/issues/32
- Owner: omer · Branch: `omer/32-server-settings`
- Started: 2026-10-26 · Last update: 2026-10-26

## Approach
Two halves: (1) server URL + connection check (done first), (2) application picker, which needs `GET /api/apps` from #128 (split out of #15 on 2026-10-26; not built yet).

- `client/src/main/server.ts` — `normalizeServerUrl` + `checkServer` against `GET /api/health`; never throws, maps every failure to a `ConnectionFailure` (`invalid-url`, `unreachable`, `timeout`, `not-ayna`, `db-down`).
- `client/src/main/settings.ts` — `settings.json` in Electron `userData` (per machine), atomic write.
- IPC: `settings:get`, `server:check` (no save), `server:connect` (check, save only on success). Contract in `client/src/shared/api.ts`.
- Renderer: `ServerSettings.tsx`; `App.tsx` shows it on first run, or when the saved server fails at startup (URL prefilled, error shown).
- Picker: `client/src/main/apps.ts` (`listApplications` / `createApplication` against #128's `/api/apps`, never throws, failures → `RequestFailure` | `duplicate` | `invalid`); IPC `apps:list`, `apps:create`, `apps:choose` (saves `Settings.applicationId`). Renderer `AppPicker.tsx`; `App.tsx` flow: server → picker → ready (`viewForServer` resolves the saved id against the list).

## Decisions (small, local to this task)
- 2026-10-26 — check runs in main with Node's `fetch`, not in the renderer — the renderer CSP (`connect-src 'self'`) and the session request filter must stay closed; Node's fetch is outside both.
- 2026-10-26 — save the URL only after a successful check — a wrong URL never overwrites a working one.
- 2026-10-26 — missing scheme means `http://`; path prefix kept, query/fragment/credentials rejected.
- 2026-10-26 — the picker can also create an application (name + free-text technology), then chooses it (user's choice) — otherwise a first run on an empty server is a dead end; nothing else creates applications yet (#15 import later).
- 2026-10-26 — `applicationId` is cleared when the server URL changes (`withServer` in `settings.ts`): ids belong to one server. If the saved id is gone from the server, the picker opens with a notice.
- 2026-10-26 — main calls the API with the *saved* server URL, so the renderer never passes a URL to `apps:*`.
- 2026-10-26 — #32 stays open until the picker is done (agreed with omer), instead of splitting #32; the applications list/create API was split out of #15 into #128 instead, so the picker no longer waits for #12.

## Status
- [x] URL setting + connection check, unit tests (`server.test.ts`, `settings.test.ts`), checked against the real backend (`docker compose up`): ok, not-ayna (Neo4j browser on :7474), unreachable (closed port, unknown host), invalid-url, db-down (Neo4j stopped)
- [x] manual UI check on macOS (below)
- [x] application picker + create, `applicationId` in `Settings`; lint, typecheck, 33 unit tests, build green; `apps.ts` checked against the real #128 server (`docker compose` from a worktree of `omer/128-apps-api`): empty list, create, duplicate, blank, sorted, not-ayna (:7474)
- [ ] manual UI check of the picker on macOS (pending, omer)
- Next step: omer runs the picker manual check (needs #128's server); on pass, mark PR #127 ready (`Closes #32`) once #129 is merged.

## Manual checks
- 2026-10-26 · omer · server settings screen on macOS (`npm run dev`, 7 steps: first run, unreachable, invalid URL, connect, restart remembers URL, saved server down) · pass · evidence: omer's report in session

- pending · omer · application picker on macOS (empty server, create, duplicate, restart remembers, change application, change server clears choice)

## Open issues
- While Neo4j is shutting down, `/api/health` can take > 5 s (`Driver.verifyConnectivity` has no bound), so the client shows "timeout" instead of "db-down". Once Neo4j is fully stopped it answers 503 in ~50 ms. Possible server fix: bound the health check (driver connection timeout). Not in #32's scope.

## Handoff
- `server:check` exists separately from `server:connect` so the startup check does not rewrite the settings file.
- The renderer has no component tests; all logic worth testing lives in `src/main/` (plain `node --test`).

## Outcome (fill when the issue closes)
