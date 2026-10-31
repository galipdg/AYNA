# #21 D1: sample-app technology and pilot apps

- Issue: https://github.com/galipdg/AYNA/issues/21
- Owner: hasan (team decision) · Branch: `hasan/21-pilot-apps-adr`
- Started: 2026-10-31 · Last update: 2026-10-31

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

## Status
- [x] Branch, task note, issue set to In progress on the AYNA Project
- [x] Evidence re-measured: `python eval/apps/trial/uia_dump.py` on Windows 11 (125 % scaling) —
      8/8 app-owned controls have a unique dotted AutomationId, exit 0
- [x] ADR written, index line added
- [ ] Acceptance criterion 2 ("pilot apps installed on every member's machine") — needs a team
      answer, see Open issues
- [ ] PR with `Closes #21`, review from galip and omer, ADR to Accepted
- Next step: open the PR, ask galip and omer to approve the ADR and to answer the criterion-2
  wording in the same thread.

## Manual checks
- 2026-10-31 · hasan · trial-app UIA dump re-run for the ADR evidence · pass · evidence: command
  output quoted in the ADR ("Why PySide6 survives the WPF exception")
- pending · KeePassXC auto-lock: can Settings → Security switch off "lock after inactivity" and
  "lock when the session is locked", and does the portable build keep it next to the exe? Needed
  only before KeePassXC is promoted to pilot 3 (not before D1 is accepted).

## Open issues
- **Acceptance criterion 2, "Pilot apps are installed on every member's machine", cannot be met
  as written.** KeePass 2, HandBrake and KeePassXC are Windows binaries; galip and omer work on
  macOS (ADR `2026-10-25-weekly-windows-test-session`). Proposed rewording: installed in
  `C:\ayna-pilots\` on every Windows machine used for verification — hasan's machine and the
  weekly-session machine — with the versions pinned in the ADR; macOS members work from the
  committed dumps. Needs the team's OK on the issue before the criterion is ticked.
- The issue's "Expected output" path (`docs/adr/ADR-001-pilot-apps.md`) contradicts the memory
  structure ADR; see Decisions above. Worth fixing in the issue text so the next decision issue
  does not repeat it.

## Handoff
The ADR's one reopening condition is #161: if the 278.5 s WinForms walk turns out to be inherent
to the WinForms UIA bridge rather than to the window state #6 captured, KeePass 2 as a pilot has
to be re-argued. Everything else in D1 is settled by the #6 tables.

## Outcome (fill when the issue closes)
