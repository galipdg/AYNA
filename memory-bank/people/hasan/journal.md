# Journal — Hasan Berk Yanıkkaya (`hasan`)

Append-only. One entry per session, newest at the bottom:
`## YYYY-MM-DD · #<issue>` then 2–5 bullets: what changed, decisions, next step.

## 2026-10-25 — #9 one-screen PySide6 trial app
- Picked #9 over #8/#10: no dependencies, finishable alone, and it unblocks
  #21 → #33 → #46/#47 → the RQ measurements. #8 and #10 both need all three members.
- Scaffolded the first Python module in the repo: `.venv` plus a local
  `eval/apps/trial/requirements.txt` (user's choice; a repo-wide `pyproject.toml`
  stays open as a devops/ADR question).
- Built `app.py`, `uia_dump.py`, 12 tests and a README. All three acceptance
  criteria verified on this Windows machine; 12/12 tests pass.
- Four non-obvious findings cost most of the session and are now in `learnings.md`:
  the venv launcher owning a child process (which made `pywinauto.Application.start()`
  hang), the dotted AutomationId, `accessibleName` replacing the UIA Name, and the
  window frame's id-less buttons. Told galip via his inbox; commented on #9.
- Commits 5e23d15, 350071c; PR #116.
- Next step: review and merge PR #116, then confirm with omer that it covers #2.

