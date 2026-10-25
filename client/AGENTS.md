# client/ — Electron + React desktop client

Owner: omer. Read `/AGENTS.md` first; this file adds only what is specific to `client/`.

## Layout
- `src/main/` — Electron main process, agent process manager, overlay window
- `src/preload/` — typed bridge to the renderer
- `src/renderer/` — React UI: Spy, repository, editor, runs, healing, NL chat

## Commands
To be filled in when the module is scaffolded (build, test, lint, run). Until then, ask before inventing tooling.

## Rules
- `contextIsolation: true`, `nodeIntegration: false`; renderer never imports Node modules.
- No remote content, CDN fonts or auto-update (closed network).
- UI text in English for now; keep strings in one place for later translation.
