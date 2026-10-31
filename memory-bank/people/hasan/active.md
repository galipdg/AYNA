# Active — Hasan Berk Yanıkkaya (`hasan`)

Only hasan's agent edits this file. Overwrite it at every session end.

- Last update: 2026-10-31
- Current issue: #21 — D1 sample-app technology and pilot apps. ADR written
  (`memory-bank/decisions/2026-10-31-pilot-apps-and-sample-app-technology.md`, Proposed) on
  branch `hasan/21-pilot-apps-adr`; needs a PR and galip's + omer's approval.
- Done this session: #6 closed (PR #159 merged); reviewed and approved PR #167 (omer, eval
  pyproject + CI) and PR #166 (galip, healing DPI).
- Next step: open the PR for #21 (`Closes #21`), request galip and omer, ask them in the body to
  answer acceptance criterion 2 (pilot apps "installed on every member's machine" cannot hold —
  macOS members; proposed rewording is in `tasks/21-pilot-apps-decision.md`, Open issues). Flip
  the ADR to Accepted in the same PR once both approve.
- Then, in order: #161 (root-cause the 278.5 s WinForms walk — it bounds #12 and NFR-02, and it
  is the one result that can reopen the D1 ADR), then #11 → #12.
- Small follow-up branch waiting (not started): fix the pre-ADR ownership tables in
  `docs/working-agreement.md` §1 and `docs/README.md` (galip's #19 note), and the
  `requirements.txt` mentions in `tasks/8-*.md` / `tasks/9-*.md` (omer's #122 note).
- Open questions:
  - Criterion 2 of #21 (above) — needs the team.
  - The #21 issue names `docs/adr/ADR-001-pilot-apps.md` as its output; the ADR went to
    `memory-bank/decisions/` per the memory-structure ADR. The issue text should be corrected.
  - Galip asked for a fallback in the healing scorer when only one side has `dpi` (my #166
    review); omer needs `dpi` in the graph model before #25 persists elements. Both are in their
    inboxes on this branch.
- Inbox: every item up to 2026-10-29 is handled, plus omer's 2026-10-31 note on #122 (PR #167
  reviewed). Do not delete them yet — PRs #167, #166, #157, #150 and #126 all add lines to that
  file and `merge=union` would bring the deleted ones back. Trim once those have merged.
- Waiting on: galip + omer to approve the #21 ADR; omer to merge PR #167 (approved) so #122
  closes; galip to decide on the one-sided `dpi` fallback.
