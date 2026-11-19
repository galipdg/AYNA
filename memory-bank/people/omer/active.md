# Active — Ömerfaruk Sarıbal (`omer`)

Only omer's agent edits this file. Overwrite it at every session end.

- Last update: 2026-11-19 late (#53 SDD 1.0 and its PDF)
- **Current issue: #53** (SDD final, due 7 Dec). PR #271 (`omer/53-sdd-traceability`, Part of #53, reviewers galip and hasan): now **v1.0** with `docs/sdd/SDD-1.0.pdf` (33 pages, 10 diagrams; build `python docs/sdd/build_pdf.py` with markdown 3.11.3). Next: push, reviews, merge; rebuild the PDF if a later merge changes a status row; submit by 7 Dec; galip fixes §5.1's #63 row (inbox).
- **PR #272** (`omer/44-passed-message`, Part of #44): a passed step's message under its row; reviewer hasan, check at the Windows session with #268's SelectRow case.
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
