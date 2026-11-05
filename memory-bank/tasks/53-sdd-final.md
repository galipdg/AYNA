# #53 SDD final and submission (7 Dec)

- Issue: https://github.com/galipdg/AYNA/issues/53
- Owner: omer · Branch: `omer/53-sdd-final` (first PR; the issue stays open, `Part of #53`)
- Started: 2026-11-05 · Last update: 2026-11-05

## Approach
Assemble `docs/sdd/SDD.md` in steps. First PR: §5 moved in from `SDD-ai.md` (headings AI-n → 5.n), §7 written from the ADR index, stale status rows fixed. Second step, after the final RS (#41, 23 Nov): §8 Traceability, reference numbers, PDF in `docs/sdd/`.

## Decisions (small, local to this task)
- 2026-11-05 — §5 is one block, by a script, so the only changes are heading level and number, AI-n references and the `---` rules between sections. The file's front matter (editor note, status table, labels) is not moved: §1.6 has the labels, §7 the ADRs.
- 2026-11-05 — Accepted ADRs keep their `SDD AI-n` wording: they are never edited, and the same goes for journals, closed inbox items and old task notes, which are history.
