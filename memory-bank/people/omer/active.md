# Active — Ömerfaruk Sarıbal (`omer`)

Only omer's agent edits this file. Overwrite it at every session end.

- Last update: 2026-10-31 (second session)
- Current issues (all waiting for a teammate):
  - #122: PR #167 (`Closes #122`), CI green (eval job runs the trial app's UIA tests on `windows-latest`); review requested from hasan. omer also did hasan's `eval/` part (user's choice)
  - #31 + #158: PR #160, approved by galip, waits for a merge
  - #45: PR #155, approved by galip; #48: PR #157 (stacked on #155), approved by hasan + galip
  - #17: draft PR #154, `needs-windows-test`; #10 (team): draft PR #126, waits for hasan's entries and the plan-copy answer
- Next step: when #160/#155 merge, check #31/#158/#45 closed and Done; retarget #157 to `main` if GitHub has not. Then #60 (local accounts and roles, the only unblocked issue; touches auth on every API, so start after #160 merges or stack on it). #25 if #12/#22 have moved (both open 2026-10-31).
- Merge note: this file differs on `omer/31-openapi-contract` (#160) and `omer/122-eval-ci` (#167); whichever merges second conflicts here → merge `main` into it and keep this version.
- Decided 2026-10-31: galip writes #58's server-side retrieval query in `server/`, omer reviews. #25 must not call `/ai/embed` on the write path (FR-28): embed after commit, retry missing vectors.
- Open questions: project licence undecided; Leotta [4] PDF unread; #159 asks for a `workflow_dispatch` Windows job running `uia_dump.py` (CI is mine; not planned yet — hosted runners can drive UIA, see `learnings.md` 2026-10-31)
- Inbox: every item up to 2026-10-29 is handled; delete them once #150 (still open) has merged (#164, #165 are in), so `merge=union` does not bring them back
- Waiting on: teammates to merge #155/#157/#160; hasan for #167 review, #10, #12 (blocks #15, #25), #22
- Network: SSH to github.com times out; fetch/push over HTTPS with `gh auth git-credential` (see `learnings.md`)
