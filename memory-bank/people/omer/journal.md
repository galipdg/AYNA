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

## 2026-10-26 · #32
- Started #32 on `omer/32-server-settings`, board → In progress; agreed with omer to keep #32 open until the picker (needs #15) instead of splitting it.
- Client: `src/main/server.ts` (URL normalisation + `/api/health` check, 5 failure types), `src/main/settings.ts` (`userData/settings.json`), IPC `settings:get` / `server:check` / `server:connect`, `ServerSettings.tsx` first-run screen. 22 tests green, build green; checked against the real compose backend (all 5 outcomes); omer's manual UI check passed (7 steps).
- Draft PR #127 (`Refs #32`), CI green.
- Next: picker after #15; propose splitting #15's applications list off snapshot import.

## 2026-10-26 · #128, #32
- #128 on `omer/128-apps-api`: `server/.../apps/` (`AppController`, `AppService` with plain Cypher via `Driver`), 4 endpoints with 400/404/409; duplicate checks in the create transaction, no constraint (omer chose option (a)); `technology` free text. `AppIntegrationTest` 7 cases, `./mvnw -B verify` green. PR #129, CI green. OpenAPI criterion left unticked (generation arrives with #31).
- #32 picker: `client/src/main/apps.ts`, IPC `apps:list|create|choose`, `AppPicker.tsx` with create form (omer's choice), `applicationId` in `Settings`, cleared on server change. 33 tests + build green; `apps.ts` checked against the real #128 server; omer's 8-step manual check passed. Pushed; PR #127 CI green.
- Next: after #129 merges, merge main into #32, mark #127 ready with `Closes #32`.

## 2026-10-29 · review round
- After three days away: #127 (#32) and #129 (#128) merged; galip opened 13 PRs needing omer's review; hasan inactive since 2026-10-26.
- Approved #134, #135 (contracts), #141, #146, #150, #151 with server/client notes; decisions posted on #140, #143, #144; opened #152 (load test, TBD-9).
- #10: merged main into `omer/10-literature-review`, applied galip's gaps-table fixes in `literature.md` and in the plan doc (Claude Docs, rev 17); found the plan doc's numbering matches the file, galip's export is another copy (asked on #126). `Closes #20` added to #126.
- Carried the unpushed #32 note commit over to this branch; cleared handled inbox items.
- Next: content reviews of the RS PRs, then #17.

## 2026-10-29 · RS content reviews
- #140 had merged before the review; my NFR confirmation on it stands. Approved with comments: #137 (RS outline; reference numbering waits for the plan copy on #126), #138 (workshop: API token for ROLE-5, uniqueness per AppVersion, UC-12 outline only with the AUT open), #143 (RS draft: apply TBD-9/10, FR-07/FR-08, server-down availability NFR, AI port, NFR-07 excludes screenshot uploads), #144 (SDD AI: retrieval through the server, AI-9 #6–#8 settled, #78 pass-through).
- Backup/restore: kept as NFR-44 (Could) in my install guide #91 (omer's choice), follow-up comment on #137.
- `gh pr review` posts needed explicit user OK (auto-mode classifier).
- Next: #17.

## 2026-10-29 · reviews, #45 SDD, #39 tests API
- Reviews: approved #142 (note: `objects` needs per-object `columns` once `column` becomes an enum); comment on #145 (all 12 pairs fail under #150's 0.2 → merge #150 first, then relabel).
- #45: `docs/sdd/SDD.md` skeleton (IEEE 1016, omer's choice) + sections 1–4; galip's AI block = §5 (answer in his inbox). PR #155, review requested from galip; diagrams checked by omer.
- galip's six PRs (#143–#146, #150, #151) show as conflicting on GitHub: only `merge=union` inbox files, except #151 (ADR index). Note in galip's inbox and in #155's body (learnings entry).
- #39: tests and steps API, networknt validator 3.0.8, V0002 + Proposed ADR (HAS_TEST, HAS_OBJECT), Docker context at repo root. 32 server tests green, CI green. PR #156, reviewers galip + hasan.
- Next: answer reviews on #155 and #156; then #48 (SDD test design) or #25 once #12/#22 move.

## 2026-10-31 · #122 eval CI
- #160/#155 not merged yet, #12/#22 still open → took #122. hasan had not done his `eval/` part, so omer did both halves (user's choice; hasan told in his inbox, reviewer on the PR).
- `eval/pyproject.toml` (deps only, `packages = []`; pywinauto win32-only; jsonschema for `nl/check_pairs.py`), `requirements.txt` removed, ruff 0.17 clean with `spikes/` excluded, `eval` CI job on `windows-latest`. `eval/AGENTS.md` and CI changes approved by the user.
- CI green: the 5 `test_uia.py` UIA tests run on the hosted Windows runner (learnings entry, useful for #67). PR #167.
- Slip: first push went out before merging the new `origin/main` (#164); merged, re-tested and pushed again, no force.
- Next: after #160/#155 merge, close-out checks; then #60.

## 2026-10-31/11-01 · #24 resume
- #24 blocked on #12 (snapshot schema) and #22 (`elementFromPoint`); pushed `937a06f` (pick hotkey) over HTTPS; reminders on #12 (draft schema, or fields in a comment and omer drafts it; answer by 2 Nov) and #22 (RPC contract first).
- Hotkey manual check on macOS with a scratch stub server + fake agent (`AYNA_AGENT_PYTHON`): all steps pass (omer). Stopped the `ayna` Compose stack (`stop`, data kept).
- Merged `origin/main` (#6, #11, #122, #149, #166, #172, #177) into the branch; client lint, typecheck, 66 tests green.
- Found on `main`: hasan's #17 Windows run, 6/7 pass, `agent.test.ts:160` fails (no signals on Windows); #11 element schema unblocks the Spy property panel.
- Next: fix #17 on Windows semantics, then the #24 property panel against `schemas/element.schema.json`.
