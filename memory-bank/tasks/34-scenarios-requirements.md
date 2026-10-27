# #34 Reference scenarios and functional requirements

- Issue: https://github.com/galipdg/AYNA/issues/34
- Owner: galip · Branch: `galip/34-scenarios-requirements`
- Started: 2026-10-27 · Last update: 2026-10-27

## Approach
One file, `docs/rs/scenarios.md`: applications under test, a scenario summary table (the RS §3.1 table), 36 Given/When/Then scenarios grouped by area, the FR tables grouped as RS §3.2.1–§3.2.10, the NFR tables grouped as RS §3.3–§3.8, a traceability section and the open TBDs. It uses the use cases `UC-01`–`UC-16` from the #19 workshop draft (PR #138) as they are, and the RS §1.5 conventions (flat IDs, statement form, Priority / Source / Verification, FR rows list Scenarios) from the #27 outline (PR #137).

Counts were checked with a one-off parser in the session scratch area (not committed): it checks contiguous IDs, matching titles and UCs between the summary and the sections, Given/When/Then in every scenario, 6 or 5 columns per FR or NFR row, valid priority and T/D/I/A values, that every FR lists existing scenarios, and that the §7.1 UC table matches the tags. Result on 2026-10-27: 36 SC (21 main, 11 negative, 4 edge), 40 FR (35 Must, 5 Should), 36 NFR (35 Must, 1 Won't), 0 errors; UC-16 has no FR (NFR only); SC-35 is listed only by an NFR.

## Decisions (small, local to this task)
- 2026-10-27 — FR and NFR tables live in `docs/rs/scenarios.md` for now, because `docs/rs/RS.md` is still on PR #137. #35 moves them into RS §3.2–§3.8 and leaves a pointer, which keeps #27's rule "each requirement in one place".
- 2026-10-27 — Sample-app scenarios name screens and controls generically, and use example logical names (`login.userNameInput`, as in `conventions.md`). The behaviour they assume from #33 is listed in §2 of the file and sent to hasan.
- 2026-10-27 — Pilot-app scenarios (SC-06, SC-07, SC-23) use "P1/P2 (chosen in D1, #21)" with no product name; TBD-1.
- 2026-10-27 — Bug-injected and controlled-change versions are referred to by their change ("wrong label", "AutomationId removed"), not by `bug1`/`v2a`, because #46/#47 do not fix which letter is which.
- 2026-10-27 — Priority follows the plan's cut order exactly. When a cut keeps part of a feature, that part is Must: the impact query (FR-33) and the decision log (FR-36). FR-25/26 (NL generation and validator) are Must because the offline RQ3 measurement is never cut; the chat panel (FR-27) is Should.
- 2026-10-27 — FR-28 ("everything except NL works without the AI service", Must) is separate from the panel's disabled state in FR-27 (Should), so cutting the panel does not drop the ADR's guarantee.
- 2026-10-27 — Proposed numbers (not in the plan or an issue) are written as numbers marked "(proposed, to confirm)" rather than as `TBD-n`, so reviewers can accept or change a value. They are all listed under TBD-4 with an owner.
- 2026-10-27 — Proposed: "element not found" = nothing matches the primary or fallback properties by the end of the wait (healing starts); "timeout" = an element matches but is not visible and enabled in time (no healing) — TBD-5, for hasan (#40, #63). Proposed: after "repair proposed", the test stops and the remaining steps are "not run" — TBD-6, for hasan (#73).
- 2026-10-27 — NFR-32 proposes that every REST/WebSocket request except login needs a session. This means the CLI runner (ROLE-5, no interactive login) needs a non-interactive credential to post results (FR-23). Raised with omer.
- 2026-10-27 — NFR-13 (16 GB RAM, no GPU) is based on #7's measurement (about 5 GB per 8B Q4 model on a 16 GB laptop) and D2's default.

## Status
- [x] Branch, task note, board In progress
- [x] `docs/rs/scenarios.md`: 36 SC, 40 FR, 36 NFR, traceability, TBDs
- [x] Coverage check run (one-off script): 0 errors
- [x] Inbox notes to hasan (#33 assumptions, playback numbers, TBD-5/6) and omer (server numbers, CLI credential)
- [ ] PR opened with `Closes #34`, reviews requested from omerfaruksaribal and HasanBerk18
- Next step: open the PR; then answer review comments. Merge after PR #138 (#19) and PR #137 (#27). If the advisor changes a use case in #19 §7, update the UC tags and §7.1 here.

## Manual checks
- none (documentation only)

## Open issues
- The scenarios depend on #19's use cases, which the advisor has not yet agreed (#19 §7). A changed or withdrawn UC means updating the tags, §7.1 and the FR Source column.
- Q5 (response times and capacity) is open with the advisor. The proposed values in TBD-4 should be confirmed or replaced there.

## Handoff
- #35: move §5 and §6 into `docs/rs/RS.md` §3.2–§3.8 and leave a pointer; copy the §3 summary table into RS §3.1; take the TBDs into Appendix E, starting at TBD-7; build the §5.1 matrix from the FR Scenarios column and the §7.1 table.
- #55 and #62 (building and running the reference scenarios) can start from SC-14, SC-16–SC-22, SC-24 and SC-29–SC-31; those need only the sample app and its versions.

## Outcome (fill when the issue closes)
