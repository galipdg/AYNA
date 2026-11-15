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

## 2026-11-01 — #170 review answered: the measurement was wrong, so it was taken again
- Merged #172 and #175 (#11 closed, element descriptor on `main`). Found that a
  `copilot-swe-agent[bot]` merge had been pushed to my #161 branch and had left a literal
  `<<<<<<< HEAD` marker in `memory-bank/decisions/README.md`; removed it. Worth asking omer
  what that bot is doing on my branches.
- Galip's three #170 points all held, and the first one was not theoretical: this machine has
  a KeePass database of the user's own, and `--fresh` was pointing `taskkill /IM KeePass.exe`
  and an `os.remove` at the default `Documents\Database.kdbx`. Now: the pilot process is
  found by image path through a CIM query and killed by pid, the demo database is
  `C:\ayna-pilots\ayna-demo.kdbx`, and `--fresh` refuses any path outside the pilot folder.
- The deduplication point reached further than it looked. `uia_probe.run` counted KeePass's
  `Add Entry` twice (154 "elements" for a tree of 114), which inflated every total by ~26 %
  **and** flattered every per-element mean, because a second pass over an already-realised
  subtree is cheaper. So the honest fix was to re-measure, not to rescale: the full walk is
  18.5 ms per element, not 11.6 ms, and the gap to the #6 dump is ~140× per element *and*
  ~140× in total, instead of two numbers that disagreed. The #12 budget argument moved from
  "3× the measured walk" to "~330 elements at the descriptor rate".
- The driver script was the day's real lesson. Three honest failures before it worked
  unattended: `click_input()` leaves KeePass's secure boxes unfocused so the keystrokes
  vanish (KeePass then says the password is *empty* — the counter read "0 ch." after a click
  and "9 ch." after `set_focus()`); a classic message box blocks UIA against the whole
  process, so it has to be answered over Win32 `BM_CLICK`, while the new-database *task
  dialog* must not be, or the script loops; and `STEP_TIMEOUT` was budgeting one step rather
  than the sequence. A cold `--fresh` run now completes, in about six minutes, nearly all of
  it inside one blocked UIA call — the issue's own finding, measured from the driver's side.
- Next step: push, answer the review on #170, then #12.
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

## 2026-11-01 — #21 / PR #169: the D1 ADR review answers

- Issue #21 (PR #169). Both reviews were in when the session started: galip (2026-10-31) and
  omer (2026-11-01, during the previous session). Both **agree with the decision** and both
  commented instead of approving on purpose — approval freezes the ADR, so they wanted the
  corrections pushed first. So "chasing #169" turned out to be work, not a nudge.
- Addressed all six points in `2026-10-31-pilot-apps-and-sample-app-technology.md`, each
  verified against the committed #6 dumps rather than taken on trust:
  - **#161 paragraph rewritten.** The reopening condition did not trigger. Also corrected
    galip's own figure: his 154 elements in 1.79 s was the pre-deduplication run, the
    measured state is 114 elements in 1.86-2.26 s over six runs, and the modal-box
    reproduction (single root, so unaffected) stands at 230.05 s for 85 elements.
  - **Dropped `#22` instead of re-pointing it.** Checked every open issue: no semester-1 issue
    upgrades a pilot app, so the version-drift role had nowhere real to point. #46/#47 are
    versions of our own sample app, and #42 and RQ4 (#76) run on those.
  - **P1 = HandBrake, P2 = KeePass 2**, confirmed from `keepass2.json` / `handbrake.json`:
    KeePass 2's single interactive control with neither id nor Name is a usable 160x28 px
    ComboBox (the toolbar quick-search box); HandBrake's two are a zero-size Button and a
    menu item.
  - **#33's uniqueness test scoped** to exclude ListItem/DataItem/TreeItem: Qt gives
    item-view children no `objectName`, so each of KeePassXC's four `QListWidget` items
    carries its `List` parent's AutomationId exactly. An unscoped test would have failed on
    the sample app's own results grid.
  - The nit (Elements walked vs Interactive) and omer's client clause (#24/#44 see -32002,
    so "snapshot incomplete" is a UI state).
- Merged `origin/main` twice (it moved mid-session with #173). The `decisions/README.md`
  conflict resolved by keeping main's five index lines and adding the D1 line; main's stray
  `<<<<<<< HEAD` was already gone, removed by #160 as omer said. `active.md` took main's
  side. PR is now MERGEABLE and CI green on the jobs that reported.
- With the user's OK, edited issue #21 itself, since both reviewers answered yes: criterion 2
  reworded to the Windows-verification-machines form and **ticked**, and "Expected output"
  corrected to `memory-bank/decisions/`. Both carry a dated note naming whose decision it was.
  **All of #21's acceptance criteria are now met.**
- Next step: review omer's #179, which has been sitting in my queue; then the #169 approvals,
  flip the ADR to Accepted and merge #169 before #170.

## 2026-11-01 (fourth session) — #179 review, D1 accepted

- **Reviewed omer's PR #179 (#60, local accounts, roles, user management) and approved it**,
  including ADR `2026-10-31-accounts-and-tokens` (opaque Bearer tokens, SHA-256 hash in Neo4j,
  BCrypt passwords, 12 h sessions, never-expiring CI API tokens). I read the whole `auth/`
  package, `AuthIntegrationTest`, `V0003`, the who-did-it path in `TestService`, `SecurityConfig`
  against `openapi.yaml`, and the client's session handling; I did **not** run the suites (no
  Docker/Java here) and said so — CI was 5/5 green on that head. No way found for a tester to
  reach an admin endpoint and no path that leaks a token to the renderer, a log or disk.
