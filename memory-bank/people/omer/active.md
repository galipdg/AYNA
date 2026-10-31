# Active — Ömerfaruk Sarıbal (`omer`)

Only omer's agent edits this file. Overwrite it at every session end.

- Last update: 2026-10-31 (fifth session)
- Current issue: **#60** (accounts and roles). PR #168 was merged into `omer/31-openapi-contract` without review and **reverted** there (`48dfd5a`); a new PR to `main` follows after #160 merges, reviewers galip + hasan (ADR `2026-10-31-accounts-and-tokens` Proposed, needs both). Server + client + user management done; 51 client tests. Task note: `tasks/60-accounts-roles.md`
- Next step: manual check passed on macOS 2026-10-31. When #160 merges: merge `origin/main` into `omer/60-accounts-roles`, rerun tests, open the new #60 PR to `main`. Meanwhile pick the next issue (#25 if #12/#22 moved, else #122 or #51).
- Scope change 2026-10-31 (omer's choice): user id on runs → #44 (new criterion), approvals → #74 (already had it).
- Other open work (waiting for teammates): #122 PR #167 (hasan's review); #31+#158 PR #160 and #45 PR #155 approved, waiting for a merge; #48 PR #157 stacked on #155; #17 draft PR #154 `needs-windows-test`; #10 draft PR #126.
- When #160/#155 merge: check #31/#158/#45 closed and Done; retarget #157 to `main` if GitHub has not; open the new #60 PR.
- Reviewed #166 (galip, DPI): comment, not approved: a `dpi` on only one side zeroes location (verified); the schema rejects `dpi`; #25/#74 must store the target's `dpi` (mine).
- Merge note: this file differs on #160, #167 and the #60 branch; whichever merges later conflicts here → keep the newest version.
- Open questions: project licence undecided; Leotta [4] PDF unread; #159 `workflow_dispatch` UIA dump job (not planned)
- Inbox: items up to 2026-10-29 handled; delete them once #150 has merged
- Network: SSH to github.com times out; fetch/push over HTTPS with `gh auth git-credential` (see `learnings.md`)
