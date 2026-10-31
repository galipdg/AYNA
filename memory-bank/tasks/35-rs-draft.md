# #35 RS draft

- Issue: https://github.com/galipdg/AYNA/issues/35
- Owner: galip · Branch: `galip/35-rs-draft` (from `galip/27-rs-outline`, with `galip/34-scenarios-requirements` and `galip/19-requirements-workshop` merged in)
- Started: 2026-10-27 · Last update: 2026-10-27

## Approach
Fill every section of the #27 outline in `docs/rs/RS.md` from the brief, the plan export, the ADRs, `docs/graph-model.md`, `docs/agent-rpc.md` (PR #135), the step schema (PR #134), the tool matrix and the two stacked drafts: #34's `docs/rs/scenarios.md` and #19's `docs/requirements-workshop.md`. The branch is stacked on PRs #137, #140 and #138, so it merges after them.

Consistency was checked with a one-off script in the session scratch area (not committed). It checks that every FR/NFR/UC/SC/TBD ID referenced in RS.md or scenarios.md is defined exactly once and that the §3.1 summaries match the definitions. It also checks that the rows moved from #34 are unchanged except for the intended edits, every FR traces to at least one SC, every UC has an SC and an FR (except UC-16), every SC is evidence for some requirement, the Appendix B lists match the FR Source columns and SC tags, and the §5.1 matrix and §5.2 list match the derived trace. Result on 2026-10-27: 0 errors; 36 SC, 16 UC, 40 FR (35 Must, 5 Should), 44 NFR (42 Must, 1 Could, 1 Won't), 11 TBD.

## Decisions (small, local to this task)
- 2026-10-27 — `scenarios.md` becomes the Appendix C source (headings C.1–C.3), as #27 planned ("Appendix C includes scenarios.md in full"). The FR/NFR tables (#34 §5, §6), the traceability (§7) and the TBDs (§8) moved into RS.md, as #34 decided.
- 2026-10-27 — The scenario summary table was **moved** to RS §3.1, not copied as #34's handoff said. Keeping two copies would break the "one place per item" rule of #27.
- 2026-10-27 — Moved FR/NFR rows were not reworded. The only cell edits are the Verification cells of NFR-07 and NFR-08: "load test, planned in #35" became TBD-9, because no issue or tool exists for it. Two NFRs from #34's "Interfaces and portability" table moved to their outline homes: NFR-20 to §3.5.1, and NFR-19 and NFR-21 to §3.8.5.
- 2026-10-27 — Added NFR-37–NFR-44, each from an existing source; no new scope:
  - NFR-37: NL accuracy ≥ 60 %, a semester-1 success criterion that #34 had no NFR for.
  - NFR-38, NFR-41: UUID ids and migrations, from ADR graph-schema-migrations.
  - NFR-39: per-version snapshots, needed for C3.
  - NFR-40: screenshots as files, removed with their run (#51).
  - NFR-42: standards compliance for the contracts.
  - NFR-43: site settings through env vars (conventions).
  - NFR-44: backup and restore described in the install guide (#91), **Could**, because no plan item requires it.
  - No new "(proposed, to confirm)" numbers.
- 2026-10-27 — §5.1 matrix has one row per use case (UC → SC → FR → NFR → verification issues), not one row per requirement. Per-requirement verification stays in the Verification column of §3, so it is not kept twice. NFRs whose Source names no UC are listed by source in §5.2. The per-requirement evidence status column is added at G2 (#70) and G3 (#88).
- 2026-10-27 — UC priority in §3.1 and Appendix B maps the workshop's cut-order Prio to MoSCoW: M → Must, S1–S4 → "Should (cut n)", naming the part that stays Must.
- 2026-10-27 — Advisor questions Q1–Q8 are listed in Appendix E.2 by their own IDs rather than as TBD-n, because they are stable workshop IDs. Q4, Q5 and Q7 are cross-referenced to TBD-2, TBD-4 and TBD-1.
- 2026-10-27 — New references: [41] JSON Schema 2020-12, [42] JSON-RPC 2.0 and [43] OpenAPI 3, after [40] 29148 as the outline set. They clash with #20's provisional [40]–[47]: TBD-11.
- 2026-10-27 — Assumption written in §1.3.5: playback needs an unlocked interactive desktop, also on the CI runner. Real input fails on a locked session. Sent to hasan for #67.

## Status
- [x] Branch from #27 with #34 and #19 merged (sequential merges; the octopus merge stopped on hasan's inbox, which the union driver resolves in a normal merge)
- [x] Board: #35 In progress
- [x] Every outline section filled; outline notes removed
- [x] scenarios.md restructured into Appendix C
- [x] Consistency check: 0 errors
- [x] PR https://github.com/galipdg/AYNA/pull/143 opened (`Closes #35`, stacked on #137, #140, #138), reviews requested from omerfaruksaribal (required) and HasanBerk18 (FYI)
- [ ] Reviewed by Galip and Ömerfaruk with comments resolved (human step)
- Next step: answer review comments on the #35 PR. After the advisor meeting, apply #19 §7's answers (Q1–Q8) to §1.3.3, §3.1, Appendix B and E.2, and rerun the check.

## Manual checks
- none (documentation only)

## Open issues
- TBD-9: the load test for NFR-07/NFR-08 has no issue. Suggest a new issue (omer, before G2); noted in his inbox.
- TBD-8: the plan document (Claude Docs) still names Hasan as RS lead.
- TBD-11: one reference numbering for RS, SDD, report and `docs/literature.md` is needed before #41.
- The RS rests on #19's draft use cases until the advisor agrees them (Appendix E.2).

## Handoff
- #41 builds the PDF: RS.md, then `scenarios.md` as Appendix C. Its headings already carry C.x numbers, and its in-text references use C.2.
- When a UC, SC or requirement changes, rerun an equivalent check. The script is not in the repo; the checks are listed in RS §5.3.

## Outcome (fill when the issue closes)
