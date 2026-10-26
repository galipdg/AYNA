# Active — Ömerfaruk Sarıbal (`omer`)

Only omer's agent edits this file. Overwrite it at every session end.

- Last update: 2026-10-26
- Current issues:
  - #128 (applications/versions API): done, PR #129 open (`Closes #128`, CI green) on `omer/128-apps-api`; waits for review + merge
  - #32 (server settings + picker): all parts done (URL + check, picker with create, remembered choice), both manual checks passed; draft PR #127 (CI green) on `omer/32-server-settings`
  - #10 (literature review, team): draft PR #126 on `omer/10-literature-review` waits for galip's and hasan's entries
- Next step: when #129 is merged, `#128` → Done; merge `origin/main` into `omer/32-server-settings`, rerun client checks, switch PR #127 body to `Closes #32` and mark it ready. Then pick the next issue (Week 2 first).
- Open questions: the project's own licence is undecided (noted in `tasks/18-tool-matrix.md`); Leotta [4] full PDF unread (server unreachable); `/api/health` unbounded while Neo4j shuts down (see `tasks/32-server-settings.md`); duplicate-name race in #128 (see `tasks/128-apps-api.md`)
- Waiting on: review of #129; galip + hasan for #10 entries; hasan for the `eval/` part of #122 before omer adds the CI job
- Network: SSH to github.com times out here; push/fetch over HTTPS with `gh auth git-credential` (see `learnings.md`)
