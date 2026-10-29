# Active — Ömerfaruk Sarıbal (`omer`)

Only omer's agent edits this file. Overwrite it at every session end.

- Last update: 2026-10-29
- Current issues:
  - #31 (OpenAPI contract v0): PR #160 (`Closes #31`) on `omer/31-openapi-contract`, review requested from galip; CI green
  - #48 (SDD test design): PR #157; #45 (SDD sections 1–4): PR #155 — both wait for galip's review
  - #39: merged (PR #156)
  - #17 (agent process manager): draft PR #154, `needs-windows-test`; after the Windows run, `Closes #17` and ready
  - #10 (literature, team): draft PR #126 waits for hasan's entries and the plan-copy answer
- Next step: answer reviews on #155/#157/#160. Then #158 (RFC 9457 error body for all APIs, split from #31; ask which milestone) — or #25 (repository) if #12/#22 have moved; #25 must write `(Application)-[:HAS_OBJECT]->(RepoObject)` (see `tasks/39-tests-steps-api.md` Handoff).
- Open questions: milestone for #158; FR-07 uniqueness per application vs "per version" (ADR on #156 says per application); project licence undecided; Leotta [4] PDF unread; inbox has three handled items (2026-10-25..27) to delete when no open PR touches the inbox
- Waiting on: galip for reviews of #155/#157/#160; hasan (inactive since 2026-10-26) for #10, #12 (blocks #15, #25), #22, #122
- Network: SSH to github.com times out here; push/fetch over HTTPS with `gh auth git-credential` (token now has `workflow` scope; see `learnings.md`)
