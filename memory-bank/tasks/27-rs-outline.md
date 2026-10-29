# #27 RS outline

- Issue: https://github.com/galipdg/AYNA/issues/27
- Owner: galip · Branch: `galip/27-rs-outline`
- Started: 2026-10-27 · Last update: 2026-10-27

## Approach
One file, `docs/rs/RS.md`: title block, document history, then the numbered SRS headings of ISO/IEC/IEEE 29148:2018 §9.6 adapted to the course. Each heading has one line: what goes there, the issue that fills it (#34, #35, #41), its sources and whose input it needs. No course-provided RS template exists in the repo or the plan, so 29148 is the structure.

Written in full now, because #34/#35 need them fixed before content starts: §1.5 conventions (IDs, statement form, attributes), §4.1 verification methods, Appendix D (mapping to 29148 §9.6).

#19 (requirements workshop, `docs/requirements-workshop.md`, `UC-xx`) is being written in parallel. The outline does not depend on its content: use cases get a slot (§3.1 summary, Appendix B full text) and the workshop notes are referenced by path only.

## Decisions (small, local to this task)
- 2026-10-27 — IDs are flat (`FR-07`, `NFR-04`, `UC-03`, `SC-12`), two-digit, never reused or renumbered; the section gives the area — area prefixes like `FR-REC-01` would change when an FR moves between areas.
- 2026-10-27 — Plan IDs (C1–C4, RQ1–RQ5, H1–H3, G0–G4, D1–D7) are reused as they are; no new prefix for tests — the traceability matrix names the test by pytest node id, eval script or issue comment.
- 2026-10-27 — Attribute set: Priority (MoSCoW tied to the plan's never-cut list and cut order), Source, Verification (T/D/I/A from 29148); FR rows add Scenarios for the FR → SC trace #34 requires; Rationale optional. No separate Type column: the section an NFR sits in is its type.
- 2026-10-27 — Requirement statements use "The ‹component› shall …", shall/should/may, no unmeasured adjectives; open values are `TBD-n`, listed in Appendix E.
- 2026-10-27 — References keep the plan's numbers [1]–[39] so RS, SDD and report share one numbering; new sources start at [40] (29148:2018).
- 2026-10-27 — The submitted RS must stand alone: Appendix B condenses the use cases from the workshop notes and Appendix C includes `docs/rs/scenarios.md` in full in the PDF (#41).
- 2026-10-27 — FRs live once, in RS §3.2 (with their Scenarios column); scenarios live once, in `docs/rs/scenarios.md`; §5 matrix is assembled from both. Avoids keeping two FR tables in sync.
- 2026-10-27 — Files on PR branches (`docs/agent-rpc.md` #135, `schemas/step.schema.json` #134, `docs/literature.md` #126) and files not written yet are named as code paths, not links, so the outline has no broken links on `main`.

## Status
- [x] Branch, task note, board In progress
- [x] `docs/rs/RS.md` outline
- [x] PR #137 opened (`Closes #27`), reviews requested from omerfaruksaribal and HasanBerk18
- [ ] Approved by all three
- Next step: answer review comments on #137; when Ömerfaruk and Hasan have approved, Galip approves and the PR merges.

## Manual checks
- none (documentation only)

## Open issues
- The plan's "Team and roles" and WP1 rows still name Hasan as RS lead; ADR `2026-10-25-windows-work-to-hasan` moved the RS chain to Galip. The plan document (Claude Docs) is outside the repo; update it when the plan is next revised.
- The project's own licence is undecided (also raised in `memory-bank/tasks/18-tool-matrix.md`); the RS lists it in Appendix E. Needs a team decision before #41.

## Handoff
- #34 writes `docs/rs/scenarios.md` (SC) and the FR tables in RS §3.2 using §1.5; #35 fills every other section and removes the one-line notes as it goes.
- `UC-xx` come from #19's `docs/requirements-workshop.md`; if #19 picks a different use-case ID format, align §1.5 in #35.

## Outcome (fill when the issue closes)
