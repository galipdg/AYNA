# #48 SDD: test design section

- Issue: https://github.com/galipdg/AYNA/issues/48
- Owner: omer · Branch: `omer/48-sdd-test-design` (stacked on `omer/45-sdd-architecture`, PR #155)
- Started: 2026-10-29 · Last update: 2026-10-29

## Approach
Fill `docs/sdd/SDD.md` §6: principles, test levels (unit, integration, contract, Windows, system, acceptance, manual, non-functional), environments, apps under test, entry/exit criteria and gates, evaluation design per RQ1–RQ5, shared experiment rules. Uses the RS §4 method codes (T/D/I/A) instead of repeating per-requirement verification; complements galip's AI-7 (what the design provides) with how experiments run. Gates are copied from the gate issues' criteria (#28, #56, #70, #88).

## Decisions (small, local to this task)
- 2026-10-29 — Stacked on #45's branch, because `SDD.md` exists only there; PR merges after #155.
- 2026-10-29 — Proposed in the doc, flagged in SDD §9: RQ1 "identified uniquely from its descriptor", RQ2 flaky definition, exact McNemar below 25 discordant pairs. Owners (hasan, galip) asked through their inboxes and the PR.

## Status
- [x] §6 drafted, open issues 8–12 added to §9, document history 0.2
- [x] PR #157 opened 2026-10-29 (`Closes #48`, base `omer/45-sdd-architecture`), reviewers galip and hasan
- [x] Reviewed: hasan and galip approved 2026-10-29
- [x] 2026-10-31: #155's branch merged in; reviews applied. hasan: RQ1 = stable vs positional identification over the `uia_dump.py stats` interactive set, per app only; RQ2 per-step comparison, reset between runs, detection limit, load recorded; RQ5 paired on the run's verdict; 125 % scaling; pilots from #159; `localhost` caveat. galip: RQ3 paired per gold step + pair-level exact match + dependence threat; RQ4 ambiguous = miss. My call on §9 #11: exact McNemar everywhere (simpler, galip's suggestion)
- Next step: after #155 merges, switch #157's base to `main` (if GitHub has not).

## Manual checks
- none (text only; no diagrams added)

## Open issues
- hasan inactive since 2026-10-26: his confirmation of the RQ1/RQ2 definitions may come late; the doc marks them proposed.

## Handoff
- PR base: GitHub would show #155's diff too if based on `main`; basing on `omer/45-sdd-architecture` keeps the diff small but the base must be switched to `main` after #155 merges (GitHub does this automatically when the base branch is deleted on merge; otherwise do it by hand).

## Outcome (fill when the issue closes)
