# #5 Electron + React skeleton

- Issue: https://github.com/galipdg/AYNA/issues/5
- Owner: omer · Branch: `omer/5-electron-skeleton`
- Started: 2026-10-25 · Last update: 2026-10-25

## Approach
- electron-vite (main / preload / renderer, Vite + React) and electron-builder `--dir` for the unpacked app; output dirs `out/` and `release/` were already in `.gitignore`.
- Security lives in `client/src/main/security.ts` (no Electron import, so the Vite config and `node --test` use it): CSP string, request allow-list, navigation check, `webPreferences`.
- CSP has one source: a small Vite plugin in `electron.vite.config.ts` injects it as a `<meta>` tag (file:// pages get no HTTP headers, so a header-only CSP would not cover the built app).
- Defence in depth in `src/main/index.ts`: `webRequest.onBeforeRequest` cancels anything that is not `file:` / `data:` / `devtools:` (or the dev server), `will-navigate` blocked except the entry page, `window.open` denied, `<webview>` blocked, all permission requests denied.
- Typed preload API: TypeScript interfaces in `src/shared/api.ts` (`AynaApi`, `IPC` channel names); `src/renderer/src/env.d.ts` types `window.ayna`. `npm run typecheck` (`tsc -b`, `tsconfig.node.json` + `tsconfig.web.json`; the renderer config has no Node types) enforces it; ESLint forbids `node:*` / `electron` / main / preload imports in the renderer.

## Decisions (small, local to this task)
- 2026-10-25 — First JSDoc + `tsc` (the tech-stack ADR said JS only); same day the team (galip, omer, hasan, in person) switched the client to TypeScript while it was still a skeleton. Recorded as ADR `2026-10-25-client-typescript.md` (supersedes only the client language of the tech-stack ADR; working-agreement §8 forbids editing accepted ADRs); AGENTS.md, conventions, architecture updated.
- 2026-10-25 — TypeScript `~6.0.3`, not 7: typescript-eslint 8.72 supports only `<6.1`. Added `typescript-eslint` and `@types/node@^24` (Electron 45 ships Node 24) with omer's OK.
- 2026-10-25 — Imports keep the `.ts` extension (`allowImportingTsExtensions`) so `node --test --experimental-strip-types` runs the tests without a test framework or build step.
- 2026-10-25 — Dependencies approved by omer: electron 45, electron-vite 6, vite 8, @vitejs/plugin-react 6, react / react-dom 19 (+ @types), electron-builder 26, eslint 10 + @eslint/js + eslint-plugin-react-hooks + globals, prettier 3 + eslint-config-prettier, typescript 7. All devDependencies (everything is bundled), so the asar holds only `out/` + `package.json`.
- 2026-10-25 — vitest dropped (approved set included it): vitest 4 and 5 crash npm 10 and 11 during install (`Cannot read properties of null (reading 'edgesOut')`, peer chain through `@vitest/mocker` → msw). Tests use `node --test` instead (no dependency). Revisit when component tests are needed.
- 2026-10-25 — No `eslint-plugin-react`: it does not support ESLint 10 yet; ESLint 10 tracks JSX references by itself.
- 2026-10-25 — Dev CSP adds `'unsafe-inline'` for scripts and styles only: the Vite dev server injects an inline React Refresh preamble and inline `<style>` tags (checked in the served HTML). Production CSP has no inline, no eval, and dev allows no remote origin either.
- 2026-10-25 — CI client job: guards removed, now `npm ci` / lint / typecheck / test / build. Job name kept (`client (lint + build)`) so a required check does not break.

## Status
- [x] Scaffold, security module, renderer, configs
- [x] Local (macOS, Node 23, clean `npm ci` with npm 10): lint, typecheck, 10 tests, `npm run build` → `release/mac-arm64/AYNA.app` green
- [x] Packaged app and `npm run dev` probed over CDP: React renders app info through `window.ayna`, `require` / `process` undefined, `window.ayna` frozen, remote fetch / script / image blocked by CSP, `window.open` null, navigation to a remote URL blocked
- [x] Human look at the window: omer, `npm run dev` (manual check below)
- [x] Switched to TypeScript; lint, typecheck, 10 tests, build, CDP probe of packaged app + dev green again
- [ ] Windows: `npm run build` → `release/win-unpacked/AYNA.exe`
- [x] PR #120 opened (`Closes #5`, `Closes #3`); CI run 40218983862 all four jobs green, client job ran the real steps
- [x] `client/AGENTS.md` Commands filled (omer OK)
- Next step: Windows check at the weekly session (`needs-windows-test`, check posted on #5); then review + merge by a human.

## Manual checks
- 2026-10-25 · omer (macOS) · `cd client && npm ci && npm run dev` → "AYNA" window with the Runtime card (ayna-client 0.1.0, Electron 45.0.0, Chromium 156.0.8078.48, Node 24.22.0, darwin) · pass · evidence: text pasted in the session (JS version; TS version probed over CDP, same output)
- Pending Windows session (label `needs-windows-test`, check posted as a comment on #5): `cd client && npm ci && npm run build`, start `release\win-unpacked\AYNA.exe` → same window, Platform `win32`.

## Open issues
- The renderer will need to reach the central server; the current CSP (`connect-src 'self'`) and request allow-list block it. Decide in the server-connection issue whether calls go through main (preferred, keeps the CSP closed) or the server origin is added from config.
- Renderer bundle is not minified (electron-vite default, ~570 kB); fine for local files, revisit if startup is slow.
- electron-builder downloads the Electron zip at build time (and `install-electron` on first `npm run dev`): build machines on the closed network need `ELECTRON_MIRROR` / `electron_config_cache` pointing at a local copy. Packaging/offline-build issue to raise later.

## Handoff
- `npm run dev` runs `install-electron` first: Electron 45 no longer downloads its binary on `npm install`, and electron-vite fails with "Electron uninstall" if it is missing.
- To probe a running app: `npm run dev -- --remoteDebuggingPort 9224` and connect over CDP (`http://127.0.0.1:9224/json`).

## Outcome (fill when the issue closes)
