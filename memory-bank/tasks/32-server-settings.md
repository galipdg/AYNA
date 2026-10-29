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
- [x] manual UI check of the picker on macOS (below)
- [x] 2026-10-26: #129 merged; `origin/main` merged in, client lint, typecheck, 33 tests, format, build green again
- [x] 2026-10-26: merge pushed, PR #127 ready for review; Windows check posted on #32 (label `needs-windows-test`)
- [x] 2026-10-27: PR #127 approved by galip and merged; #32 closed (label `needs-windows-test` kept until the Windows run)
- Next step: Windows run at the weekly session (comment on #32); the two review notes below go into #17.

## Manual checks
- 2026-10-26 · omer · server settings screen on macOS (`npm run dev`, 7 steps: first run, unreachable, invalid URL, connect, restart remembers URL, saved server down) · pass · evidence: omer's report in session

- 2026-10-26 · omer · application picker on macOS against #128's server (`npm run dev`, 8 steps: empty server, create + choose, change application, duplicate name, sorted list, restart remembers, reconnect same server keeps choice, deleted app shows notice) · pass · evidence: omer's report in session

- Windows (9 steps, issue comment https://github.com/galipdg/AYNA/issues/32#issuecomment-6426014115) · pending Windows session

## Open issues
- From galip's #127 review (non-blocking, to fix in #17, which adds IPC handlers anyway): (1) `AppPicker.choose()` has no `catch`, so a failed `chooseApplication` (settings file not writable) shows nothing; map it to an error like `create()` does. (2) IPC handlers do not check `event.senderFrame`; add one shared check against the entry page for every `ipcMain.handle`.
- While Neo4j is shutting down, `/api/health` can take > 5 s (`Driver.verifyConnectivity` has no bound), so the client shows "timeout" instead of "db-down". Once Neo4j is fully stopped it answers 503 in ~50 ms. Possible server fix: bound the health check (driver connection timeout). Not in #32's scope.

## Handoff
- `server:check` exists separately from `server:connect` so the startup check does not rewrite the settings file.
- The renderer has no component tests; all logic worth testing lives in `src/main/` (plain `node --test`).

## Outcome (fill when the issue closes)
- 2026-10-27: merged via PR #127 (approved by galip). Both acceptance criteria met on macOS (manual checks above); Windows run pending.
