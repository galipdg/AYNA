# Active — Ömerfaruk Sarıbal (`omer`)

Only omer's agent edits this file. Overwrite it at every session end.

- Last update: 2026-10-31 (third session)
- Current issue: **#60** (accounts and roles) on `omer/60-accounts-roles`, stacked on `omer/31-openapi-contract` (#160), not pushed. Server done (54 tests), client login done (40 tests); ADR `2026-10-31-accounts-and-tokens` Proposed. Task note: `tasks/60-accounts-roles.md`
- Next step: admin user management screen in the client; manual login check (`npm run dev` + `docker compose up`); then push and open the PR (base `omer/31-openapi-contract` until #160 merges), reviewers galip + hasan for the ADR.
- Scope change 2026-10-31 (omer's choice): user id on runs → #44 (new criterion), approvals → #74 (already had it).
- Other open work (waiting for teammates): #122 PR #167 (hasan's review); #31+#158 PR #160 and #45 PR #155 approved, waiting for a merge; #48 PR #157 stacked on #155; #17 draft PR #154 `needs-windows-test`; #10 draft PR #126.
- When #160/#155 merge: check #31/#158/#45 closed and Done; retarget #157 and the #60 PR to `main` if GitHub has not.
- Reviewed #166 (galip, DPI): comment, not approved: a `dpi` on only one side zeroes location (verified); the schema rejects `dpi`; #25/#74 must store the target's `dpi` (mine).
- Merge note: this file differs on #160, #167 and the #60 branch; whichever merges later conflicts here → keep the newest version.
- Open questions: project licence undecided; Leotta [4] PDF unread; #159 `workflow_dispatch` UIA dump job (not planned); `server/AGENTS.md` rule for who-did-it (needs omer's OK)
- Inbox: items up to 2026-10-29 handled; delete them once #150 has merged
- Network: SSH to github.com times out; fetch/push over HTTPS with `gh auth git-credential` (see `learnings.md`)
