# Active — Hasan Berk Yanıkkaya (`hasan`)

Only hasan's agent edits this file. Overwrite it at every session end.

- Last update: 2026-10-29
- Current issue: #6 — UIA tree dump spike on the candidate pilot apps (handover from galip)
- Branch: `hasan/6-uia-dumps` (3 commits + this one; **not pushed yet**)
- Next step: remove the `needs-windows-test` label from #6 and open the PR with `Closes #6`,
  requesting galip's review (he owns the spike's first half, PR #119).
- State: done except the PR. All four dumps are committed, `keepassxc.json` was re-taken on the
  entry form on 2026-10-29 (the 10-27 one had caught the unlock screen), and
  `eval/spikes/uia-dump.md` carries Results, nine Findings, the verdicts on the pre-run
  expectations and the pilot recommendation (**KeePass 2 + HandBrake**, KeePassXC third,
  Notepad++ only as the #23 fixture). 26 unit tests green on Windows.
- Worth knowing: the retake overturned the "`LabeledBy` is never populated" finding — Qt sets it
  on form rows (5/41), on the row *container* rather than the editable control. Finding 6 and
  three `learnings.md` entries were corrected; it changes what #11 can rely on for labels.
- Open questions:
  - #9 / PR #116 was the previous focus and is still open awaiting a review; the last #2
    criterion ("all three members merged one test PR") waits on it. Ask omer whether #9's PR
    counts for #2.
  - Inbox, oldest first: omer's #3 CI-skeleton review; omer's two #8 criteria that disagree
    between the issue and PR #121 (was the advisor summary sent? it is ticked in the issue but
    "hasan's action, still pending" in the PR); #122 (`eval/` pyproject + ruff) is mine and omer
    waits on it for the CI job; galip's #13 step-schema v0 needs all three approvals; galip's
    #34 wants my confirmation on NFR-02/04/05 and on TBD-5/TBD-6.
  - 11 PRs are waiting for my review (#135, #138, #141–#146, #150, #151, #157) — mostly galip's.
  - A new issue is worth opening from #6: measure UIA read cost per property on WinForms vs WPF
    (KeePass 2 took 278.5 s for 106 elements against HandBrake's 1.97 s for 149); NFR-02's 2 s
    snapshot target for #12 cannot be designed on the WPF number alone.
