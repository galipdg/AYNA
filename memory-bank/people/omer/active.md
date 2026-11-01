# Active — Ömerfaruk Sarıbal (`omer`)

Only omer's agent edits this file. Overwrite it at every session end.

- Last update: 2026-11-01
- Current issue: **#24** (Object Spy) on `omer/24-object-spy` (stacked on `omer/17-agent-process-manager`, no PR yet). Window list, highlight overlay, Spy screen and pick hotkey done; hotkey manual check passed on macOS 2026-11-01. Tree waits for the snapshot schema (#12), element-under-cursor for #22; reminders posted on both 2026-11-01 (asked hasan to answer by 2 Nov). Task note: `tasks/24-object-spy.md`
- Next step:
  1. **#17 Windows failure** (hasan's run, inbox 2026-10-31 + issue comment): `agent.test.ts:160` fails on Windows and the "failed" message shows the last stderr INFO line, because a killed child has `signal === null` and a non-zero code there (`agent.ts` ≈239–245). Fix on `omer/17-agent-process-manager`, merge it into `omer/24-object-spy`, ask for a re-run at the Windows session.
  2. #24 property panel: `schemas/element.schema.json` (#11, merged 2026-10-31) defines the descriptor, so the panel can be built before #12; the tree still needs the snapshot schema.
- Other open work: #60 waits for #160 to merge, then a new PR to `main` (see the #60 branch's `active.md`, 2026-10-31); #31+#158 PR #160, #45 PR #155, #48 PR #157 approved, waiting for a merge; #122 PR #167 merged 2026-11-01 (check closed/Done); #10 draft PR #126.
- Inbox: new 2026-10-31 items (galip #149 proposal schema 0.2 review; hasan #17 result) not yet handled. Items up to 2026-10-29 handled; delete them once #150 has merged.
- Merge note: this file differs on #160, the #60 branch and this branch; whichever merges later conflicts here → keep the newest version.
- Open questions: project licence undecided; Leotta [4] PDF unread
- Network: SSH to github.com times out; fetch/push over HTTPS with `gh auth git-credential` (see `learnings.md`)
