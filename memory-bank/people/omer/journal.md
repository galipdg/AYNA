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
