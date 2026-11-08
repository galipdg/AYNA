# client/ — Electron + React desktop client

Owner: omer. Read `/AGENTS.md` first; this file adds only what is specific to `client/`.

## Layout
- `src/main/` — Electron main process, agent process manager, overlay window
- `src/preload/` — typed bridge to the renderer
- `src/renderer/` — React UI: Spy, repository, editor, runs, healing, NL chat

## Commands
Run from `client/` (Node >= 22.12):
- `npm ci` — install (all packages are devDependencies; everything is bundled)
- `npm run dev` — open the app with hot reload (first downloads the Electron binary via `install-electron`)
- `npm run dev:mock` — the same against a stub server (`http://127.0.0.1:8099`) and a fake agent, on any OS without the server, Neo4j or Windows; options and window list in `dev/mock/README.md`
- `npm run build` — `out/` + unpacked app in `release/<platform>-unpacked` (no installer)
- `npm run lint` — ESLint
- `npm run typecheck` — `tsc -b` (`tsconfig.node.json` for main/preload/shared, `tsconfig.web.json` for the renderer, which sees no Node types)
- `npm test` — `node --test` (type stripping) on `src/**/__tests__/*.test.ts`
- `npm run format` / `npm run format:check` — Prettier

Before committing: `npm run lint && npm run typecheck && npm test` (CI also runs `npm run build`).

## Code layout
- `src/shared/api.ts` — the preload API contract (`AynaApi`, IPC channel names). Add a bridge method here first, then in `src/preload/index.ts` and an `ipcMain.handle` in main; the renderer gets the type via `src/renderer/src/env.d.ts` (`window.ayna`).
- `src/main/security.ts` — CSP, request/navigation allow-lists, `webPreferences`; tested in `src/main/__tests__/`.

## Rules
- `contextIsolation: true`, `nodeIntegration: false`; renderer never imports Node modules.
- No remote content, CDN fonts or auto-update (closed network).
- Every UI text exists in Turkish and English (#185, ADR `2026-11-03-client-ui-language`): add it to `src/renderer/src/i18n/en.ts` and `i18n/tr.ts`, read it as `strings.x` at render time (never copy it into a module constant); `i18n.test.ts` fails on a missing or untranslated text. Dates through `formatDate` / `formatTime`; known server messages through `serverText`. Test data is never translated (NFR-16).
