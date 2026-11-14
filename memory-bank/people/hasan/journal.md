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
