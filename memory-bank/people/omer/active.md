# Active — Ömerfaruk Sarıbal (`omer`)

Only omer's agent edits this file. Overwrite it at every session end.

- Last update: 2026-10-29
- Current issues:
  - #158 (RFC 9457 error body, Week 4): PR #163 on `omer/158-problem-details`, **stacked on #160** (base `omer/31-openapi-contract`); reviewers galip + hasan for the Proposed ADR `2026-10-29-rest-error-problem-details`
  - #31 (OpenAPI contract v0): PR #160 (`Closes #31`), CI green, review requested from galip
  - #48 (SDD test design): PR #157; #45 (SDD sections 1–4): PR #155 — both wait for galip's review
  - #17 (agent process manager): draft PR #154, `needs-windows-test`; after the Windows run, `Closes #17` and ready
  - #10 (literature, team): draft PR #126 waits for hasan's entries and the plan-copy answer
- Next step: check CI on #163; answer reviews on #155/#157/#160/#163. When #160 merges: merge `origin/main` into `omer/158-problem-details` and retarget #163 to `main`. Then #25 (repository) if #12/#22 have moved — #25 throws the shared `ApiExceptions` and writes `(Application)-[:HAS_OBJECT]->(RepoObject)` (see `tasks/39-tests-steps-api.md` Handoff).
- Open questions: FR-07 uniqueness per application vs "per version" (ADR on #156 says per application); project licence undecided; Leotta [4] PDF unread; inbox has three handled items (2026-10-25..27) to delete when no open PR touches the inbox
- Waiting on: galip for reviews of #155/#157/#160/#163; hasan (pushed `hasan/6-uia-dumps` on 2026-10-29) for #10, #12 (blocks #15, #25), #22, #122 and the #163 ADR approval
- Network: SSH fetch works again, but push over HTTPS with `gh auth git-credential` (token has `workflow` scope; see `learnings.md`)
