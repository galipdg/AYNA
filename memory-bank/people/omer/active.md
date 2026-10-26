# Active — Ömerfaruk Sarıbal (`omer`)

Only omer's agent edits this file. Overwrite it at every session end.

- Last update: 2026-10-26
- Current issues:
  - #32 (server settings + picker): URL setting + connection check done, draft PR #127 (`Refs #32`, CI green, manual check passed) on `omer/32-server-settings`; picker blocked on #15's applications list
  - #10 (literature review, team): draft PR #126 on `omer/10-literature-review` waits for galip's and hasan's entries
- Next step: propose splitting the applications list/create part of #15 off from snapshot import (blocked on hasan's #12), so #32's picker can go ahead; else pick the next unblocked issue
- Open questions: the project's own licence is undecided (noted in `tasks/18-tool-matrix.md`); Leotta [4] full PDF unread (server unreachable); `/api/health` unbounded while Neo4j shuts down (see `tasks/32-server-settings.md`)
- Waiting on: galip + hasan for #10 entries; hasan for the `eval/` part of #122 before omer adds the CI job
- Network: SSH to github.com times out here; push/fetch over HTTPS with `gh auth git-credential` (see `learnings.md`)
