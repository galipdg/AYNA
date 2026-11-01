# #21 D1: sample-app technology and pilot apps

- Issue: https://github.com/galipdg/AYNA/issues/21
- Owner: hasan (team decision) · Branch: `hasan/21-pilot-apps-adr`
- Started: 2026-10-31 · Last update: 2026-11-01

## Approach
D1 is a decision, not code: write the ADR from the measurements that already exist (#6 dumps of
four apps, #9 trial-app dump) and get all three members to approve it. No new measurement was
needed, except re-running `eval/apps/trial/uia_dump.py` on Windows to quote the sample app's own
AutomationId uniqueness as evidence for keeping PySide6.

## Decisions (small, local to this task)
- 2026-10-31 — The ADR goes to `memory-bank/decisions/2026-10-31-pilot-apps-and-sample-app-technology.md`,
  not to the `docs/adr/ADR-001-pilot-apps.md` named in the issue's "Expected output". Reason:
  ADR `2026-10-25-memory-bank-structure` put every ADR in `memory-bank/decisions/` with one line
  in its index, and 15 ADRs already live there; `docs/adr/` does not exist and is referenced by
  nothing. Raised on the issue so the plan's wording can be corrected instead of silently split.
- 2026-10-31 — Status `Proposed (#21)` until galip and omer approve, like the other team ADRs
  (#13, #39). The issue is closed by the PR; the status line flips to Accepted in the same PR
  once both approvals are in.
- 2026-10-31 — KeePassXC stays the *third* pilot, conditional on switching its auto-lock off
  (galip's lead from the #159 review), rather than being dropped or promoted now. Verifying it
  needs the app in front of a person, so it is a manual check, not a blocker for D1.
- 2026-11-01 — **P1 = HandBrake, P2 = KeePass 2** (galip's review point 3), decided from the
  dumps rather than from the order the pilots are listed in: SC-07 needs P2 to have a control
  with neither an AutomationId nor a Name, and only KeePass 2's is usable (the main toolbar's
  quick-search ComboBox, 160×28 px). HandBrake's two such controls are a zero-size Button and a
  menu item, which no scenario can act on.
- 2026-11-01 — **The version-drift role is removed from the ADR, not re-pointed.** galip's
  review point 2 was right that #22 is "element under cursor". Checked every open issue: there
  is no semester-1 issue that upgrades a pilot app. #46 and #47 are controlled-change and
  bug-injected versions of *our* sample app, and #42 and RQ4 (#76) run on those. KeePass 2's
  release history stays in the ADR only as a source of realistic change patterns for #46.
- 2026-11-01 — The #33 uniqueness test is **scoped, not dropped** (galip's review point 4): it
  excludes ListItem, DataItem and TreeItem, because Qt gives item-view children no `objectName`
  and they inherit their container's AutomationId. Verified in `keepassxc.json`: each of the
  four `QListWidget` ListItems carries its List parent's id. Keeping an unscoped test would
  have made #33 fail on its own results grid.

## Status
- [x] Branch, task note, issue set to In progress on the AYNA Project
- [x] Evidence re-measured: `python eval/apps/trial/uia_dump.py` on Windows 11 (125 % scaling) —
      8/8 app-owned controls have a unique dotted AutomationId, exit 0
- [x] ADR written, index line added
- [x] Acceptance criterion 2 reworded and ticked in the issue on 2026-11-01, with a dated `<sub>`
      note naming whose answer it was; see Open issues
- [x] PR #169 opened with `Closes #21`, CI 5/5 green (all five jobs reported on 2026-11-01)
- [x] Both reviews in (galip 2026-10-31, omer 2026-11-01): **both agree with the decision** and
      both answered yes to the criterion-2 rewording and to `memory-bank/decisions/`. Neither
      approved yet, deliberately — approval freezes the ADR, so they asked for galip's four
      points plus the nit and omer's one addition to be pushed first.
- [x] 2026-11-01 — all six review points addressed in the ADR, `origin/main` merged (the
      `decisions/README.md` conflict resolved by keeping main's five index lines and adding the
      D1 line; main's stray `<<<<<<< HEAD` was already gone, removed by #160)
- [x] Issue text: criterion 2 reworded and ticked, the `docs/adr/` path corrected (2026-11-01,
      with the user's OK)
- [x] 2026-11-01 — **ADR flipped to Accepted** in this PR, with the status line naming the
      evidence: both agreed with the decision in writing in their #169 reviews, on the one
      condition that their points were folded in, and they are (a488608, 004a741). What is
      still missing is only the Approve click, which branch protection needs to merge; the
      chase comment says so and offers to revert if either of them does not consider it decided.
      Written this way on purpose: an ADR that reaches `main` as `Proposed` with its condition
      met is the recurring failure here (step schema v0, #134, is still wrong on `main`).
- [ ] galip's and omer's Approve click on #169, then merge — **before** #170, which is stacked
      on it and carries `eval/spikes/uia-walk-cost.md`, which the ADR cites.
- Next step: wait for the two approvals on #169 (chased 2026-11-01), then merge #169, then #170.
  If either reviewer wants the ADR back at `Proposed`, revert the two-line flip, not the content.

## Manual checks
- 2026-10-31 · hasan · trial-app UIA dump re-run for the ADR evidence · pass · evidence: command
  output quoted in the ADR ("Why PySide6 survives the WPF exception")
- pending · KeePassXC auto-lock: can Settings → Security switch off "lock after inactivity" and
  "lock when the session is locked", and does the portable build keep it next to the exe? Needed
  only before KeePassXC is promoted to pilot 3 (not before D1 is accepted).

## Open issues
- **Settled 2026-11-01** (kept for the reasoning, which the next migrated issue will need):
  acceptance criterion 2, "Pilot apps are installed on every member's machine", could not be met
  as written. KeePass 2, HandBrake and KeePassXC are Windows binaries; galip and omer work on
  macOS (ADR `2026-10-25-weekly-windows-test-session`). Proposed rewording: installed in
  `C:\ayna-pilots\` on every Windows machine used for verification — hasan's machine and the
  weekly-session machine — with the versions pinned in the ADR; macOS members work from the
  committed dumps. Needs the team's OK on the issue before the criterion is ticked.
- **Settled 2026-11-01**: the issue's "Expected output" path (`docs/adr/ADR-001-pilot-apps.md`)
  contradicted the memory structure ADR and now names the real file. Both edits carry a dated
  `<sub>` note, so neither is a silent rewrite. The board text predates the memory-structure ADR,
  so **do this for every migrated issue whose wording predates an ADR** — it will come up again.

## Handoff
The ADR's one reopening condition was #161, and **it did not trigger**. #161 (PR #170) measured
the same two KeePass 2 windows at 114 elements in 1.86–2.26 s over six runs, about 18.5 ms per
element, and reproduced the 278.5 s outlier only with a **modal message box** open: 230.05 s for
85 elements, 2.71 s per element against the dump's 2.63 s. WinForms is not inherently unreadable,
so KeePass 2 stays a pilot and D1 is settled by the #6 tables. The ADR's #161 paragraph now says
this, and cites `eval/spikes/uia-walk-cost.md`, which reaches `main` with #170 — so #169 must
merge first and the citation must not become a dead link.

## Outcome (fill when the issue closes)