- **What #179 settles for my #61 CLI runner**, so it is not re-derived: `Authorization: Bearer
  $AYNA_SERVER_TOKEN` on every call; an API token is a `kind: api` token on an ordinary tester
  account, never expires, revoked only by `DELETE /api/tokens/{id}`, and `POST /api/auth/logout`
  deliberately leaves it alone, so a CI run cannot log itself out. 401 = missing/unknown/revoked/
  expired, 403 = role refused, both RFC 9457; FR-23 maps either to exit 2, so the CLI need not
  tell them apart for the exit code. A password change ends sessions but not API tokens, so an
  admin rotating their own password does not break the nightly run. `/api/health` stays public.
  **The one contract point I added:** 401 and 403 must *not* be retried by the result-delivery
  backoff — a revoked token answers the same for the rest of the run — so retry only on
  unreachable/timeout/5xx, then `ayna-undelivered.jsonl` and exit 2.
- Three minor findings, none blocking: (1) `server/AGENTS.md` claims `AuthIntegrationTest` checks
  that `@PublicEndpoint` and `SecurityConfig` agree, but the test reads the *generated contract*,
  so it catches an annotation without a `permitAll()` and misses a `permitAll()` without the
  annotation — the direction that actually opens a hole; (2) after an admin changes their own
  password the renderer goes to login but the Electron main process keeps the dead token, so
  `currentUser()` still answers (self-corrects on the next 401; one-line fix is to fire
  `logout()` from `onSessionEnded`); (3) `FirstAdmin` throws from an `ApplicationRunner`, so a
  hand-made "no active admin but the name is taken" state stops the server from booting.
- **Flipped the D1 ADR to `Accepted`** (7dd2d64) and chased the approvals on #169. Both reviewers
  had written "I agree with the decision", each conditional on their points being folded in, and
  they are (a488608, 004a741) — so the status line names that evidence and the dates instead of
  claiming the click, and the chase comment offers a one-commit revert to `Proposed` if either of
  them disagrees. Reason for not leaving it at `Proposed`: step schema v0 (#134) reached `main`
  that way with its condition met and is still wrong there, and a dozen issues cite D1.
- Next step: the two Approve clicks on #169, then merge #169 **before** #170. Then #180's
  reviews, then #22 / #23.
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

## 2026-11-07 — review round: twelve PRs, and a KeePass 2 measurement

**No issue of my own.** The queue had grown to twelve PRs while #169/#180 were waiting to merge:
galip's #150 and omer's whole stack (#182 → #191, plus #192, #193, #194, #197). All twelve are
approved now, and two ADRs with them (client UI language, runs API).

**What I measured rather than reasoned about.** #150's ADR listed one check as "still to do at a
Windows session", so I did it instead of approving around it: KeePass 2's `m_lvEntries` through raw
UIA after `eval/spikes/kp_state.py main`. It is a UIA **List** with no Grid and no Table pattern —
which confirms galip's fallback paragraph — but his ADR says its ListItems have no cell children,
and they have **five `Text` children each, one per column, in header order**. The #6 dump missed
them because it was taken with the Add Entry dialog on top. That also settles the WinForms half of
the v0.2 cell-text rule: there is no ValuePattern at all on that control, so Value-first and
Name-first are indistinguishable on every WinForms control we actually have, and source [9] stays
docs-only until the sample app brings a real `DataGridView`. Full numbers in `learnings.md`.

**The find that matters most for the team.** #192 hard-codes `STEP_SCHEMA_VERSION = '0.1'` while
compiling the real `schemas/step.schema.json` with Ajv — and I had just given #150 (which makes that
const `'0.2'`) its third and last approval. Whichever merges second makes **every test save fail**,
in the client's own validator and on the server, with only a generic document-level message. It is
not a conflict git reports: neither side touches the other's file. Galip hit the identical bug in
`ai/` two weeks ago, so the fix and the precedent both existed.

**Three places where reading someone else's code found my own bug.** omer's Java `treeError`
enforces contiguous subtrees; my `snapshot.loads` only checks "the parent appeared earlier", so a
level-order document passes the agent and gets a 400 from the server. His test
`anElementOutsideItsParentsSubtreeIsRejected` is the one that caught it — the shared `cases.json`
working in the direction I did not expect. Also: his `NEVER_MATCH` has `nearestLabelSource` and my
`model.NEVER_MATCH` does not. Both are now in `active.md` as things to fix.

**Two gaps that only appear by tracing a decision through to its consequence.** (1) #187 rightly
lets an ambiguous Find-by set be saved, but FR-35 has no category for "more than one element
matched" — so I decided #40's rule: *element not found*, never pick the first (UIA child order is
not stable, and guessing would make RQ2 measure our own nondeterminism), and no healing, because
the answer is another property rather than another element. (2) #193's run statuses are four, so a
run stopped by a repair proposal (TBD-6, mine) can only finish as `aborted` — while omer's own
style guide lists `repairProposed` as a run status with the words "Needs review / İnceleme
bekliyor". RQ5 (#86) counts those runs; stored as `aborted` they are indistinguishable from a crash.

**The Turkish review was worth doing properly.** omer's `foldText` folds `İ`/`I`/`ı` — the subtle
half, and correct — but not `ş ğ ü ö ç`, so **step 2 of his own #184 Windows check cannot pass**:
"giris" does not find "Giriş". Ran the cases rather than reading them. Also: "Seç" in the editor is
ambiguous against galip's §4.1 NL vocabulary, where *seç* is Click for a tab and Select for a combo
box, and the English column already distinguishes them ("Choose item"); "Zaman aşımı" reintroduces
the jargon the English deliberately avoided ("Took too long"); and *Geçti / Kaldı* for passed/failed
is the best line in that glossary.

**Also found:** SDD §2.2 claims the agent process manager is Built when PR #154 is still open and
#17 still carries `needs-windows-test`; `Window.snapshotId` has no uniqueness constraint, which my
own #61 retry path would race into a state that breaks every later read of that snapshot; and
`docs/ui/` lands in my `docs/` area by the current `AGENTS.md`.

**Next step:** the Windows session queue — **#184 first** (it saves the elements #38's check uses),
then #38 and #17, plus #197's popover and resizer. Before that, or in the same branch: the four
follow-ups in `active.md` (pre-order fix in `loads`, `nearest_label_source`, the two probe scripts
under `eval/spikes/`, and the `docs/AGENTS.md` ownership question for the user).

## 2026-11-07 (continued) — #26 built, then the Windows session found two bugs of mine

**#26 is done** (PR #200). `playback/` with resolution, actions and the runner; `read_tree()` on
the UIA backend so a target is matched against the *same* derivation that produced the values the
repository stored. Both acceptance criteria measured, not argued: the 3-step login 10/10 on the
real trial app (each run resetting the status label first so it proves its own login), and "no
coordinates" as a property of the contract rather than of one document. 112 new tests.

**I avoided in my own code the bug I had just found in omer's #192**: the runner reads step schema
0.1 *and* 0.2 instead of pinning one version. Pinning is what would break the day #150 merges.

**Then the Windows session for #184, and it earned its keep.** Six of eight steps pass. Two of the
failures are omer's to decide (the Turkish fold; smoothness at 285 real elements versus his
synthetic 3031). But the session's real output was **two coordinate bugs of mine**, both invisible
on one display and in every unit test:

1. The agent had **never** been per-monitor-v2 DPI aware. A pointer-sized context handle truncated
   by ctypes, a call failing with error 87, my code treating 87 as "already set", and pywinauto's
   import quietly setting v1. The log line said "already set" for weeks about a call that had never
   worked. **A success log is not evidence** — read the state back when a contract depends on it.
2. `listWindows` reported `GetWindowRect`, which includes Windows 10's invisible resize border, so
   the Spy framed a window 8 px too wide. My user found this one by *looking*: the frame around
   every element was exact, the frame around a window was not. One window has three rectangles and
   we were reporting the wrong one; "bounds" is not one concept on Windows.

Both in PR #201. The second is the better argument for the weekly session existing: no test I would
have thought to write catches "the rectangle is subtly too big", and a person noticed in seconds.

**And the G0 chain ran end to end** (#28). The object my user picked in the Spy went to Neo4j, and
playback read its property sets *back from the graph* and played the login — "Welcome, admin!". I
ticked three of #28's four criteria; the last one is galip's #7. Two days before the gate, the
thing that had never been connected is connected.

**Three mistakes of my own worth remembering.** I told the user the display was at 100 % — I had
read it from a DPI-unaware process, which is the same class of mistake as bug 1 above. I predicted
"2 matches" for a search from the #11 fixture when the live window had 3, because a fixture is one
moment. And my own ad-hoc G0 script read the status label immediately after the click and saw the
*previous* state — exactly the trap #26's test already guards against, which is now twice-proven
and is the design point for #40's checkpoints.

**Next step:** #38 and #17 are still in the Windows queue and the environment is now proven
(`http://[::1]:8080`, seeded app/version/objects). Before that, #170 is one click from merging.

