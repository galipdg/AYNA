# #53 SDD final and submission (7 Dec)

- Issue: https://github.com/galipdg/AYNA/issues/53
- Owner: omer · Branch: `omer/53-sdd-final` (first PR; the issue stays open, `Part of #53`)
- Started: 2026-11-05 · Last update: 2026-11-07

## Approach
Assemble `docs/sdd/SDD.md` in steps. First PR: §5 moved in from `SDD-ai.md` (headings AI-n → 5.n), §7 written from the ADR index, stale status rows fixed. Second step, after the final RS (#41, 23 Nov): §8 Traceability, reference numbers, PDF in `docs/sdd/`.

## Decisions (small, local to this task)
- 2026-11-05 — §5 is one block, by a script, so the only changes are heading level and number, AI-n references and the `---` rules between sections. The file's front matter (editor note, status table, labels) is not moved: §1.6 has the labels, §7 the ADRs.
- 2026-11-05 — Accepted ADRs keep their `SDD AI-n` wording: they are never edited, and the same goes for journals, closed inbox items and old task notes, which are history.
- 2026-11-05 — The `User` row stays in this PR (omer's OK): the conflict with #193 is one row, and leaving it would make §3.3 say Planned while §2.4.2 says Built.
- 2026-11-05 — `active.md` stays untouched on this branch: #186–#193 all edit it, so a change here would add a real conflict (it has no union merge). This note and `journal.md` carry the state.
- 2026-11-05 — Rows beyond the brief's list that #60, #11, #12, PR #173 and PR #174 made stale are fixed too (Client, Agent, Server and Database in §2.2, CI ↔ server in §2.4.2, Healing proposal in §3.4, the security paragraph in §6.2), so one document does not say both Built and Planned for the same issue.

## Status
- [x] §5 moved, headings and references renumbered; the reverse transform equals the original block
- [x] §7 written: 23 ADRs, same order and titles as the index (D1 added 2026-11-07, after #169 merged)
- [x] Status rows checked against the code and updated; version 0.3
- [x] References in files of others: request in galip's inbox (`docs/rs/RS.md:285`, `ai/API.md:196`, `ai/ayna_ai/validate.py:29`); hasan has none
- [x] `docs/sdd/SDD-ai.md` removed (omer's OK, 2026-11-05)
- [ ] First PR (`Part of #53`)
- [ ] After the final RS (#41, 23 Nov): §8 Traceability, one reference numbering (§1.5, §5.10, RS, `docs/literature.md`)
- [ ] PDF rendered with the diagrams, stored in `docs/sdd/`, submitted by 7 Dec
- [x] 2026-11-07, hasan's #194 review: the Client row and the deployment row say PR #154 is still open and its Windows check pending (it read as Built); #63 added to the Agent row's Planned list; the §7 note on Proposed ADRs no longer counts them, so it does not go stale when #150 flips *Step schema v0*
- Next step: merge #194; when #182, #190 and #193 merge, §7 needs rows for their ADRs (*Client UI language*, *Runs API and live updates*, *Graph schema v0.4*) and the status rows of #15/#24/#25/#30/#38/#44 need updating; then §8 and the reference numbers after the final RS (#41).

## Manual checks
- 2026-11-05 · agent · Mermaid 11.17.2 parser under jsdom on `SDD.md`: 10 blocks, 0 failed; 24 fence lines; `marked` GFM: 69 headings, no level skip, no duplicate text, 31 tables, no row with a wrong cell count · pass · evidence: this note (scratch script, not in the repo)
- pending · omer · open `docs/sdd/SDD.md` on GitHub after the push and look at the diagrams; the check above parses them but does not draw them.

## Open issues
- **`User` row and PR #193.** #193 inserts its new row directly below the `User` row of §3.3, so editing that row conflicts on `SDD.md` when the second PR merges (tested with `git merge-tree`; without that commit the merge is clean). Keep both rows when resolving. Every other line of this PR merges cleanly with #193.
- **Proposed ADRs.** *Accounts…*: PR #179 has the two approvals its status line asks for, so the ADR, the index and `docs/graph-model.md:8` can move to Accepted. *Step schema v0* (PR #134) and *Healing proposal schema 0.2* (PR #174) ask for three approvals, and GitHub shows only omer's. The team should settle these before the G1 freeze (#52); §7 then changes with the index.
- §2.4.2 `Server ↔ AI service` says "No authentication", but `ai/API.md` needs `AYNA_AI_TOKEN` as soon as the service listens off loopback, which the Compose setup of #82 does. Fix with #82 or the next SDD pass.
- §9 row 7 points at #31, which is closed, while `HealthController` still calls `verifyConnectivity()` with no bound. It needs a new issue or a "won't fix" note.
- §3.2 and §4.1 still say graph model v0 although migrations reach v0.2 (`V0003`), and the §3.2 diagram has no `User`. Update after #193 merges, because #193 edits that diagram.
- §5 is unchanged on purpose, so its own statuses are as galip last left them; `§5.9` rows 7, 8, 9 and §5.5.3 are out of date (inbox request sent).
- Inbox: galip's 2026-10-27 "where does the block go" item is answered. Delete it after #126, #150, #169, #170 merge; those PRs touch `people/omer/inbox.md`, and union merges bring deleted lines back (learnings 2026-10-27).

## Handoff
- PR text: shared notes folder of the #53 session group, `53-pr-body.md`.
- SSH to GitHub times out; push over HTTPS with `gh auth git-credential` (learnings 2026-10-26).
- Keep the issue open: the PR says `Part of #53`, not `Closes`.

## Outcome (fill when the issue closes)
