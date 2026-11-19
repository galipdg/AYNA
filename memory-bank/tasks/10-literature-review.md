# #10 Literature review part 1 (fragility, locators, self-healing)

- Issue: https://github.com/galipdg/AYNA/issues/10
- Owner: team (omer started it) · Branch: `omer/10-literature-review`
- Started: 2026-10-26 · Last update: 2026-10-26

## Approach
One file, `docs/literature.md`: an assignment table, one entry per source (citation · finding · what it means for AYNA · source checked), grouped by the themes of the project plan's gaps table, and the gaps table copied from the plan ("AYNA – 14-Week Project Plan" in Claude Docs, section "What has been done"). Section 2 is left for #20 (galip).

## Decisions (small, local to this task)
- 2026-10-26 — source list = the 10 in the issue + Alégroth et al. [9], which the plan's gaps table also cites (11 entries).
- 2026-10-26 — split by code ownership: omer Hammoudi [3], Leotta [4], Healenium [23] (healing API #74 / approval screen #75); galip Similo [7], WATER [10], Vista [11] (heal); hasan ROBULA+ [5], contextual clues [6], Luo [12], Sikuli [8], Alégroth [9] (recognition/playback). Proposed to both via inbox; swaps are fine.
- 2026-10-26 — references keep the plan's numbering, so the RS (galip) can reuse them.
- 2026-10-26 — every entry says what was actually read ("Source checked"); no claims from memory.
- 2026-10-29 — gaps table: galip's two wording fixes applied (#132 description): Similo row counts failed localizations (11% vs 27% of 801), test-repair gap names Healenium as the silent healer (WATER, Vista only suggest). The plan doc must get the same two cells.
- 2026-10-29 — numbering: the plan doc in omer's Claude Docs ("AYNA – 14-Week Project Plan", rev 12, 2026-10-18) has Hammoudi [3], survey [14], Healenium [23] — the file matches it. galip's "plan export" ([9] Hammoudi, UFO [24] …) is another copy; which one is canonical is asked of galip (his inbox).
- 2026-10-26 — `docs/literature.md` is in hasan's `docs/` area but is the issue's expected output; editing it is in scope.

## Status
- [x] Branch, task note, board In progress
- [x] `docs/literature.md` skeleton + assignment table + gaps table
- [x] omer's three entries ([3], [4], [23])
- [x] Draft PR #126 (`Closes #10`); galip and hasan add their entries on this branch (user chose one PR over skeleton-first)
- [x] galip's three entries (#132) and section 2 for #20 (#139) merged into this branch; `main` merged in (2026-10-29); #126 body has `Closes #20`
- [ ] hasan's five entries (no activity from hasan since 2026-10-26)
- Next step: settle the plan copy with galip, sync the plan doc's gaps table; when hasan has pushed his entries, check the assignment table is all "done", tick the criteria in #126 and mark it ready for review.

## Manual checks
- none (documentation only)

## Open issues
- Leotta [4]: full PDF unreachable (sepl.dibris.unige.it refused connections 2026-10-26); only the abstract was verified. Read the PDF before the RS cites details.
- Week 1 milestone ends 2026-10-26; #10 needs all three members, so it will close after the milestone date.

## Handoff
Gaps table must stay identical to the plan's; if an annotation changes a finding (e.g. Similo's 27% → 11%), update both.

## Outcome (fill when the issue closes)
