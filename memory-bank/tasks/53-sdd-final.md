# #53 SDD final and submission (7 Dec)

- Issue: https://github.com/galipdg/AYNA/issues/53
- Owner: omer · Branch: `omer/53-sdd-final` (first PR, merged as #194), `omer/53-sdd-update` (second); the issue stays open, `Part of #53`
- Started: 2026-11-05 · Last update: 2026-11-08

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
- [x] §7 written: 24 ADRs, same order and titles as the index (D1 added 2026-11-07 after #169 merged; *Runs API and live run updates* added 2026-11-07 after #193 merged)
- [x] Status rows checked against the code and updated; version 0.3
- [x] References in files of others: request in galip's inbox (`docs/rs/RS.md:285`, `ai/API.md:196`, `ai/ayna_ai/validate.py:29`); hasan has none
- [x] `docs/sdd/SDD-ai.md` removed (omer's OK, 2026-11-05)
- [ ] First PR (`Part of #53`)
- [ ] After the final RS (#41, 23 Nov): §8 Traceability, one reference numbering (§1.5, §5.10, RS, `docs/literature.md`)
- [ ] PDF rendered with the diagrams, stored in `docs/sdd/`, submitted by 7 Dec
- [x] 2026-11-07, hasan's #194 review: the Client row and the deployment row say PR #154 is still open and its Windows check pending (it read as Built); #63 added to the Agent row's Planned list; the §7 note on Proposed ADRs no longer counts them, so it does not go stale when #150 flips *Step schema v0*
- [x] 2026-11-07, main merged with #193 (Auto-fix on #194): the `User` row conflict resolved by keeping both rows; the user on runs, the WebSocket handshake, the runs API and `V0004` marked Built in §2.2, §2.4.2, §3.3 and §4.2 (checked in `RunService`, `RunEvents`)
- [x] 2026-11-08, `omer/53-sdd-update` (v0.4): §7 rows for *Step schema v0.2*, *Client UI language*, *Graph schema v0.4*; *Step schema v0* Accepted; status rows of Client, Server, Database, test machine, Turkish search, graph changes, step schema, snapshot and repository APIs checked against the code and marked Built; `RepoObject.columns` → #221; RQ1 path `uia_tree_dump.py` (#199). §5 stale lines (limits 2 and 3, open issue 4) are galip's: asked in his inbox.
- [x] 2026-11-15, `omer/53-sdd-v05` (v0.5): status after #22, #23, #26, #29, #33, #46, #51, #52, #59, #68, #152, #221; contracts 1.0 in §4.1/§4.3/§6.2; §3.2 renamed "Graph model" with Application links and User/AuthToken in the diagram; §3.3 rows v0.5 and v0.6; §2.4.2 AI token (open issue closed); §2.3 load numbers; §7 rows *Run screenshots*, *Contracts v1*; §9 row 7 marked open (needs its own issue), row 8 settled, row 13 (FR-35 uncategorised failures). §5 untouched (galip's).
- [x] 2026-11-19, `omer/53-sdd-traceability` (v0.6): §8 written from RS 1.0 as on PR #267 (86 IDs: 40 FR, 46 NFR, each once; every § reference checked to exist by a scratch script); §9 row 13 settled (#251); Agent/CLI rows after #54, #66. The table maps to design sections only; issues and verification stay in the RS so they are not kept twice.
- [x] 2026-11-19: #267 merged; `main`'s RS is the one §8 was built from (86/86 hold). One reference numbering: RS §2.1's numbers (RS 1.0 TBD-11), SDD-only sources [44]–[52], one list in §1.5, §5.10 points there. Checked by script: every cited number is listed, every listed one is cited, and [14]–[42] name the same source as the RS.
- [x] 2026-11-19: `docs/sdd/build_pdf.py` (reuses `docs/rs/build_pdf.py`'s Chrome lookup, list fix, CSS); Mermaid 11.4.1 vendored in `docs/sdd/vendor/` (MIT; omer chose vendoring over mmdc/PNGs), inline in the page, so the build is offline. The build fails if a diagram does not parse (error SVG check; the string "Syntax error in text" is in Mermaid's own source, so it cannot be the check). Two diagram fixes found by it: a `;` in a sequence message ends the statement (also broken on GitHub), and a `Note over A,C` wider than its span was clipped. v0.6 builds to 33 pages, 10 diagrams, checked as page images. The PDF is not committed until the submitted version.
- Next step: final pass on status rows, version 1.0, build `SDD-1.0.pdf`, commit it, submit by 7 Dec.

## Manual checks
- 2026-11-05 · agent · Mermaid 11.17.2 parser under jsdom on `SDD.md`: 10 blocks, 0 failed; 24 fence lines; `marked` GFM: 69 headings, no level skip, no duplicate text, 31 tables, no row with a wrong cell count · pass · evidence: this note (scratch script, not in the repo)
- pending · omer · open `docs/sdd/SDD.md` on GitHub after the push and look at the diagrams; the check above parses them but does not draw them.

## Open issues
- **Proposed ADRs.** *Accounts…*: PR #179 has the two approvals its status line asks for, so the ADR, the index and `docs/graph-model.md:8` can move to Accepted. *Step schema v0* (PR #134) and *Healing proposal schema 0.2* (PR #174) ask for three approvals, and GitHub shows only omer's. *Runs API and live run updates* (PR #193) has hasan's approval and waits for galip's. The team should settle these before the G1 freeze (#52); §7 then changes with the index.
- ~~§2.4.2 `Server ↔ AI service` says "No authentication"~~ (fixed in v0.5), but `ai/API.md` needs `AYNA_AI_TOKEN` as soon as the service listens off loopback, which the Compose setup of #82 does. Fix with #82 or the next SDD pass.
- §9 row 7 points at #31, which is closed, while `HealthController` still calls `verifyConnectivity()` with no bound. It needs a new issue or a "won't fix" note.
- ~~§3.2 and §4.1 still say graph model v0~~ (fixed in v0.5) although `docs/graph-model.md` is at v0.3 (`V0004`), and the §3.2 diagram has no `User`. #193 has merged; #190 (*Graph schema v0.4*) may edit the same diagram, so do it after #190 or coordinate.
- §5 is unchanged on purpose, so its own statuses are as galip last left them; `§5.9` rows 7, 8, 9 and §5.5.3 are out of date (inbox request sent).
- Inbox: galip's 2026-10-27 "where does the block go" item is answered. Delete it after #126, #150, #169, #170 merge; those PRs touch `people/omer/inbox.md`, and union merges bring deleted lines back (learnings 2026-10-27).

## Handoff
- PR text: shared notes folder of the #53 session group, `53-pr-body.md`.
- SSH to GitHub times out; push over HTTPS with `gh auth git-credential` (learnings 2026-10-26).
- Keep the issue open: the PR says `Part of #53`, not `Closes`.

## Outcome (fill when the issue closes)