## 2026-11-07 (third part) — the Windows queue: #184 and #38 run with my user

**#184: six of eight pass. #38: twelve of fourteen.** Both results are issue comments; both labels
stay, for findings rather than for anything unverified.

**The best part was not a test result.** Twice my user found something by *looking* that no test I
would have written would catch:

- the Spy's red frame around a **window** sat outside the window while the frame around every
  **element** was exact — which turned out to be `listWindows` reporting `GetWindowRect`, invisible
  resize border included (PR #201);
- *"this element is no longer in the repository"* on a step whose element was right there — which
  turned out to be the editor reading the test once per `id` while refetching the element menu on
  every show, so it showed a pre-rename document and then blamed the data.

Both are the argument for the weekly session existing. Neither is a thing a unit test fails on.

**Two predictions I made from the code before my user looked, and both held:** `2,5` would come back
as `2.5` (`secondsText` is `String(ms / 1000)`, locale-fixed on the way out only), and `Login` in
the Spy's search would match 8 of 14 elements because every Qt id is a dotted path containing the
window's name. Reading the code first made the manual check sharper — "type this, expect exactly
this" instead of "have a look".

**And two things I got wrong and had to walk back.** I said the picker failing was silently
swallowed — it is not, omer renders `stepsElementsFailed` and I had read the file too fast. And I
implied a server bug when `GET …/versions` looked empty — that was my own shell loop eating the
output. Both corrected in the same breath; the lesson is to run the thing rather than skim it,
which is also what made the good findings good.

**My own setup mistake, worth remembering:** I switched the checkout to #38's branch but left the
server container built from #184's, so the element picker was empty because the endpoint did not
exist in the running image. `docker compose up --build` builds from the checked-out branch and
nothing ties the image to it. It will happen to someone at the demo.

**Also fixed, found the same way:** the agent had never been per-monitor-v2 DPI aware, and I had
read "100 % scaling" off a DPI-unaware process and told my user so — the same class of mistake as
the bug. The display was 125 % the whole time.

**Left behind:** the stack stopped but not deleted, with `AYNA Trial`, five repository objects and
two tests seeded, so #17 starts in seconds. `http://[::1]:8080`, not `localhost`.

**Next step:** #17 (omer's PR #154) is the last item in the Windows queue. Its happy path ran
incidentally all session — every client start launched the agent and every close logged
`stdin closed, shutting down` — so the check is presumably about crash and restart.

## 2026-11-12 (second session) — #29 built; #231 approved; #162 unblocked

- Asked the user about the overdue #162 vs #29 first, as they wanted. They chose to run both in
  parallel: pull the models in the background and build #29 meanwhile. **Both models are now on
  this machine** (`qwen3:8b`, `gemma4:e4b-it-qat`; Ollama 0.40.16 was already installed, which
  #162's body does not know), so #162's remaining work is machine time, not a download.
- **Reviewed and approved PR #231** (omer, run history + report window, #68) before starting new
  work. Answered his two questions as commitments: #61 does not want the app-wide run list and it
  must not be widened for it; and the failed-Verify message wording for #40 is now fixed, in
  `resolve.py`'s house style. Asked for one fix before merge — the report's temp files are
  deleted with a fire-and-forget `rm` in `will-quit`, so 15 MB pages carrying screenshots of the
  app under test can survive in `%TEMP%`.
- **#29: the harness and the labelling guide are committed** (`ae9ab25` on
  `hasan/29-rq1-measure`). `measure.py` has `capture` (Windows, drives the agent's own
  `UiaDesktop`) and `measure` (pure, reads committed snapshots). It imports `ayna_agent.model`
  and `playback.resolve` rather than copying them, so "recognised" is decided by the Spy's own
  proposal rule and playback's own comparison. `labelling.md` is the ground-truth procedure,
  which exists because an automated denominator hides a control the walk never found. 31 new
  tests, 43 eval tests pass, ruff clean.
- **None of #29's three acceptance criteria is met**: all three need the pilot apps measured
  here, and the user asked to run nothing on the machine this session. PR opened without
  `Closes #29` on purpose, to get the definition agreed before the numbers exist.
- Next step: with the machine idle, `kp_state.py main` → `capture keepass2 --screen main`,
  the same for `entry`, HandBrake `main-summary`, then `measure`. Then leave the machine alone
  for #162's idle batch.
## 2026-11-12 (late) — omer's #221 Windows check: 7 of 7 pass

- **Ran the whole check on `omer/221-grid-columns` (`c1534e3`) with the user driving the UI, and
  it passes.** Set up the backend from that branch, `npm ci`, KeePass 2 via
  `kp_state.py main`, the Qt probe, and HandBrake 1.11.2. Result posted as a comment on #221 and
  `needs-windows-test` removed.
- **Recorded it at the `columns` level, not only as "the dropdown looked right"**, because that
  field is what feeds the dropdown and it is checkable from the API: KeePass 2 `main.entryList`
  → `['Title','User Name','Password','URL','Notes']`; Qt `probe.customerGrid` →
  `['Ad','Soyad','Şehir']`; HandBrake `queue.jobs` → `[]`. Three UI frameworks, which is as much
  as this machine can offer.
- **Step 6 is the one that mattered and it held:** no `1`, `2`, `3` among the Qt columns, even
  though Qt publishes row and column headers as `Header` with the *same* `automationId` and the
  only separator is one pixel (row header ends at x=666, first cell starts at x=667).
- **Said plainly in the report that step 7 did not test what it hoped to.** HandBrake's queue is
  a `List` (`queueJobs`) with no `Header` child at all, not a WPF `DataGrid`, so it exercised the
  free-text fallback instead. The `DataGrid` branch is still unexercised and nothing in
  `C:\ayna-pilots\` has one. Better to leave that gap visible than to let a `List` stand in for
  it.
- **Checked two suspicions before reporting them and both were wrong**, which is the useful part:
  the mojibake in app names was my console's codepage (the server stores `ı` U+0131 and `Ş`
  U+015E correctly), and the "empty space" the user saw next to *Metni olan satır* is the row-text
  input with its hint. Neither became a false finding on a teammate's PR.
- **One real finding, mine not omer's:** `Invoke` on HandBrake's WPF toolbar button throws
  `COMError -2147220992` while a mouse click works — and on its update dialog the reverse was
  true. #40 cannot implement Click as a single call. In `learnings.md`.
- Two deviations from the step text worth fixing in it: the health check is on **8081** here
  (#208's `.env` escape, another program holds 8080) and the Qt window's *title* is
  `AYNA Grid Probe` while `GridProbeWindow` is only in the automation id.
- Next step: **#29** (RQ1 recognition harness, Week 4, due 16 Nov) unless #162 jumps the queue —
  it is overdue from Week 3 and by the earliest-milestone rule it should go first; worth one
  question to the user. My own #22/#33 are both finished and waiting only on reviews.
## 2026-11-10 — eight reviews, then #22 built

- **Reviewed and approved all eight PRs waiting on me** (omer's #217, #218, #219, #220, #222,
  #223, #224, #225), including the two ADRs `2026-11-08-run-screenshots-and-retention` and
  `2026-11-08-contracts-v1-freeze`. The queue had been empty on 2026-11-07 and refilled
  completely; it is empty again.
- Three of the reviews needed measurements rather than opinions, so I took them here:
  - **8 MB screenshot limit (#223):** a real 1920×1080 PNG is **222 KB**, the incompressible
    ceiling at that resolution is **7.92 MB**. So the limit is exactly one raw 1080p frame and has
    no headroom above that — which is fine only because I committed to #54 sending the *window*.
  - **`schema_compat.py` (#224):** ran omer's checker myself (28/28) and put six mutations
    through it against my own `snapshot.schema.json`. It proved that my planned whitespace
    `pattern` change is **0.1 → 1.0, not 0.2** — a correction to my own plan.
  - **`DEMO-windows.md` §5.3 (#218):** computed the four tree-search counts against the committed
    capture; `user` → 2, not the 3 the guide claims. Also checked that #219's leaf-id rule does
    not change any of them.
- Two findings I would not have had without reading my own code: **`-32002` has two causes** and
  the client throws the distinction away, so #219's retry ladder gives exactly the wrong advice
  when an application is blocked by a modal message box (opened **#226** for it); and **`cell`
  being grid-only while `rowExists {value, column}` is allowed on a list** is the same column
  mapping forbidden in one place and required in the other (raised on #220 and #221).
- Commented on **#221**: the column headers are already in every snapshot as `Header`/`HeaderItem`
  elements, so its heaviest acceptance criterion — a snapshot-schema ADR with three approvals —
  may be unnecessary, and `GetColumnHeaders` alone would miss KeePass 2.
- **Built #22** on `hasan/22-element-from-point`, three commits (backend, galip's `rpc.py`,
  the contract doc), 31 new tests, 432 agent tests green on real Windows. The design decision
  worth keeping is in `learnings.md`: a descriptor for one element is not the same thing as a
  descriptor from a walk, so `elementFromPoint` answers out of the last snapshot. Criteria 1 and 2
  met and measured (median 3.39 ms against 300 ms); criterion 3 is a manual scaling check, written
  up in the task note, because this display sits at 125 %.
- Also learned the hard way that a UIA hit test answers with what is **visible**: the first
  Windows run failed because pytest's own terminal was over the trial app.
- Next step: the scaling manual check with the user, then the PR with `Closes #22`.

## 2026-11-12 — #22's review answered, #228 and #229 reviewed, #33 started

- **Answered omer's changes-requested review on PR #227** (`142a6c6`). He was right and it was
  the dangerous case, not a rare one: `match_in_document` let a single same-bounds candidate win
  with no COM call, which only holds while a window keeps the same elements in the same
  rectangles. Every candidate now goes to `CompareElements`, and the deepest-candidate fallback
  is gated on `controlType` / `name` / `automationId`. The check is free: median 2.2 ms and
  2.5 ms over two runs of 50, against 3.39 ms *before* it. 436 agent tests pass here including
  the Windows ones. His real question — do the hit test and the walk agree on identity for real
  leaves — is answered yes: all 50 calls named an element, the fallback was never taken.
- Also fixed a flake I caused: `test_a_window_that_was_never_captured_has_no_snapshot_id` failed
  once with another window's handle, because the module fixture raises the trial window only at
  setup. Any Windows test about a point has to own the stacking order right before it points.
- **Ticked #22's criteria 1 and 2 on the issue** with the evidence in a comment, and posted
  criterion 3 (display scaling) as a manual check with `needs-windows-test` — it needs the user
  at the machine, and this display sits at 125 %.
- **Reviewed and approved omer's #228 (#221 grid columns).** Did not take the rule on trust: ran
  his `GridColumns.of` against real AYNA captures of the Qt probe app and KeePass 2. Both shapes
  hold, including the part he asked about (Qt's column headers really are `Header` children named
  with the column text, and the row header is excluded — by exactly one pixel).
- **Reviewed and approved omer's #229 (#59 HTML run report).** The finding worth having: the
  endpoint holds every screenshot and the whole HTML in memory, ~58 MB peak in English and ~90 MB
  in Turkish for his own NFR-09 case, because one `ı` in the Turkish title inflates a
  15-million-character `StringBuilder` to UTF-16. Offered the streaming fix. Answered his two
  questions: `category` (FR-35) must be in the step result before the freeze, and the CLI may
  save the report as an opt-in `--report`, fetched after the last screenshot upload.
- **Started #33** (sample app v1) on `hasan/33-sample-app` from `main`. Nothing built yet.
- Next step: read `docs/rs/scenarios.md` for the behaviour the reference scenarios assume of the
  sample app, write the task note, then build the screens.

## 2026-11-12 (late) — #22's scaling check: run, passed, criterion 3 ticked

- **Ran #22's last acceptance criterion with the user at the machine, and it passes at both
  scalings.** The user changed the scale in Windows Settings; I ran
  `pytest tests/test_uia_element_from_point.py -q` at each. **23 passed at 100 % and at 150 %**
  (and 23 at this machine's own 125 % as a baseline), with no skips, so the five
  `@pytest.mark.windows` tests really ran against the trial app each time. **The full agent suite
  passes at 150 % too: 436 passed in 13.65 s.**
- **Did not take "the tests pass" as proof the scaling changed.** A DPI-unaware process reports
  96 DPI whatever the scale is, and at 125 % it did exactly that, which would have "confirmed" a
  scaling nobody set. So I read the DPI from the product instead: `window dpi` 96 against 144,
  every element's `dpi` likewise, `dpi_awareness()` `per-monitor-v2` both times, and the trial
  login window 360 × 164 against 540 × 246 physical pixels — exactly 1.5×. Then four points taken
  at the centre of a rectangle the snapshot itself reported answered with the **same element id**
  at both scalings (`e4`, `e5`, `e6`, `e8`), which is the property `142a6c6`'s identity check
  needs. Gotcha written to `learnings.md`.
- **Ticked criterion 3 on #22**, posted the numbers as an issue comment, removed
  `needs-windows-test`, and asked omer again for the #227 re-review in a PR comment that says
  what `142a6c6` changed and what the Spy side needs from the reply shape. #227 is CI 5/5 green
  and `MERGEABLE`; **#224 is still open, so #227 carries no schema change today.**
- Also learnt, and it is worth money to the Windows queue: a scale change **needs no sign-out**,
  it applies to apps started afterwards — so #197's 100 % / 150 % pass can be batched with any
  other scaling work in one sitting. And `agent/.venv` has no PySide6: a script starting the
  trial app outside pytest must use the repository root `.venv`.
- Next step: **#22 and #33 are both waiting only on other people.** Start omer's **#221** Windows
  check (7 steps, comment on the issue of 2026-11-10: the editor's column dropdown must offer the
  real header names, not the row headers `1`, `2`, `3`), then **#29** (RQ1 recognition harness,
  Week 4). #162 is overdue and worth raising with the user first.
## 2026-11-12 — #33: the sample app finished, and three faults the first full test run found

The session before this one wrote the app — six screens, `model.py` without Qt, `texts.py`
for every string, `uia_check.py` as the acceptance check — and stopped before anything had
been run as a whole. So this session was mostly verification, and verification earned its
keep: **the first full `pytest` run errored in all 25 UIA tests, 12 minutes 40 of it pure
timeout, while every one of them passed alone.**

The cause was mine from two layers away. `test_screens.py` set `QT_QPA_PLATFORM=offscreen`
at import so the widget tests need no display; the UIA tests start the real app as a child
process, and a child inherits the environment, so the app came up with no window at all and
`wait("visible ready")` sat there for 30 s a time. The fix is to ask Qt for the platform in
its own argv (`QApplication(["pytest", "-platform", "offscreen"])`) and never touch the
environment — which also fixed the trial app's five UIA tests, broken the same way the
moment both apps were in one run.

Then `pytest eval` would not even collect: two `test_uia.py` and two `uia_dump.py` under
`eval/`. This is exactly #199 again, four days later, and I had written the learning myself.
Renamed to `uia_check.py` and `test_sample_uia.py`, and put the rule in `eval/AGENTS.md`
where the next person will actually meet it, not only in `learnings.md`.

The third fault was a real race in my own test: two `nextButton.click()` calls in a row sent
the second before Qt had shown page two, so the wizard stayed on page one and the summary
label genuinely was not in the tree. `until()` now treats `ElementNotFoundError` as "not
ready yet" and the test waits for each page by its label. The probe that found it is worth
remembering: dump the tree after the clicks with sleeps in between, and compare.

**Where #33 stands:** two of three criteria are measured, not argued — 44 interactive
controls over five screens, zero without an AutomationId, and the same checks run in
`test_sample_uia.py` so CI repeats them. `pytest eval` is 125 green in 39 s, ruff clean.
The README's id tables are generated from `uia_check.py --json`, so they cannot drift into
fiction.

**Next step:** criterion 3 ("runs with one command on every member's machine") is the only
one left and it is not mine to tick — galip and omer have to run
`python eval/apps/sample/sample_app.py` once on macOS. Asked for it in PR #230's body.

**And a fourth fault, which CI found after I had pushed.** I kept `app.py` under its own name
on the argument that it is only ever run, never imported — and wrote that reasoning into the
PR and the README. It is importable, so the argument was worthless: the trial app's
`from app import ...` resolved to *this* app's `app.py` in CI and broke two of its test
modules. What made it invisible here is the detail worth keeping: both apps' conftests insert
their own folder at `sys.path[0]`, so the conftest loaded **last** wins, and the order differs
between `pytest eval` from the repository root (alphabetical) and CI's bare `pytest` from
`eval/` (`testpaths` order). Renamed to `sample_app.py`, and from now on I reproduce CI's
invocation (`cd eval; pytest -q`) before pushing anything that adds a module under `eval/`.
The twice-stated rule now also says that a script is not exempt.

## 2026-11-12 (second part) — the inbox and the review queue, triaged against GitHub

My user asked what is still waiting on me. Answered from `gh`, not from the inbox, and that
was the right call: **the review queue is empty** (no open PR requests my review) and most of
the inbox's 29 entries are already handled — #6, #8 and #161 closed, #17's PR #154, #51's PR
and #122 merged, the dozen October "please review" asks approved on 2026-11-07. Two entries
are still live: my five #10 literature entries, and #221's Windows run.

**One correction I had to make to my own report.** I read PR #227's `CHANGES_REQUESTED` and
told my user the identity fix was the next task. It is already written and pushed — `142a6c6`,
with the answer to omer posted at 14:41 today — so what is actually left there is criterion 3,
the 100 % / 150 % display-scaling run, which needs a person at this machine. GitHub kept
showing the old decision because omer has not looked again, and I took the label for the state.
Lesson: on a PR of my own, read the branch's task note before believing the review decision.

**The order my user agreed to:** (1) #22's scaling check, then ask omer for the re-review;
(2) #221 / PR #228's Windows check, seven steps with KeePass 2 and `GridProbeWindow`; (3) #29,
the RQ1 harness, which the sample app that landed today is the input for. #162 is overdue from
Week 3 and sits outside that order — it needs a decision, not work.

## 2026-11-14 — third session · #29 (round-2 tooling) and #162 (measured)

- **#29**: built what a second independent labelling round actually needs and the procedure did
  not have — `measure.py sheet` writes a blank per-screen label file with **no** `matchCount`,
  `recognised` or `primary` column (a labeller who sees those labels the measurement, not the
  screen), `measure.py agree` compares two rounds (raw agreement, Cohen's kappa, the
  disagreement table), `measure --labels --round r2` reports the second round without
  overwriting the first, and `labelling.md` gained §8. Kappa is reported **undefined, not 1.0**,
  when both rounds use a single category — HandBrake's queue is six rows and all six are
  controls, so chance agreement is 1. 8 new tests (45 in rq1). `fdf05e9`, `c3a924e`.
- Showed the user what the round is worth in numbers rather than asserting it: the three
  disabled `TabItem`s on `queue` are one call and move that screen 66.7 % → 33.3 %. Also said
  plainly that **I cannot be the second labeller** (round 1's calls are all in the task note)
  and that a fully blind round is gone anyway, since the findings are published on #29. Offered
  four ways to get a labeller; **the user postponed the round** and asked to move on. Sheets and
  tooling are committed and ready.
- **#162**: new branch, task note, and `eval/llm-latency/` — a matrix driver that imports
  `ayna_ai.generate` rather than copying it, no new dependency. Then all 13 runs on this
  machine: GPU, forced CPU-only, and under 8 busy processes. 24 tests, ruff clean. `6b18e05`,
  `4c516a4`.
- **The issue's premise was wrong about this machine and that is the main finding.** It assumed
  no GPU; there is an RTX 3060 Laptop with 6 GB, so the default numbers beat the Mac's and the
  closed-network number had to be forced with `options.num_gpu = 0`. CPU-only it is 2.7× the
  Mac. `gemma4` fits in 6 GB and `qwen3:8b` does not, which **reverses the model ranking**
  between the two machines — gemma4 3.2× faster here and 10/10 keywords against 9/10.
- Recommended a **60 s** Windows deadline instead of 30 s, and **`reasons` opt-in, default
  off**, with the CPU-only evidence for both. Four of five criteria met; the fifth is galip's
  files.
- The harness caught two of my own measurement errors before they were published — a warm-up
  that warmed the wrong offload (false `1/10 over 30 s`) and a cold load inside an HTTP sample.
  `check_offload` now refuses to record a run whose `size_vram` contradicts its configuration.
  Both gotchas are in `learnings.md`.
- Next step: post #162's numbers as an issue comment and open the PR. Then PR #234's review
  (omer asks for me by name on #22's three states), then #29's labelling round when a person is
  free.
- Pushed #162 as **PR #235** and posted the numbers on the issue (`6876199863`). Then reviewed
  **PR #234** (omer, #24 pick hotkey): CHANGES_REQUESTED for one constant —
  `ELEMENT_FROM_POINT_TIMEOUT_MS` is 10 s while the Spy's own retry ladder captures for 30 s and
  120 s, and the agent serialises UIA calls on one thread, so a pick during a long capture shows
  a false `agent-error`. Confirmed what he asked: `pickState` reads #22's three states correctly.
  I owe #24 its Windows check, which is the first real test of the client's DIP -> physical
  conversion at 100 % and 150 %.
## 2026-11-14 — fourth session (continued): #162 and #23 out, #40 started

- Pushed **#162** as PR #235 with the numbers on the issue, then **reviewed PR #234** (omer, #24
  pick hotkey): CHANGES_REQUESTED for one constant. `pickState` reads #22's three states exactly
  right, including the two subtle ones, but `ELEMENT_FROM_POINT_TIMEOUT_MS` is 10 s while the
  Spy's own retry ladder captures for 30 s and 120 s, and the agent serialises UIA calls on one
  worker thread (`rpc.py:72-80`) -- so a pick during a long capture shows a false `agent-error`.
  Also noted that `highlighter.hide()` is never restored on a pick that selects nothing.
- **#23 (win32 fallback trial) done in one sitting and the answer is "do not build it".** Built
  `eval/spikes/win32_probe.py`, ran KeePass 2 twice from two launches and HandBrake once. The
  elements win32 can see are exactly the ones UIA already names, the control id is literally the
  same `automationId`, and 7 of 8 changed between launches. HandBrake: 149 elements, **one**
  HWND. One real finding: a native Win32 `Edit` kept `1001` across the restart, which
  `_GENERATED_ID` discards -- recorded as an open issue, not a change, because `model.py` is
  normative under #11 and the sample is one element. PR #236, `Closes #23`.
- Three of that probe's 19 tests exist because I got it wrong first, each time in the direction
  that *flattered* the fallback: a zero control id counted as stable, `None` in a match key
  crashed `compare` on every real run, and absent handles counted as "the handle did not move"
  (49 of them, which read as evidence against `NEVER_MATCH`). Worth remembering as a shape:
  measurement bugs are not random, they lean towards the conclusion you set out to test.
- **Started #40 (Playback v1)** and got two of the four keywords: `Wait` and `Verify`. The useful
  discovery was in the issue text all along -- "wait until the element exists, is **visible and
  enabled**" -- which #26's `_resolve_waiting` did not do, so a disabled element resolved at once
  and failed inside `actions`. #29's HandBrake finding is the real case. `Verify` needed a new
  module because three of its six properties are state the walk deliberately does not carry.
- Corrected a stale note: **#28's four criteria are all ticked**; it is open because #24 is.
- **Next step: `Select`**, whose design is written out in the task note -- it is not a pure action
  (the items of a combo box may not exist until it is expanded, #33), and Qt is expected to
  refuse, which matters because SC-20 needs it.

## 2026-11-14 — fifth session: #40 finished, PR #237
- **All four remaining keywords landed**: `Select` (`f36f1b3`) and `SelectRow` + the three row
  checkpoints (`dc395c4`), on top of this morning's `Wait` and `Verify`. 612 agent tests pass,
  ruff clean, `docs/agent-rpc.md`'s `runSteps` section rewritten, **PR #237** with both reviews
  requested, the three acceptance criteria ticked and the Windows check posted as issue comment
  `6879885017` with `needs-windows-test`.
- **`Select` cost two new modules, and the reason is worth keeping**: the item is a *descendant*
  of the target, so #26's habit of throwing the raw nodes away after `describe_tree` had to
  stop (`playback/tree.py`), and a closed combo box has no items at all, so the keyword has to
  expand the box and **read the window again** rather than look harder (`playback/items.py`).
  Everything about the Qt obstacle from #33 is still unanswered until the Windows session; the
  code reports it as a finding about the application instead of as a wrong value.
- **The row work was mostly *reading the measurements right*, not writing code.** Three shapes
  from the v0.2 ADR, and the rule had to be structural (does the item have cell children? is
  the target a Table?) rather than per framework, or the next application breaks it. The part
  that would have been easy to get silently wrong: the column list, which **must** reproduce
  omer's `GridColumns.java` to the pixel, because that rule fills the dropdown the tester picked
  the column from — otherwise a `cell` check reads the cell *next to* the one they meant and
  reports `passed`. Both of them have inbox entries about it.
- **A defensive test hung pytest with no output**: `model.describe_tree`'s ancestor walk has no
  seen-set, so a hand-built node that is its own parent loops for ever. Unreachable from a real
  UIA walk; in `learnings.md` as a fixture hazard and in the task note as a small open issue.
- **Next step**: nothing of mine blocks #40 — the Windows session answers steps 1 and 3 (SC-20
  and the cell-selecting case). Still owed: the second labelling round on #29 (a person's hour),
  #24's Windows check after omer's fix, and my five #10 entries.

## 2026-11-14 (second session) — #40's own Windows check, and the four defects it found

Ran #40's manual check (issue comment `6879885017`) at the Windows machine rather than taking a
review, because the review queue was empty and the check was the only thing of mine in the
Windows queue. **7 of 7 pass — but steps 1 and 2 failed on the code PR #237 shipped**, and
fixing them is `b28f2b9`.

- **No driver existed.** Nothing in the repo plays a step document by hand, so the first half
  hour went on writing one in the scratchpad: `UiaDesktop()` + `setup()`, `list_windows()`,
  `desktop.run_steps(handle, document, targets)`. Use `agent/.venv`, not the root one —
  `ayna_agent` is only installed in the former. Worth a committed `ayna_cli` subcommand (#61).
- **The pattern lookup never unwrapped the element.** `get_elem_interface` wants the raw
  `IUIAutomationElement`; the walk hands out a `UIAElementInfo`; only #26's `actions.py`
  unwrapped it. So on real Windows every pattern read the four new modules make returned `None`
  — Select, SelectRow, Verify's live properties, `cell`, `rowCount`, all of it — and 612 unit
  tests were green because a fake patterns function takes the fake element either way. One line
  at the seam. This is the finding I would most want a future session to remember: **a fake that
  accepts both shapes cannot tell you which shape the real one needs.**
- **`Select` reported a choice it had not made.** Qt's `SelectionItem.Select()` returns cleanly,
  changes nothing, and the item then reports `IsSelected` true. I only caught it because I read
  the combo's value back instead of trusting the `passed` — the same habit that caught #22's
  stale-node case. Every rung is now confirmed against the **target**, not the item.
- Two more from the same probe: `LegacyIAccessible.DoDefaultAction()` is the **only** route Qt
  honours, and the box was expanded only once while Qt's popup shuts itself after ~1 s, so a
  late-filling list could never be found. Both pinned by tests that fail on the old behaviour.
- **Measure from a clean start.** My first pass said three routes worked; re-measuring with a
  reset between them showed two of those three were inheriting the previous route's result.
- **SC-20 is unblocked and #33's conclusion was too broad** — UIA can choose in a Qt combo box,
  and the popup's items are in the window's tree. In galip's inbox.
- **Next step**: push `b28f2b9` + this memory, post the check result on #40, remove
  `needs-windows-test`, re-request both reviews (the PR changed under them). Then the Windows
  queue's other seven are omer's and need him present. Still owed: the second labelling round on
  #29 (a person's hour), #24's Windows check after omer's fix, my five #10 entries.
## 2026-11-14 — #29's first real numbers, and two approved PRs unblocked

- **Unblocked #227 and #232.** Both were APPROVED but `CONFLICTING`, and in both the only
  conflict was `memory-bank/people/hasan/active.md` — exactly the clash the file's own header
  predicted. Merged `origin/main` into each, kept the branch's (newer) version and folded #33's
  unique facts in below it. Re-ran #227's suite on the merge: **436 agent tests pass, ruff
  clean**. Pushed both with the user's OK; both are now APPROVED **and** MERGEABLE, and the
  merge is omer's.
- **#29: the first captures ran on this machine.** KeePass 2 `main` (74 elements, 561 ms) and
  `entry-editor` (40, 291 ms) via `kp_state.py`, HandBrake `main-summary` (149, 1267 ms), all
  with 0 read errors. Unlabelled rates: HandBrake 45 controls / 97.8 %, KeePass 2 53 / 100 %.
  Posted to the team on #29 with the warning that these are not RQ1's rate.
- **The first real run found a real bug**, which is why it was worth running before the labelled
  half: `capture` snapshotted *every* window of the process, so KeePass 2's `Add Entry` state
  wrote the dialog **and** the main form behind it, and `measure` — which counts every snapshot
  file of an app — counted the main window's controls twice. Fixed by taking the topmost window
  (`EnumWindows` is Z-order; the foreground window is useless here because the terminal is in
  front), with `--all-windows` for the old behaviour, and extracted into `pick_windows` /
  `snapshot_name` so four new tests cover it off Windows. 35 rq1 tests, 104 eval tests.
- **The useful result is one control AYNA cannot identify.** 7 of HandBrake's 8 toolbar buttons
  have an `automationId` and a `name`; the eighth has neither, so its proposal escalates to
  `{className, parentPath}`, shared by all 8. `siblingIndex` would separate it and `suggestUses`
  deliberately will not use it. Asked omer on #29 to confirm that stays — if so it is a measured
  limit for #64, not a bug to fix.
- Two environment facts cost time and are in `learnings.md`: `capture` needs `agent/.venv`
  because `recognition/uia.py` reaches `ayna_agent.rpc`, which imports `websockets` at module
  level (request in galip's inbox; his file, untouched); and leaving pilot apps open makes
  `eval/apps/trial/tests/test_uia.py` print a `0x8001010d` fatal-exception dump and take 57 s
  instead of 2.1 s — retried, nothing fails, but it reads like a crash.
- **Next step:** the eight-step check on #29 (the four screens behind a click), then ground-truth
  labelling, then the only rate worth reporting.

## 2026-11-14 (second session) — #29, the eight-step check and the first labelled rates

- Ran the check posted on #29 with the user staging each screen. **Every capture 0 read
  errors.** 6 steps passed as written; the other two were the check's own mistakes — the
  interpreter must be `agent/.venv` (the root one has no `websockets`) and HandBrake sits one
  directory deeper than every note claimed.
- **Caught a staging error in my own committed evidence.** The 2026-11-14 `main-summary` had
  been taken with HandBrake's source picker still up (149 elements against the real 118). Found
  by capturing to a probe name and diffing rather than trusting the file. The numbers I had
  already posted to #29 (45 controls / 97.8 %) came from it.
- **Retracted the headline I posted.** `e20`, the "control AYNA cannot identify", has no
  `bounds` key at all and reads `enabled: false` — a WPF template part, not a control. Withdrew
  the `siblingIndex` question to omer. The real limit is a **nameless `MenuItem` inside a named
  `Menu`**, where identity lives one level up the tree.
- **First labelled rates:** HandBrake `queue` 4/6 = 66.7 %, KeePass 2 `options` 35/35 = 100 %.
  The user's `missing` sweep came back empty on both. Picked those two screens *because* they
  carry the findings; `main-summary` would have read 100 % and hidden the result.
- **Found and closed a hole in my own harness:** a half-labelled screen measured silently, since
  `counted()` keeps only `control` rows. `apply_labels` now refuses it, with two tests.
- **Another session was working in the same tree** (`.codex/`), mid-merge on my branch. Its work
  was good — it had reached the composite-control rule independently — so I finished it rather
  than reverting it. Lesson: check `git status` before trusting a clean tree.
- `main-video` dropped from `apps.json`: HandBrake's tabs are all `enabled: false` without a
  source, so the screen's own instruction contradicted itself.
- Pushed `afe8343`; posted the correction to #29; ticked its three criteria. Issue left open and
  PR #233 still has no `Closes` — the user's call.
- **Next step:** a second independent labeller for the report's screen, then #162 (overdue,
  Week 3), which needs the machine idle.

## 2026-11-15 (second session)

- **#47 / PR #239 unblocked.** #238 (#46) had merged, so GitHub had already retargeted #239 to
  `main`; what it actually needed was an `origin/main` merge, because the squash made every file
  #46 touched conflict. Resolved "ours" on the three `eval/apps/sample/` files (each is `main`'s
  content plus #47's additions) and folded four #29 findings that reached `main` through #236
  into `active.md`'s #29 section rather than letting a one-sided resolution drop them. Pushed
  with the user's agreement; all six checks green, MERGEABLE / CLEAN.
- **Found and wrote up an intermittent UIA readiness flake** while verifying that merge: one
  `eval` run failed on `test_the_right_credentials_are_welcomed_by_name` and the pair
  `test_bug_uia.py test_sample_uia.py` failed twice more, both with the signature "the text I set
  did not land". Ruled out a window leak (the tree is clear within 0.3 s of `kill_process_tree`),
  a cross-window mix-up (two live windows of one class raise `ElementAmbiguousError`), any single
  bug version, `set_edit_text` on a fresh app, and `test_variant_uia.py` in the same slot. It
  vanishes under instrumentation, so it went to #69 as flaky-rate data rather than being patched
  blind. `learnings.md` and the #47 task note have it.
- **Started and finished the code for #54 (screenshot per step).** Two decisions with the user:
  the PNG travels as a *path* rather than base64, and there is no Pillow -- `pywin32` captures
  and `zlib` + `struct` write the file. Moved `frame_bounds` out of `recognition/uia.py` into a
  new `recognition/frames.py` because importing it dragged in `websockets` and the capture would
  not run on the root `.venv`. 475 agent tests green, ruff clean, NFR-03 met with room (41 ms at
  902x564, 91-96 ms at 1920x1020 against 300 ms), and the captured image was opened and checked
  by eye, not only timed.
- Next step: push `hasan/54-screenshot-per-step` and open the PR (`Closes #54`), saying in the
  body that the client side (reading the file and uploading it) is #51's and omer's.
## 2026-11-15 — #46 and #47, the sample app's change and bug versions

Session start found nothing of mine left on #40 (PR #237 green, both reviews requested), an
empty review queue and one stale inbox item: the five #10 literature entries had merged as
PR #171 on 31 October, so that debt was already paid. Took Week 6's pair instead.

- **#46 (controlled UI-change versions), PR #238, five CI jobs green.** Six versions, one change
  kind each plus a combined one, as **one declarative layer** rather than the six directories the
  issue asked for — the user agreed, and the reason that decided it is that `ground_truth.json`
  is generated from the same declaration the app applies, so the mapping cannot drift. 35 declared
  changes, 48 mapping rows once the form labels and the neighbours a change pushed are counted.
  26 offscreen tests, 23 through real UI Automation (17 app launches).
- **The Windows run corrected three derived values, and one is a finding for #73**: clearing a Qt
  widget's `objectName` does not remove its AutomationId — Qt substitutes the class name
  (`QApplication.login.QPushButton`), so v2e still passes #33's criterion while every scenario's
  locator fails. Also: a grid's inner UIA elements inherit the grid's id (six matches for one
  lookup), and a `QGroupBox` is a `Group`. One bug of my own: `setVisible(old.isVisible())` during
  `__init__` hid every retyped control for good.
- **#47 (bug-injected versions), PR #239, five CI jobs green**, stacked on #238. Five bugs, and
  four of them were already specified by `docs/rs/scenarios.md` down to the control, so the work
  was reading the RS rather than inventing: SC-21 wants the **login** status label, SC-19 the
  detail form's Save button disabled, SC-31 a login that opens the wrong screen, SC-34 the missing
  validation. The fifth (wrong saved value) has no scenario, so it sits where SC-20's Verify
  catches it; galip has the question. 25 offscreen tests, 5 through UIA, all green first run.
- **The constraint that shaped #47**: a Qt signal keeps calling the method that existed when
  `connect` ran, so #46's per-window hook shape cannot inject a behaviour bug. The bugs patch
  module globals and class methods before the first window exists, and `reset()` undoes them
  because one pytest process compares the correct build with the broken one.
- Both issues' criteria are ticked and each criterion has a test that checks it, including the
  change log and the "every bug names a scenario that exists" check, which reads the RS itself.
- Side effects: `uia_check.kill_process_tree` now waits for the killed process (a reaped-too-late
  app gave two `DetailWindow`s and an `ElementAmbiguousError`), and two flaky UIA tests are
  recorded in the app README as #69 data rather than re-run away.

Next step: nothing of mine is blocked on me. Retarget PR #239 to `main` once #238 merges, take
galip's answer on where bug3 belongs, and pick a Week 7/8 issue (#54, #55, #61 or #62).
- Later the same session: the user merged #47, #40 and #162 while #54 was being written, so
  #54's branch took an `origin/main` merge. It was the small reconciliation the task note had
  predicted — `runner.py`'s import block and nothing else; `_run_one`'s signature was identical
  on both sides and the capture hook dropped into #40's loop unchanged. 677 agent tests green.
  **The merge also turned up a real find**: galip's `ayna_agent/errors.py` was on `main` and
  `rpc.py` re-exported all four exceptions, but `recognition/uia.py` was still importing them
  *from* `ayna_agent.rpc`, so the decoupling that file exists for had never taken effect and the
  UIA backend still could not be imported without `websockets`. One line fixed it; #29's
  `capture` no longer needs `agent/.venv`. In `learnings.md`, in galip's inbox, and the claims
  it made stale in `frames.py`, the task note, `active.md` and the PR body are all corrected.
- **PR #248 is open** for #54 (`Closes #54`), both reviews requested.
