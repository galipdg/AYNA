# Active — Hasan Berk Yanıkkaya (`hasan`)

Only hasan's agent edits this file. Overwrite it at every session end.

- Last update: 2026-10-31 (long session; four PRs opened, four reviews given)
- Current issue: none in progress. Everything started this session is in review.
- My open PRs, newest first:
  - **#172** `hasan/inbox-17` — the #17 Windows-check failure in omer's inbox (`Refs #17`)
  - **#171** `hasan/10-literature-entries` — my five annotations, **based on
    `omer/10-literature-review`**, so it merges into #126, not into `main`
  - **#170** `hasan/161-winforms-walk` — `Closes #161`, review requested from galip
  - **#169** `hasan/21-pilot-apps-adr` — `Closes #21`, D1 ADR **Proposed**; flip it to
    Accepted in the same PR once galip and omer approve
- Next step: answer the reviews on #169 and #170. Then **#11 (element descriptor v0)**, which
  now has everything it needs: the D1 decision (#169), the #161 budget, galip's
  camelCase / `nearestLabel` constraints, and ROBULA+'s argument (#10) for writing the
  property priority and a never-use list into the descriptor note.
- Open questions waiting on the team:
  - #21 criterion 2 ("pilot apps installed on every member's machine") cannot hold for two
    macOS members; the proposed rewording is in #169's body and in the task note.
  - #21's issue text names `docs/adr/ADR-001-pilot-apps.md`, which contradicts the
    memory-structure ADR. Fix the issue text once the team agrees.
  - galip: the one-sided `dpi` fallback in the healing scorer (my #166 review).
    omer: `dpi` has nowhere to live in `docs/graph-model.md` (#14 / #25).
- Not started, small and ready: the pre-ADR ownership tables in `docs/working-agreement.md`
  §1 and `docs/README.md` (galip's #19 note), and the `requirements.txt` mentions in
  `tasks/8-*.md` / `tasks/9-*.md` (omer's #122 note).
- `needs-windows-test` queue: nothing unrun. #17 keeps the label because its Windows unit
  test fails — result on the issue, root cause in omer's inbox via #172.
- Inbox: every item up to 2026-10-31 is handled. Do not delete them yet — PRs #166, #157,
  #150 and #126 still add lines to that file and `merge=union` would bring deleted ones back.
  Trim once those have merged.
- Environment for the next session: `agent/.venv` exists (`pip install -e ".[dev]"`,
  `ayna_agent.rpc` imports) and `client/node_modules` is installed, so the #17 check can be
  rerun without the long setup. KeePass 2's demo database is at
  `%USERPROFILE%\OneDrive\Belgeler\Database.kdbx`, password `ayna-demo`.

## Still open from the 2026-10-29 review session (not mine to close)

- **PR #150** — held by me on content: galip needs to fix two sentences in the step-schema
  v0.2 document (I posted the exact replacement text). It is a `schemas/` freeze document
  (#52), so it waits for him, not for me.
- **PR #138** is now empty (0 files) because #143 carried its content to `main`; it should be
  **closed, not merged**. Side effect: `docs/requirements-workshop.md` is on `main` with §7
  still the empty template, tracked by #19 — galip must fill it.
- **Two ADRs still say Proposed although their condition is met:**
  `2026-10-27-step-schema-v0` (my third approval given on #134) and
  `2026-10-29-graph-schema-application-links` (I approved on #156; needs galip's, then omer
  flips it).
- **Branch `hasan/2209a-application`**: created from `main`, no commits, not created by me.
  Still worth finding out whose it is before someone builds on it.
- **Proposed, needs an ADR:** replace the single `learnings.md` with a directory of dated
  one-fact files, so append-only memory stops causing the merge cascade (`learnings.md`,
  2026-10-29).
- **#9 / PR #116 merged** — ask omer whether it satisfies #2's last criterion ("all three
  members merged one test PR").

The binding sign-offs I gave in that session (NFR-02 scoped to the sample app, NFR-04/05,
TBD-5's third failure state, TBD-6, RQ1 refused as defined, the CLI exit codes 0/1/2,
camelCase at every contract boundary, `parentPath` from programmatic ControlType names) are
recorded in `memory-bank/people/hasan/journal.md` under 2026-10-29 and in the PRs themselves;
RS 0.6 folded them in (galip's 2026-10-29 inbox note).

