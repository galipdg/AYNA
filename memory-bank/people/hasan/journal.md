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

## 2026-11-01 (second session) — #12 window snapshot export

**Issue:** #12. **Branch:** `hasan/12-snapshot-export`. **PR #180**, `Closes #12`, CI 5/5 green.

**The one judgement call:** the handoff said "UIA backend first", but omer had asked on #12 twice
(31 Oct and again that morning) for the schema and one example, because #15, #24, #25 and the G0
demo (#28, 9 Nov) were blocked on the *shape*, not the code — with a "say by Monday" on it. I put
the contract in the first commit so it can be reviewed on its own, and the backend in the second.
Both landed the same day, so nothing was traded away.

**Delivered:** `schemas/snapshot.schema.json` 0.1 + a real example (rebuilt by the tests from the
#11 trial-app tree, so it cannot drift) + 39 named cases + ADR `2026-11-01-snapshot-schema-v0`
(Proposed); `recognition/snapshot.py` and `recognition/uia.py`, wired into `rpc.main()`; the
`snapshot` success example in `docs/agent-rpc.md`; `schemas/README.md` sections for the snapshot
and for the element descriptor (#11 never added one). 95 new tests, agent suite 280 green.

**Measured on this machine, not assumed:** trial app 14 elements in **28–32 ms** (criterion 1
wanted under 2 s); KeePass 2's main window **114 elements in 819 ms** against #161's 2.26 s for
the same window — the difference is the reader (12 properties, no pattern probes), not the
framework; and a Qt window whose GUI thread slept 40 s returned `-32002` after **2 251 ms** of a
2 000 ms budget, which is the proof the timer design was needed at all, since the *first* UIA read
blocked and no between-element check could have fired. #16 also answered end-to-end over JSON-RPC.

**Three real bugs found, two of them mine:**
1. `python -m ayna_agent.rpc` loads the module twice (`__main__` + `ayna_agent.rpc`), so the two
   copies had two different `UiaUnavailable` classes and a backend error came out as `-32603`
   instead of `-32001`. Only the subprocess CLI test could see it.
2. Wiring the backend into `main()` made the server refuse to start where UIA cannot run, which
   would have stopped galip and omer from running anything on macOS. `setup()` now records the
   reason, which is what `docs/agent-rpc.md` specified all along.
3. `Path.read_text(newline=...)` is Python 3.13 only; CI runs 3.11.9. Green locally, red in CI.
   **Only 3.13 exists on this machine, so nothing local can ever verify the 3.11 floor.**

**Raised, not fixed:** `minLength: 1` cannot express "not only whitespace", so both this schema and
`element.schema.json` promise something they do not enforce. Named as a *valid* case in the cases
file so the gap is visible, and put to the deciders in the ADR.

**Next step:** answer the #180 review, then chase **#169** — it still has no approval and it blocks
#170 (#161), which is the oldest thing stuck on my side.