## 2026-10-29 — review queue (#135, #138, #141–#146, #150, #151, #157)
- Cleared the whole queue: 11 PRs reviewed, 6 approved (#141, #142, #144, #145, #146, #151),
  5 left as comments with concrete asks (#135, #138, #143, #150, #157). Nothing waits on me.
- Reviewed by measuring, not by reading: a Qt `QTableWidget`/`QListWidget` probe answered all
  four of galip's #150 questions and found two schema defects (ValuePattern-first reads `''` on
  every Qt cell; `cell` is unsatisfiable on a list); the #141 scorer run showed a wrong Win32
  button scoring 0.800 and the score not being comparable across targets, so #73's threshold
  cannot be a constant; `eval/nl/objects/trial.json` verified live against the running trial app,
  which galip had marked unverified.
- Tested finding 7's own hypothesis and it failed: on KeePass 2, plain property reads cost
  2.79 ms/element and the ten pattern probes 1.56 ms, so the WinForms COM bridge is not the
  cause of the 278.5 s walk — it is tied to that window state. Corrected the finding in
  `eval/spikes/uia-dump.md` (PR #159 is still open) and posted the correction on #143 and #138,
  since I had overstated it in both reviews.
- Signed off NFR-02 (sample-app-scoped only), NFR-04, NFR-05, TBD-5 (plus a third "search ran out
  of budget" state), TBD-6 and RQ2; refused RQ1's definition as vacuous and proposed a two-number
  replacement. Committed the CLI runner's exit codes (0/1/2) and the camelCase contract rule.
- Next step: open the two issues promised in the reviews (the KeePass 2 hot spot; Ollama on
  Windows — every LLM number is from an M2 and the service's 30 s deadline already fires there),
  then #122.
- Followed through on both promises: opened **#161** (root-cause the 278.5 s WinForms walk, Week 2,
  blocks #12's snapshot budget) and **#162** (measure local-model latency on Windows, Week 3 —
  every number we have is from an M2 and the service's 30 s deadline already fires there), linked
  from the PRs where I promised them. Pushed `47d1e8b` to `hasan/6-uia-dumps` (PR #159).

## 2026-10-29 (second session) — review queue cleared and merged
- Reviewed 12 PRs: the 11 in my queue plus #163, and two late reviews on merged PRs whose ADRs
  were stuck unaccepted (#134, which merged without my review ever being requested, and #156,
  which merged with no reviews at all). Approved all but #150, which I hold on two schema
  defects I measured on a real Qt table.
- Helped merge eight of them (#141-#146, #135, #151): pushed `git merge origin/main` to nine of
  galip's branches to clear GitHub's union-driver conflict flag, re-synced after each merge —
  nine rounds, because every PR appended to the same inbox file (now in `learnings.md`) — and
  resolved three real conflicts, including `docs/agent-rpc.md`, where galip had meanwhile
  implemented my #135 concurrency point on `main` while #151 still carried the old wording.
- With the user's approval, flipped two ADRs to Accepted whose condition was met
  (`agent-rpc-v0`, `healing-proposal-transport`) rather than repeat #134's mistake of merging a
  binding decision labelled Proposed. Two more still need flipping by their owners.
- Found that #138 is now empty (#143 carried its content) and that its "fill §7 first" gate was
  bypassed, so the workshop document sits on `main` saying its own contents are not agreed yet.
- Next step: #161 (reproduce the #6 KeePass 2 state and bisect the 278.5 s walk), then #122.

## 2026-10-31 — #6 closed, two reviews, #21 D1 ADR
- Session started from a 95-commit-behind `main` and a stale `active.md`; #6's work was already
  finished on `hasan/6-uia-dumps`, so the first move was the user merging PR #159 (approved) —
  #6 is closed and the dumps are on `main`.
- Triaged the inbox: of 13 entries, 7 were already handled by last session's review round. Six
  live items left, the two urgent ones being review requests on my own area.
- Reviewed PR #167 (omer did my `eval/` half of #122) on this Windows machine instead of
  trusting CI: editable install resolves, ruff clean, `pytest eval/apps/trial/tests` 12 passed
  including the 5 UIA tests, spike `unittest` 24 OK. Two notes: the removed `noqa: E402` is
  unused only because E402 is outside ruff's default rules (`--select E4` reports 2 errors there),
  and CI covers neither ruff nor pytest for `spikes/` — which now holds the measurement tool
  #161 depends on.
- Reviewed PR #166 (galip's DIP fix). Found by measuring that a missing `dpi` on one side is
  worse than the old behaviour: an element against itself scores 0.33 location / 0.44 area.
  Asked for "if one side has dpi, use it for both". Also raised that `docs/graph-model.md` has
  nowhere to store the recording-time DPI → note in omer's inbox for #14/#25.
- Wrote the D1 ADR for #21. The decision turns on one thing: KeePassXC's 10 % id uniqueness is
  caused by unnamed widgets, not by Qt, and in our own app `objectName` is ours to set — the
  trial app, re-dumped today, gives 8/8 app-owned controls a unique dotted AutomationId. So
  PySide6 stays and the plan's WPF exception is not taken; pilots are KeePass 2 + HandBrake.
- Found that #21's criterion "pilot apps installed on every member's machine" cannot hold for
  two macOS members, and that the issue's expected ADR path contradicts the memory-structure
  ADR. Both are written up for the team instead of being quietly worked around.
- Next step: open the PR for #21, then #161 (the only result that can reopen this ADR).

## 2026-10-31 (second half) — #161, #17 Windows check, #10
- #161: the #6 outlier is explained. The documented window state walks in 1.79 s; the
  **modal message box** is what breaks it — 230 s for 85 elements, 2.71 s each against the
  dump's 2.63 s, with the median element still 1.4 ms and six containers absorbing 170 s.
  Refuted on the way: pattern probes, WinForms itself, CPU load, an open menu (a tracked
  menu still pumps). Cache API answered: no (0.6 %). PR #170.
- Built `eval/spikes/uia_probe.py` (six cost centres, per-element timings) and 21 tests for
  its pure parts. `kp_state.py` is committed unfinished on purpose: it drives KeePass's
  six-dialog wizard but has not completed it unattended, and the note and its docstring say
  so rather than pretending otherwise.
- #17 Windows check (omer's PR #154): 6 of 7 steps pass — both restart paths, no orphan
  process, clean shutdown in 1.2 s. `npm test` is 51/52: Windows has no signals, so Node
  reports a killed child as `signal === null` with a non-zero code, which makes the
  "killed" branch unreachable and leaks an INFO log line into the user-facing failure
  message. Result on the issue, root cause in omer's inbox (PR #172), label kept.
- #10: my five annotations ([5] ROBULA+, [6] contextual clues, [12] Luo, [8] Sikuli,
  [9] Alégroth) on a branch off omer's, PR #171. Two were read in full and three only as
  abstracts — each entry says which, because the whole point of "Source checked" is that
  the RS can trust it.
- Learned and worth repeating: when a desktop measurement is 100× out, suspect a modal
  dialog before suspecting the framework (`learnings.md`).
- Next step: answer reviews on #169/#170, then #11 with the D1 decision and the #161 budget
  in hand.
## 2026-10-31 (third part) — #11 element descriptor v0
- Wrote the descriptor as a `schemas/` contract plus a UIA-free model, so the rules could be
  tested on any OS and replayed over the #6 dumps. 53 new tests; agent suite 171 green.
- The label rule was decided by measurement rather than taste, and the first version was
  wrong: accepting a label *above* mislabels the trial app's check box and Login button with
  the password field's label 6 DIP above them. Dropping "above" and adding a 48 DIP ceiling
  reproduces UIA's own `LabeledBy` 7/7 on KeePassXC. Worth remembering as a method: when a
  heuristic has a ground truth hiding in the data (here `LabeledBy`), use it.
- Added `nearestLabelSource` so #43 can tell a changed label from a changed method — the
  problem galip raised in the #159 review.
- Found that `healing-proposal.schema.json`'s `scoredElement` refuses unknown keys and has no
  `dpi`, so a proposal carrying PR #166's `dpi` would be schema-invalid. Told galip.
- `jsonschema` went into agent's `[dev]` extras with the user's approval, so the contract is
  tested next to the component that produces it.
- PR #175. Next: #12, which emits these descriptors with the #161 budget.

## 2026-11-01 (second part) — reviewed #176 and #173
- Both were follow-ups to my own earlier reviews, so the job was to check the rules are
  usable rather than to re-argue them. Approved both.
- #176 (NL dataset §4.4 quoting, §6.8 check boxes): the rules are what I asked for, and the
  checker enforces the half a script can. Verified the 12 trial pairs are unaffected (all
  `origin: team`, and their only CheckBox steps are Verify, which §6.8 exempts). Raised: a
  team pair tagged `informal` cannot satisfy both §4.4 and "no apostrophes" unless the
  sentence is phrased so the value takes no suffix (galip's own test shows the pattern);
  and §6.8's start state is only true if #40/#69 reset the app between pairs — a Click
  leaves the box toggled and a check box survives a logout.
- #173 (loopback pinning, `stepLimitReached`): both answers yes. The pinning closes the
  check-then-resolve gap I meant in #142 §4, and `stepLimitReached` is the signal I asked
  for in §2.
- Running both suites on Windows paid for itself twice. `::1` passes the new loopback check
  and then dies at bind, because `ThreadingHTTPServer.address_family` is AF_INET — newly
  reachable through a name that resolves to `::1` only. And a closed loopback port times out
  here instead of being refused, which turns "Ollama is down" into a 504 `timeout` where
  macOS gives a 503 `server_error`; the client is told to retry on one and to disable the
  panel on the other. Recorded in `learnings.md`; it is the same trap for #16/#135 and #17.
- Next step: #170 waits on galip's re-review behind #169, then #12.
