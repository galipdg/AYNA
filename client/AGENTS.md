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
- UI text in English for now; keep strings in one place for later translation.
