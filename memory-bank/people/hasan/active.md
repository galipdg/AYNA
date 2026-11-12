# Active — Hasan Berk Yanıkkaya (`hasan`)

Only hasan's agent edits this file. Overwrite it at every session end.

- Last update: 2026-11-12 (#33 built and green in CI; inbox and review queue triaged)
- Current issue: **#33 is done** — PR #230, `Closes #33`, CI 5/5 green, waiting on two
  reviews. Nothing else in progress.

## The agreed order for the next sessions (user's decision, 2026-11-12)

1. **#22 / PR #227 — the display-scaling check, then the re-review.** The code half is
   already done and pushed: omer's `CHANGES_REQUESTED` (identity, not geometry, must decide
   the element under a point) is fixed in `142a6c6` and answered in a PR comment on
   2026-11-12. GitHub still shows the old decision because he has not looked again.
   **What is left for me is criterion 3**, which only a person at this machine can do: run
   `agent/tests/test_uia_element_from_point.py` at **100 %** and at **150 %** display
   scaling (this machine sits at 125 %). The exact steps are in
   `memory-bank/tasks/22-element-from-point.md` under "Manual checks"; expect 19 passed at
   both scalings. Then set the scale back to 125 %, tick the criterion and ask omer for the
   re-review. If #224 merges before #227, also add `$defs/elementFromPointRequest` /
   `elementFromPointResult` to the contract as 1.1 (his answer: whoever merges second adds
   them).
2. **#221 / PR #228 — omer's Windows check.** `needs-windows-test`, 7 steps, posted as a
   comment on #221 on 2026-11-10: capture KeePass 2 and `GridProbeWindow` with the Spy and
   confirm the editor's column dropdown offers the real header names (Title, User Name, …
   and Ad, Soyad, Şehir) and **not** the row headers `1`, `2`, `3`. Needs the backend, the
   client, KeePass 2 (`python eval/spikes/kp_state.py main`) and
   `python eval/spikes/grid_probe_app.py`. Report pass/fail per step as an issue comment and
   remove the label on a pass. My own part of #221 is already answered (the headers are in
   every ControlView snapshot, so no schema change is needed).
3. **#29 — recognition measurement harness (RQ1), Week 4.** Due the same week as #33 and it
   builds on the sample app that just landed.

## Also waiting on me, outside that order

- **#162 is overdue** (Week 3, 3–9 Nov): local-model latency on Windows, because every
  number we have comes from one M2 Mac. Worth asking the user whether it goes before #29.
- **#10, my five literature entries** (omer's inbox note of 2026-11-05). PR #126 is still a
  draft.
- **#28 (G0 gate) is still open** with three of four criteria ticked; the last one is
  galip's #7.
- Inbox: of its 29 entries only two are still live (#10's entries and #221's run). The rest
  are handled — #6, #8 and #161 are closed, #17 (PR #154), #51's PR and #122 are merged, and
  the dozen October "please review" asks were approved on 2026-11-07. **Offered to delete
  the handled ones; the user has not said yes, so they stay.**

## My open PRs

1. **#227** (`hasan/22-element-from-point`, `Closes #22`) — CI 5/5 green, `MERGEABLE`,
   decision still `CHANGES_REQUESTED` until omer re-reads it. See item 1 above.
2. **#230** (`hasan/33-sample-app`, `Closes #33`) — CI 5/5 green (run 43262203133: the
   `eval` job ran 69 tests on the Windows runner), `REVIEW_REQUIRED` from galip and omer.
   Its first CI run failed on the `app.py` name clash with the trial app, fixed by renaming
   the entry point to `sample_app.py`. Two things in it are not mine to decide: for galip,
   `texts.py` and `uia_check.py --json` are what `eval/nl/objects/sample.json` (#36) should
   be generated from; and **UI Automation cannot choose an item in a Qt combo box**
   (`SelectionItem.Select`, `Invoke`, `ValuePattern.SetValue` all leave it unchanged; the
   items exist only after `ExpandCollapse`), which SC-20 needs — an open question for #40.
   Its last acceptance criterion needs galip and omer to run
   `python eval/apps/sample/sample_app.py` once on macOS; asked for in the PR body.
- **#170, #200 and #201 are merged** (2026-11-07/08), so #161, #26 and the coordinate fixes
  are on `main`.

**Review queue: empty.** No open PR requests my review (`gh pr list --search
"review-requested:@me"` is `[]`); #229, #228 and #224 ask galip, and #126 has no reviewer.

## Rules this week cost me something

- **Reproduce CI before pushing anything under `eval/`:** `cd eval;
  ../.venv/Scripts/python.exe -m pytest -q` (69 passed). CI runs that, not `pytest eval`
  from the root, and the two disagree about which module wins when a name exists twice.
- Three gotchas went into `learnings.md` on 2026-11-12: a Qt environment variable set in a
  pytest process poisons every app the run starts afterwards (12:40 of timeouts); the #199
  one-module-name-per-tree trap bit again and has no exception for scripts; and the combo-box
  finding above.
- `.codex/` sits untracked in my working tree (another CLI's hooks, my user's). Deliberately
  not committed and not ignored.
