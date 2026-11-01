# Active — Ömerfaruk Sarıbal (`omer`)

Only omer's agent edits this file. Overwrite it at every session end.

- Last update: 2026-11-01 (third session)
- Current issue: **#24** (Object Spy) on `omer/24-object-spy` (stacked on `omer/17-agent-process-manager`, draft PR #154, no PR of its own yet). Window list, highlight, pick hotkey and property panel done and manually checked on macOS; `npm run dev:mock` (stub server + fake agent, `client/dev/mock/`) for manual checks. 77 client tests. Task note: `tasks/24-object-spy.md`
- Next step:
  1. #24 element tree on snapshot 0.1 (hasan's PR #180: flat pre-order `{id, parentId, element}`): `snapshot` on window select, one-pass tree, panel fed by the selected node, `capture` shown, `-32001`/`-32002` messages; `dev:mock` fake agent answers `snapshot` with `trial-login.json` (copy from #180 until it merges).
  2. #179 (#60): no human review yet from galip or hasan; answer when they come. Both must approve ADR `2026-10-31-accounts-and-tokens`.
  3. #17: Windows re-run requested (57 tests + "failed" message without INFO line); `needs-windows-test` stays until it passes, then PR #154 → `Closes #17`, ready for review.
  4. #22 (`elementFromPoint`) still open; the pick handler waits for it.
- Reviews: approved #180 (snapshot schema ADR) 2026-11-01 with 5 non-blocking points (stale `rpc.main()` comment, `durationMs` 312 vs 29, 409 on a repeat `snapshotId` with another body for #15, `readErrors`/`agentVersion` optional, `\S` pattern in 0.2). galip's approval pending.
- Merged 2026-11-01 at omer's explicit request: #178, #160, #155, #157, #173 (after a `main` merge pushed to galip's branch, omer's choice). Not merged: #176, #150 (galip), #169, #170 (hasan): all conflict with `main` only in append-only memory files (GitHub ignores `merge=union`); notes left on each PR. #150 also needs hasan's approval, #180 galip's.
- Inbox: everything up to 2026-11-01 handled (incl. hasan's #12 note, answered by the #180 review). Delete the handled items once #150 has merged, so `merge=union` does not bring them back.
- Merge note: this file differs on the #60 branch (#179) and this branch; whichever merges later conflicts here → keep the newest version.
- Open questions: project licence undecided; Leotta [4] PDF unread; #159 `workflow_dispatch` UIA dump job (not planned); Electron renderer not visible to UIA on Windows (hasan, #17 comment) — candidate issue; off-screen/minimized windows' highlight (#24 task note, Open issues)
- Network: SSH to github.com times out; fetch and push over HTTPS with `gh auth git-credential` (see `learnings.md`)
- Local env: `agent/.venv` lacks `websockets` (and `pywinauto` after #180): reinstall with `pip install -e ".[dev]"` before running the real agent. `JAVA_HOME`: run Maven as `JAVA_HOME=$(/usr/libexec/java_home -v 21) ./mvnw test` until `~/.zshrc` is fixed.
