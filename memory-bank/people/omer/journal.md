# Journal — Ömerfaruk Sarıbal (`omer`)

Append-only. One entry per session, newest at the bottom:
`## YYYY-MM-DD · #<issue>` then 2–5 bullets: what changed, decisions, next step.

## 2026-10-25 · #2, #4
- #2: module READMEs + DoD item (#113, merged); closed by omer — "main protected" kept as a rule, GitHub protection still off (owner needs Pro); hasan's test PR pending.
- #4: Spring Boot 4.1.2 / Java 21 / Maven skeleton, `/api/health`, root `docker-compose.yml` (Neo4j 5.26, telemetry off); tests + compose verified locally; #114 merged; CI criterion waits for #3.
- Process: AGENTS.md §3/§6 now say pull `main` at session start, merge `origin/main` before push, move board card to In progress (branch `omer/agents-sync-and-board`).
- Next: #3 CI skeleton.

## 2026-10-25 · #3
- `.github/workflows/ci.yml`: server (`./mvnw -B verify`), client (guarded until #5), agent (windows-latest), ai — ruff + pytest for Python.
- omer chose to write minimal `agent/` + `ai/` packages with one smoke test each; galip + hasan asked to review via inbox. ruff pinned `~=0.17.2`; `ai/spikes/` excluded from ruff.
- All steps green locally; PR opened as `Refs #3` (client criterion waits for #5).
- Next: check the CI run, close #4 with the run link.

## 2026-10-25 · #5
- #3 PR #118 merged. Started #5 on `omer/5-electron-skeleton`, board card → In progress.
- `client/`: electron-vite + React 19 + electron-builder `--dir`; CSP from `src/main/security.js` (meta tag via Vite plugin), request/navigation/window.open/webview blocking in main, frozen `window.ayna` bridge typed with JSDoc + `tsc` (checkJs).
- vitest dropped (crashes npm install), `node --test` instead; Electron 45 needs `install-electron` before `electron-vite dev`.
- Lint, typecheck, 10 tests, build green locally; packaged app and dev probed over CDP (remote fetch/script/img blocked). CI client job now runs the real steps.
- Next: manual check, push, PR, close #3 after the green client job.
- Later: PR #120 opened (also `Closes #3`), CI all green with the real client steps; #4 closed with run 40217766040; `needs-windows-test` + Windows check on #5; `client/AGENTS.md` commands filled.
- Later: team agreed to TypeScript for the client; switched `client/` to `.ts`/`.tsx` (TS 6.0, typescript-eslint, split tsconfigs), ADR `2026-10-25-client-typescript.md` (supersedes the client language only) and updated AGENTS.md / conventions / architecture. omer's manual `npm run dev` check passed.

## 2026-10-25 · #14
- PR #120 merged → #3 and #5 closed and Done. hasan's eval-CI note: opened #122 (hasan: pyproject + ruff; omer: CI job), replied in his inbox.
- Started #14 on `omer/14-graph-schema`, board → In progress. Added neo4j-migrations starter 4.2.0 (omer OK; built for Boot 4.1), `V0001__graph_schema_v0.cypher` (11 unique `id` constraints + 5 indexes), `GraphSchemaMigrationIntegrationTest`, `docs/graph-model.md`, ADR `2026-10-25-graph-schema-migrations.md`.
- `./mvnw test` green (5); compose run: migration applied on start, skipped on restart, all 14 sample queries pass EXPLAIN.
- Next: push + PR `Closes #14` after omer's OK.

## 2026-10-26 · #18
- PR #124 merged → #14 closed and Done. Inbox: #18 and #48 now mine (ADR windows-work-to-hasan).
- Picked #18 (Week 2, no deps; #15/#17 blocked). Branch `omer/18-tool-matrix`, board → In progress.
- Wrote `docs/tool-matrix.md`: 15 rows (user-approved) × 7 tools + AYNA (target); every cell sourced. Link check: all 200 except Ranorex Zendesk (403 to bots), verified via its public API.
- Correction while checking: TestComplete persists a healed locator only if the user accepts it; takeaway reworded.
- Next: PR `Closes #18`, then #32.
