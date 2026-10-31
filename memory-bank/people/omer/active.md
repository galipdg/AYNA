# Active — Ömerfaruk Sarıbal (`omer`)

Only omer's agent edits this file. Overwrite it at every session end.

- Last update: 2026-10-31
- Current issues (all reviews answered 2026-10-31, waiting for a teammate to merge):
  - #31 + #158: PR #160 (`Closes #31`, `Closes #158`; #163 merged into it). Approved by galip; review points folded in (errorCount cap 50, `urn:ayna:error:` types, JSONPath, idempotent 200, AI errors → problems with `code`); graph schema v0.1 and problem-details ADRs now Accepted on this branch
  - #45: PR #155, approved by galip; his status/retrieval/AI-error points applied
  - #48: PR #157 (stacked on #155), approved by hasan + galip; RQ1–RQ5 points applied
  - #17: draft PR #154, `needs-windows-test`; heartbeat now pings during long calls (agent RPC replies in any order since #135)
  - #10 (team): draft PR #126, `main` merged in; waits for hasan's entries and the plan-copy answer
- Next step: when #160/#155 merge, check #31/#158/#45 closed and Done; retarget #157 to `main` if GitHub has not. Then #25 if #12/#22 have moved (both still open 2026-10-31), else #122 (eval pyproject + CI, Week 2, overdue) or #51.
- Decided 2026-10-31: galip writes #58's server-side retrieval query in `server/`, omer reviews. #25 must not call `/ai/embed` on the write path (FR-28): embed after commit, retry missing vectors (said in the #165 review).
- Open questions: project licence undecided; Leotta [4] PDF unread; #159 asks for a `workflow_dispatch` Windows job running `uia_dump.py` (CI is mine; not planned yet)
- Inbox: every item up to 2026-10-29 is handled; delete them once #150, #164 and #165 (which append to it) have merged, so `merge=union` does not bring them back
- Waiting on: teammates to merge #155/#157/#160; hasan for #10, #12 (blocks #15, #25), #22, #122 input
- Network: SSH to github.com is flaky; fetch/push over HTTPS with `gh auth git-credential` (see `learnings.md`)
