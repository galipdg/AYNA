# Active — Ömerfaruk Sarıbal (`omer`)

Only omer's agent edits this file. Overwrite it at every session end.

- Last update: 2026-11-19 (PR reviews; #53 §8)
- **Current issue: #53** (SDD final, due 7 Dec). Branch `omer/53-sdd-traceability` (not pushed): v0.6 with §8 Traceability from RS 1.0 as on galip's PR #267 (86 IDs, each once, refs checked), §9 row 13 settled, Agent/CLI rows after #54/#66. Next: push + PR on omer's OK; after #267 merges re-check the IDs against `main`; then one reference numbering (§1.5, §5.10, `docs/literature.md`, RS) and the PDF (ask galip about reusing `docs/rs/build_pdf.py`).
- **Merged 2026-11-19 (omer's PR sweep):** #259 (with #260, #270 stacked into it; #36 stays open), #262 (closed #67), #263 (#261 stays open, `needs-windows-test`), #267 (RS 1.0; §8 here matches it). #126 marked ready (closes #10, #20), reviews asked. #266 (hasan) has code conflicts in `agent/tests/conftest.py` and `test_playback_runner.py` after #268; hasan said he resolves them.
- **Waiting on Windows / hasan:** #261 (screenshot upload), #44 check B (task note `44-run-from-editor.md`), #24, #68, #183, #184, #204, #206. CI works again (2026-11-19 afternoon).
- **Reviewed 2026-11-19 (all approved):** galip's #267 (RS 1.0; notes: #44 "Windows check pending" in §1.3, no agent `highlight` method in §3.5, NFR-06 could cite 69 ms), #269 (client already sends `runId`; fits #263), #270 (§6.3/§6.7 match the editor); hasan's #266, #268.
- **Owed by omer (small client fix):** the editor's result rows show a step's message only when it failed (`StepTable.tsx`, `step-failure` row); a *passed* step's message (SelectRow "selected but not current", "selects cells") is hidden. The report already shows it. Promised on #268.
- **Follow-ups owed**: #226's client half; a client check of the agent's major `rpcVersion`; `--screenshots` in the load test (#152); promised issues from #250 (named suite subset, version order "1.10" < "1.9", window title on repo objects, `matched`/`performedWith`).
- PR #246 (#245, report async auth) still waits for a review. Raise the licence (TBD-7, before #90) at the next team meeting.
- ADRs still **Proposed**: `2026-10-31-healing-proposal-schema-0-2`, `2026-10-31-accounts-and-tokens`, `2026-11-07-window-snapshot-unique`, `2026-11-15-failure-category` (hasan's approval).
- **AGENTS.md** §2 lists hasan as `@HasanBerk18`; his login is `hasanberkyanikkaya`. Changing AGENTS.md needs omer's OK.
- Inbox: items up to 2026-11-15 handled; delete them in a branch of their own (`merge=union`).
- Many old worktrees/branches in `.claude/worktrees/` (see `git worktree list`); delete only on omer's OK.
- Network: SSH to github.com times out. Use HTTPS: `git -c credential.helper='!gh auth git-credential' -c url."https://github.com/".insteadOf="git@github.com:" push origin <branch>` — one push per command (also for `fetch`).
- Local env: `JAVA_HOME=$(/usr/libexec/java_home -v 21) ./mvnw test` (regenerates `docs/api/openapi.yaml`; commit it). A worktree needs its own `npm ci` in `client/`.
