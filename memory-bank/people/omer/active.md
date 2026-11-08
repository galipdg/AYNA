# Active — Ömerfaruk Sarıbal (`omer`)

Only omer's agent edits this file. Overwrite it at every session end.

- Last update: 2026-11-08 (fifteenth session: #205 built)
- **Current issue: #205** (SelectRow and row checks in the editor) on `omer/205-selectrow-rows` (worktree `.claude/worktrees/selectrow-step-schema-rows-642084`). Code, tests, en/tr and `docs/ui/` done and committed; task note `memory-bank/tasks/205-selectrow-rows.md`.
- **Next step** (resume here): push `omer/205-selectrow-rows` and open the PR (`Closes #205`) after omer's OK; then propose the next issue (#44 client half needs #40; #53 next step; #206).
- **Waiting for review:** #219 (#204 Spy follow-ups, also needs the Windows check), #218 (#203 wording), #217 (#207 demo seed).
- **Follow-ups from #205** (task note "Open issues"): column dropdown needs `columns` on a grid's RepoObject and column headers in the snapshot (hasan's schema, ADR) — suggest an issue; English action column clips "Choose item"/"Choose row"; demo seed has no grid or list object.
- Issues left open on purpose: #17 (`needs-windows-test`), #24 (hotkey needs #22), #183, #184, #185, #38 (Windows findings in #206).
- Inbox: emptied 2026-11-08 (every item handled, #150 merged).
- **CI**: since 2026-11-08 morning the client job's `npm run build` fails on `main` and every PR with `Response code 504 (Gateway Time-out)` from a download electron-builder makes after Electron itself; lint, typecheck and tests pass in the same job. Reruns sometimes pass. If it persists, cache electron-builder's downloads in CI or skip `electron-builder --dir` on Linux (CI is `.github/`, ask first).
- **Open from #209's review** (hasan, non-blocking): `.env.example` points at `AYNA_SERVER_URL`, which nothing reads (wire it for the CLI #61 or say it is reserved); binding `127.0.0.1:` would make a taken port fail loudly (LAN trade-off). hasan runs the real port-8080 check at the next Windows session.
- Local branches of the merged stack (`omer/17…`, `omer/24…`, `omer/25…`, `omer/183…`, `omer/184…`, `omer/185…`, `omer/30…`, `omer/38…`, `omer/196…`) are still here; delete them only on omer's OK. Worktrees: `omer/195-advisor-demo` in the main folder, `omer/15-snapshot-import`, `omer/53-sdd-final` and `omer/44-run-api` in `.claude/worktrees/` (all merged).
- Open questions: project licence undecided; Leotta [4] PDF unread; Electron renderer not visible to UIA on Windows (hasan, #17 comment); galip's ADR approval on runs-api-and-live-updates.
- Network: SSH to github.com times out. Fetch and push over HTTPS: `git -c credential.helper='!gh auth git-credential' -c url."https://github.com/".insteadOf="git@github.com:" push origin <branch>` — one push per command.
- Local env: `JAVA_HOME=$(/usr/libexec/java_home -v 21) ./mvnw test` (regenerates `docs/api/openapi.yaml`; commit it). Stale surefire reports survive a branch switch; count only fresh ones. The `ai/.venv` and `agent/.venv` in the main folder have pytest; neither has PySide6, so the trial app's tests do not run on this Mac.
