# Active — Ömerfaruk Sarıbal (`omer`)

Only omer's agent edits this file. Overwrite it at every session end.

- Last update: 2026-10-29
- Current issues:
  - #39 (tests and steps API): done, PR #156 (`Closes #39`, CI green) on `omer/39-tests-steps-api`; needs galip's and hasan's approval of the Proposed ADR `2026-10-29-graph-schema-application-links`, then switch it to Accepted in the same PR
  - #45 (SDD sections 1–4): PR #155 (`Closes #45`) on `omer/45-sdd-architecture`; waits for galip's review (acceptance criterion)
  - #17 (agent process manager): draft PR #154, `needs-windows-test`; after the Windows run, `Closes #17` and ready
  - #10 (literature, team): draft PR #126 waits for hasan's entries and the plan-copy answer
- Next step: answer reviews on #155/#156. Then #48 (SDD test design, no deps) — or #25 (repository) if #12/#22 have moved; #25 must write `(Application)-[:HAS_OBJECT]->(RepoObject)` (see `tasks/39-tests-steps-api.md` Handoff).
- Open questions: FR-07 uniqueness per application vs "per version" (ADR on #156 says per application); REST error body for all APIs (#31, RFC 9457 proposed, used in `tests/`); project licence undecided; Leotta [4] PDF unread
- Waiting on: galip for reviews of #155/#156 and for merging `main` into his six PRs (inbox note travels with #155); hasan (inactive since 2026-10-26) for #10, #12 (blocks #15), #22, #122 and the #156 ADR approval
- Network: SSH to github.com times out here; push/fetch over HTTPS with `gh auth git-credential` (see `learnings.md`)
