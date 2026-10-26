# #18 Tool comparison matrix

- Issue: https://github.com/galipdg/AYNA/issues/18
- Owner: omer · Branch: `omer/18-tool-matrix`
- Started: 2026-10-26 · Last update: 2026-10-26

## Approach
One Markdown file, `docs/tool-matrix.md`: 15 feature rows × the 7 tools in the issue, plus an "AYNA (target)" column. Short cells, sources as footnotes (vendor docs, repo/package pages; *3rd party* only where the vendor publishes nothing). Rows follow AYNA's scope in `memory-bank/project/brief.md`, so the matrix also shows the gap AYNA fills (input for the RS and the literature review, #10).

## Decisions (small, local to this task)
- 2026-10-26 — cells are backed by public documentation links, not "tested by us" — we work on macOS; hands-on checks would need the weekly Windows session and licences we do not have. A cell can be upgraded to "tested by us" later.
- 2026-10-26 — `docs/tool-matrix.md` sits in hasan's `docs/` area but is the issue's expected output (#18 was reassigned to omer, ADR windows-work-to-hasan), so editing it is in scope.
- 2026-10-26 — user approved the 15 rows and the extra "AYNA (target)" column.
- 2026-10-26 — Robot Framework's desktop column assumes robotframework-flaui (maintained, built on FlaUI); core RF has no Windows driver.
- 2026-10-26 — AYNA licence cell says "licence-free" (AGENTS.md §1), not "open source": no decision on the project's own licence exists.

## Status
- [x] Branch, task note, board In progress
- [x] Feature rows agreed with the user
- [x] Cells filled with sources; links checked (all remote links 200; support.ranorex.com blocks curl with 403, so those articles were checked through its public Zendesk API `/api/v2/help_center/en-us/articles/<id>.json`)
- [ ] PR
- Next step: ask the user to push and open the PR (`Closes #18`).

## Manual checks
- none planned (documentation only)

## Open issues
- The project's own licence (e.g. MIT/Apache) is undecided; the RS will likely need it. Suggest raising it with the team.

## Handoff
- Correction found while checking: TestComplete persists a healed locator only if the user accepts the fix after the run, so "no approval step at all" is wrong for TestComplete; the takeaway now says healing happens *during* the run in all three commercial tools.
- Commercial prices are not published by any of the three vendors; the matrix cites the vendors' quote pages instead of third-party price figures.

## Outcome (fill when the issue closes)
