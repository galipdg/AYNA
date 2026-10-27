# #19 Requirements workshop with the advisor

- Issue: https://github.com/galipdg/AYNA/issues/19
- Owner: galip · Branch: `galip/19-requirements-workshop`
- Started: 2026-10-27 · Last update: 2026-10-27

## Approach
The workshop itself is a human step: the advisor meeting on Tuesday 27 Oct 2026. The agent writes the pre-read and working notes, `docs/requirements-workshop.md`. It has roles, use cases, constraints, out-of-scope items and questions, all with stable IDs, plus an empty "Advisor's answers" section. Galip takes it to the meeting, records the answers and agreed changes in §7, and then ticks the second criterion. Every item comes from the project plan, `memory-bank/project/brief.md`, the ADRs or existing issues. Nothing is new scope.

## Decisions (small, local to this task)
- 2026-10-27: The doc is written in English, like the rest of the repo. The meeting may be held in Turkish; only §7 records its outcome.
- 2026-10-27: Stable IDs (`ROLE-n`, `UC-nn`, `CON-nn`, `OOS-nn`, `Qn`). A dropped item is marked *withdrawn* and its ID is never reused, so #27, #34 and #35 can trace to these IDs.
- 2026-10-27: Five roles. ROLE-1 to ROLE-3 (author, engineer, healing reviewer) are responsibilities that all map to the `tester` account role of #60. ROLE-4 maps to `admin`. ROLE-5 is the CI pipeline. Reason: #60 defines only admin and tester. Whether approvals need their own permission is left to the advisor (Q1).
- 2026-10-27: 16 use cases (the issue asks for at least 10). Each traces to a plan feature (Core 1–5, C1–C3), an RQ, an ADR and its issues. Measurement work (RQ1–RQ5) is not a product use case; the doc notes which use cases each measurement relies on.
- 2026-10-27: Prio is taken from the plan's fixed cut order. M means not in the cut order; S1 to S4 give the position in it. No priority was invented.
- 2026-10-27: CON-01 (closed network) cites the brief and the architecture, not an ADR, because no closed-network ADR exists. It is a project premise rather than a design decision, so the task does not add an ADR.
- 2026-10-27: The out-of-scope list is the plan's "Out of scope (or later)", plus the semester-2 items from the plan and ADRs: checkpoints from the Spy, the decision layer and unexpected-window handling. "Not a full TestComplete clone" from the plan summary is also included.
- 2026-10-27: `docs/requirements-workshop.md` is in hasan's `docs/` area, but the issue names this path and #19 moved to galip (ADR windows-work-to-hasan). Editing it is in scope, and hasan reviews the PR.

## Status
- [x] Branch, task note, board set to In progress
- [x] `docs/requirements-workshop.md` drafted: 5 roles, 16 use cases, 8 constraints, 12 out-of-scope items, 8 questions
- [x] PR #138 opened with omer and hasan as reviewers. Do not merge before §7 is filled in
- [ ] Advisor meeting held; §7 filled in; status line changed to "Agreed with the advisor on <date>"; second criterion ticked
- Next step: galip goes through the doc with the advisor (manual check below), fills §7 and applies the agreed changes on this branch.

## Manual checks
- Pending · galip · the meeting itself, as below.
  - **Setup.** Open `docs/requirements-workshop.md` from the PR branch (or print it) before the Tuesday meeting.
  - **Steps.**
    1. Go through §2 roles. Expected: the advisor agrees or names changes.
    2. Go through §3 use cases and the Prio column. Expected: agreement on the list, or added, changed or withdrawn UCs.
    3. Go through §4 constraints. Expected: explicit agreement.
    4. Go through §5 out of scope. Expected: explicit agreement.
    5. Ask Q1 to Q8 in §6. Expected: an answer or a follow-up for each.
  - **Report back.** Fill §7: date, people present, agreed/changed per section, the answer table. Apply the changes to §2–§5, keeping IDs stable. Change the status line. Tick the second acceptance criterion in the issue and the PR. Then ask for re-review and merge.

## Open issues
- `docs/working-agreement.md` §1 (#8, hasan) and `docs/README.md` still show the ownership from before ADR windows-work-to-hasan. For example, they list galip as owner of `recognition/` and hasan as owner of all of `docs/`. Noted in hasan's inbox.
- #21 and #80 name `docs/adr/ADR-00x-*.md` as their output, but ADRs live in `memory-bank/decisions/`. Fix the issue bodies when those issues start. #80 is galip's; #21 is the team's.

## Handoff
- §6 Q5 proposes NFR figures that the issues already set: Spy pick under 300 ms (#22), snapshot under 2 s (#12). #34 needs the advisor's answer about concurrent clients.
- The RS outline (#27) should keep the `UC-nn` IDs, and each FR in #34 should name the UC it comes from.

## Outcome (fill when the issue closes)
