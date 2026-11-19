# Active — Hasan Berk Yanıkkaya (`hasan`)

Only hasan's agent edits this file. Overwrite it at every session end.

- Last update: 2026-11-19. `origin/main` (`c1d325d`) merged into `hasan/66-junit-xml` for
  PR #254; the current state lives on `hasan/55-reference-runs`'s copy of this file.

## #66 -- JUnit XML, and what the schema actually says (2026-11-15)

PR #254. `memory-bank/tasks/66-cli-junit-xml.md` has it; four things not to re-derive:

- **The format this project wrote from #249 until now does not validate**, in four ways:
  `<testsuites name=…>` takes no `name` and a nested suite needs `package`/`id`; `<properties>`
  is required and first; `<system-out>`/`<system-err>` belong to the **suite** and are both
  required; `timestamp` and `hostname` are required. Checked against a file the stand-in really
  produced, not asserted.
- **`timestamp` may not carry a timezone** -- the schema says so outright. This is the one place
  the project departs from "always an offset"; the offset stamp is kept as a `<property>`.
- **A delivery failure goes in `<system-err>` and the testcases stay green.** FR-23's exit 2
  with all tests passing would otherwise read as a reporting bug.
- **`xmlschema` is a `[dev]`-only dependency and the XSD is vendored** (Apache-2.0, noted in
  `agent/tests/data/README.md`). No product module imports either.

## #64 -- RQ1's report, and the two rules it is built on (2026-11-15)

PR #253. `memory-bank/tasks/64-rq1-report.md` has it all; four things not to re-derive:

- **The target is judged on the interval's lower bound, never the point estimate.** 39 of 41 is
  95.1 % and the Wilson interval reaches 83.9 %, so **NFR-27 is reported as not demonstrated**.
- **Only labelled screens enter a rate, and a verdict never appears without its coverage** --
  the table says "met on 1 of 4 screens", because a bare "met" is what gets quoted. Both rules
  exist because a rate of mine was quoted out of scope once and retracted.
- **`wilson()` lives in `eval/rq1/report.py`** and is the only implementation in the repo; RQ2
  (#69) and RQ3 (#77) will want it. It is checked against numeric root-finding on the score
  equation, not against its own output. Asked galip whether to move it somewhere shared.
- **A test pins the committed `report.md` to the generator's output**, so it cannot drift from
  the labels. Regenerate with `.venv/Scripts/python.exe eval/rq1/report.py`.

#63 -- the triage rule, and the one decision it had to make (2026-11-15)

PR #251. `memory-bank/tasks/63-failure-triage.md` has the mapping; what not to re-derive:

- **A failure the *agent* caused never wears one of FR-35's five.** The ADR left this call to
  #63, and the cases are wider than the two it named: a keyword not implemented, a refused step
  document, an unmatchable property set, a provider that refuses the action, an unreadable
  property. `category` is absent for all of them, and the **decision log** carries a finer
  `reason` that is never absent. The reason it matters: RQ2 and RQ5 are computed from this
  field, and a `timeout` that was really "this agent has no `SelectRow` yet" could never be
  separated out again once stored.
- **`playback/triage.py` is the only place that decides.** `done()` takes the *exception* and
  triages itself; do not add a `category=` at a call site.
- **`CheckpointError` is not `assertionFailed`** -- it means the checkpoint itself is wrong,
  whatever the application is doing. There is a test named after that trap.
- **A sixth value (`notAttempted`) is proposed, not taken**: asked of omer on #63 and #251,
  because it is a minor version on two shared schemas and #248 already holds 1.2.
- `NotReady` moved from `runner.py` to `resolve.py` so triage can name it without a cycle, and
  `RowFailed`/`SelectFailed` now carry a `kind`, because each merged "it is not there" with
  "the application refused it" -- two findings a stored result could never split again.
- **Nothing passes `decisions=` yet.** Criterion 3's ≥50 examples (week 12) will come from the
  CLI runner in CI once #250 and #251 are both on `main`.
- **CI caught an import that could not fail here**: `python -m pytest` puts the CWD on
  `sys.path` and bare `pytest` does not. Reproduce the agent job with
  `agent/.venv/Scripts/pytest.exe`, never `python -m pytest`. In `learnings.md`.

## From `hasan/40-playback-v1`, kept at merge

- Current issue: **#40 (Playback v1, Week 5, due 23 Nov)** on `hasan/40-playback-v1`.
  All six keywords are implemented, all three criteria are tested, **and the Windows check ran
  here on 2026-11-14: 7 of 7 pass — but only after four fixes (`b28f2b9`)**. `Wait` and the
  ready gate (`826b386`), `Verify` (`ca51c83`), `Select` (`f36f1b3`), `SelectRow` + the three
  row checkpoints, then the four fixes. **623 agent tests pass, ruff clean, PR #237 open** with
  both reviews requested. **Read `memory-bank/tasks/40-playback-v1.md` before touching any of
  it**: the three row shapes, the duplicated column rule, the message wording and now the
  read-back ladder are all decisions with reasons.
- **The four defects the check found are the lesson of this issue, not a footnote.** All four
  needed a real provider and all four passed 612 unit tests. (1) **The pattern lookup never
  unwrapped the element** — `get_elem_interface` needs the raw `IUIAutomationElement`, the walk
  hands out a `UIAElementInfo`, and only #26's `actions.py` unwrapped it, so on real Windows
  *every* pattern read #40 added was silently "unsupported": Select, SelectRow, Verify's
  value/checked/selected, `cell`, `rowCount`. It is now done once inside `uia_patterns`.
  (2) **`Select` reported a choice it had not made** — Qt's `SelectionItem.Select()` returns
  cleanly, changes nothing, and the item then says `IsSelected` true. Every rung is now
  confirmed by reading the **target** back. (3) `LegacyIAccessible.DoDefaultAction` joined the
  ladder: the only rung Qt honours. (4) The box was expanded **once**, and Qt's popup shuts
  itself ~1 s later, so a late-filling list stayed invisible for good.
- **#40 is out and nothing of mine is left on it.** Pushed (`75f2b18`), result posted as issue
  comment `6880618635`, `needs-windows-test` removed, both reviews re-requested because the PR
  changed under them. It waits on the two reviews and then on a merge.
- **The Windows queue's other seven are all omer's** (#206, #204, #184, #68, #38, #24, #17) and
  need him present, so they wait for the weekly session — do not run them alone. #24's is mine
  to run but only after his fix to PR #234.
- **SC-20 is unblocked and #33's Qt finding is overturned** (too broad): UIA *can* choose an
  item in a Qt combo box, the popup's items *are* in the window's tree once expanded, and
  `LegacyIAccessible.DoDefaultAction()` on the item works. In galip's inbox.
- **The driver for a manual `runSteps` check does not exist in the repo** and had to be written
  from scratch (scratchpad, not committed): `UiaDesktop()` + `setup()`, `list_windows()` to pick
  the handle, then `desktop.run_steps(handle, document, targets)` — the `rpc.py` path with the
  socket taken out. `ayna_agent` is **not** pip-installed in the root `.venv`; use
  `agent/.venv/Scripts/python.exe`, which has it editable along with `websockets`. Worth a
  committed `ayna_cli` subcommand when #61 starts, because every future playback check needs
  it — **the user decided on 2026-11-14 that this stays inside #61's scope**, not its own issue.
- **The sample app's grid is empty until a search runs**, so any grid step needs a `Click` on
  `refreshButton` first, and `--screen main` skips the login. The automation ids are Qt-prefixed:
  `QApplication.main.customerGrid`, not `customerGrid`.
- **This file is now spread over four branches and no copy is complete.** `hasan/29-rq1-measure`
  has the long review history and #29; `hasan/162-windows-llm-latency` has #162 and #23's
  summary; this one has #40. **Whichever merges last keeps every branch's own section.** Also:
  `eval/pyproject.toml`'s `testpaths` line is edited on the #29 *and* #162 branches and **will
  conflict** -- keep both entries (`rq1/tests` and `llm-latency/tests`).
- **#162 and #23 are delivered and out; #29 is waiting on a human.** PR **#235** (#162, no
  `Closes`: criterion 5 is galip's files) + issue comment `6876199863`. PR **#236** (#23,
  `Closes #23`) + comment `6876502627`. PR **#233** (#29, deliberately no `Closes`) needs the
  second labelling round, which the user postponed on 2026-11-14 -- the blind sheets and
  `measure.py agree` are committed and ready, so it needs a person's hour and nothing else.
- **PR #234 (omer, #24) reviewed 2026-11-14, CHANGES_REQUESTED**: `pickState` reads #22's three
  states correctly, but `ELEMENT_FROM_POINT_TIMEOUT_MS` is 10 s while the Spy's own retry ladder
  captures for 30 s and 120 s and the agent serialises UIA calls on one worker thread -- so a
  pick pressed during a long capture shows a false `agent-error`. **I owe #24 its Windows check**
  after his fix: it is the first real test of the client's DIP -> physical conversion at 100 %
  and 150 %, the half #22's scaling evidence does not cover.
- **The Project status is settable again, and all four of mine are now `In progress`** (#23,
  #29, #40, #162). The token was missing `project`; the user granted it on 2026-11-14 with
  `gh auth refresh --hostname github.com --scopes project`. **`--hostname` is required**, because
  the shell here is non-interactive and `gh auth refresh -s project` alone exits with
  "--hostname required when not running interactively" -- which is what blocked every earlier
  session from touching the board.
- **#28's four acceptance criteria are all ticked** -- the earlier note saying "three of four,
  the last is galip's #7" was wrong. It stays open because its dependency **#24** is still open.
- **Merge note (2026-11-15, omer's agent, merging `origin/main` into `hasan/162-windows-llm-latency` for PR #235):** both sides of this file are kept, as the rule above asks. The bullets under "From `hasan/162-windows-llm-latency`" are that branch's copy, unedited; reconcile them at your next session end.

## From `hasan/162-windows-llm-latency`, kept at merge

- Current issue: **#162 (NFR-12 Windows latency, Week 3, overdue) — measurement DONE**,
  `hasan/162-windows-llm-latency`, commits `6b18e05` and `4c516a4`. Four of its five
  acceptance criteria are met; the fifth is galip's files. **PR #235 is open** (deliberately no
  `Closes`, since criterion 5 is galip's) and the numbers are posted as issue comment
  `6876199863`. It was `CONFLICTING` after #233 merged; this merge is the fix.
- **#29 is still open and in progress** on `hasan/29-rq1-measure` (PR #233, deliberately no
  `Closes`). Its three criteria are ticked; what is left is the **second independent labelling
  round**, which the user **postponed on 2026-11-14**. Everything for it is committed and
  ready — blank blind sheets at `eval/rq1/labels/{handbrake-queue,keepass2-options}-r2.csv`
  plus `measure.py sheet` / `agree` / `measure --labels --round r2` (`fdf05e9`), and
  `labelling.md` §8. It needs a person's hour and nothing else.
- **The second labelling round is worth doing before #64 quotes anything, and here is why in
  numbers:** HandBrake `queue`'s three disabled `TabItem`s are **one** judgement call and they
  move that screen from **66.7 % (4/6)** to **33.3 % (1/3)**; KeePass 2 `options` is symmetric
  (100 % against 70.4 % if the 16 composite inner parts are called `control`). Both headline
  rates rest on a single labeller's call. **The agent cannot be that second labeller** —
  round 1's labels and every one of its calls are written out in the #29 task note — and a
  *fully* blind round is no longer available inside the team either, since the composite rule,
  the nameless-`MenuItem` finding and the `e20` retraction are published on #29.
- **PR #234 (omer, #24 pick hotkey): reviewed 2026-11-14, CHANGES_REQUESTED.** `pickState`
  reads #22's three states exactly right, including the two subtle ones (a `snapshotId` other
  than the one on screen means none; an `elementId` missing from the tree means "changed"), and
  the tests cover them. **One real bug**: `ELEMENT_FROM_POINT_TIMEOUT_MS` is 10 s, but the agent
  runs every UIA call on one worker thread in arrival order (`rpc.py:72-80`), so a pick waits out
  a running capture — and the Spy's own retry ladder is `LONGER_SNAPSHOT_BUDGETS_MS =
  [30_000, 120_000]`. Pressing the hotkey during a "capture for longer" therefore shows an
  `agent-error` while the capture is fine. Asked him to derive it the way `snapshot()` does.
  Smaller: `highlighter.hide()` is never restored on a pick that selects nothing, so the frame
  around the selected node disappears until the user clicks another one.
- **I owe #24 its Windows check** (steps on the issue, `needs-windows-test`): the own-window check
  only matches on Windows, and this is the **first exercise of the client's DIP → physical
  conversion** at 100 % and 150 % — the half #22's scaling evidence does not cover. Told omer I
  will test the version *after* the timeout fix.
- **`gh` cannot set the Project status**: the token is missing `read:project`, so #162 is still
  `Todo` on the board. `gh auth refresh -s project` is interactive, so the user has to run it.
- **#22 is DONE and closed.** All three criteria are ticked, the scaling check ran here on
  2026-11-12 at 100 % and 150 % and passed at both, and **PR #227 was squash-merged on
  2026-11-14 (`bfcdb35`)**, which closed the issue. Nothing is left on it.
- **#29 is MERGED and CLOSED, and the second labeller is still owed.** PR **#233** was
  squash-merged by the user on 2026-11-14 (`6fd87a9`), which **closed #29 even though the PR
  deliberately carried no `Closes`** — the PR was linked to the issue in GitHub's Development
  panel, and a linked issue closes on merge regardless of keywords. So **the closing is a
  side effect of the link, not a judgement that the work is done**: a second independent
  labeller is still owed and two open issues still feed #64. If that matters, reopen #29 or
  carry the remainder as a new issue. **Watch for this on every PR that omits `Closes` on
  purpose** — unlink it in the Development panel, or the omission buys nothing.
- **The eight-step check is done** — every screen captured with 0 read errors, 6 steps passing
  as written and the other two being the check's own mistakes. HandBrake is now 3 screens
  (`main-summary`, `preferences`, `queue`); `main-video` is **dropped from `apps.json`** because
  every tab reads `enabled: false` with no source loaded, so the instruction contradicted itself.
- **The first labelled rates, per screen, are the only ones that may be quoted**: HandBrake
  `queue` **4/6 = 66.7 %**, KeePass 2 `options` **35/35 = 100 %** (`eval/rq1/labels/*.csv`,
  `missing` sweep run by the user and empty on both). **Never quote the app totals**:
  `measure --labels` mixes labelled and unlabelled screens, so KeePass 2's app line reads
  99 / 100 % while only one of its four screens is labelled.
- **The `e20` claim is RETRACTED and the question to omer withdrawn.** It is not a control:
  **no `bounds` key at all**, `enabled: false`, a WPF toolbar template part that is never
  rendered. So `siblingIndex` was never the issue, and a missing `bounds` is the cheap test for
  "not a control". Said so on #29 (comment `6874969764`) and in omer's inbox. The *real* limit is
  **a nameless WPF `MenuItem` inside a named `Menu`**: HandBrake's `Options` split button and
  `When Done` dropdown carry no `automationId` and no `name`, the name sits on the parent
  `Menu`, and a per-element descriptor does not reach for an ancestor's identity. That same
  shape is *recognised* in `main-summary`'s status bar only because it has no sibling — one app
  pattern giving both a pass and a fail, which belongs in #64.
- **The unlabelled rate is NOT reliably the optimistic one** — I had this backwards and so did
  the guide; both are corrected. The denominator is wrong in **both** directions: a missed
  control flatters it, a composite control's inner parts punish it. KeePass 2's Options screen
  shows both at once (70.4 % unlabelled → 100 % labelled, all 19 dropped rows non-controls).
- **#227 and #232 are MERGED** (2026-11-14, `bfcdb35` and `d788d64`), so **#22 is closed** and
  #221's notes are on `main`. Both had been `CONFLICTING` on this file alone; each took an
  `origin/main` merge, and 436 agent tests were re-run green on #227's.
- **Merging a PR is the agent's prohibition, not the user's** (AGENTS.md §6 is addressed to the
  agent). The user has `push` on the repo, `protect-main` asks only for 1 approval, squash and
  resolved review threads, and there are **no bypass actors and no CODEOWNERS gate** on who
  merges. So an approved PR of mine is the user's to merge whenever they want — **do not tell
  them it is waiting on omer**, which is how the earlier "neither mine to merge" note got
  misread. The user asked about exactly this on 2026-11-14.
- **`capture` runs on `agent/.venv`, not the repo-root one** — `recognition/uia.py` takes its
  exception types from `ayna_agent.rpc`, which imports `websockets` at module level. galip has
  the request to decouple it; `rpc.py` is his file and is untouched.

## #46 and #47 -- the sample app's change and bug versions (2026-11-15)

Both shipped as **one layer each inside `eval/apps/sample/`, not as the directories the issues
asked for** (the user agreed on 2026-11-15, and both PR bodies say so): `variants.py` +
`variant_patch.py` + `ground_truth.py` + `ground_truth.json` + `variants.md` for #46, and
`bugs.py` + `bug_patch.py` + `bugs.md` for #47. Reasons, in the order they decided it: the
ground truth cannot drift from the app when both come from one declaration; `eval/AGENTS.md`
allows a module name **once** per tree with no exception for scripts (#199), so six or five
copies of `windows.py`/`model.py`/`texts.py` would each need unique names; and a reviewer can
read a change set, while nobody reads a diff of six trees.

**The measured finding worth carrying into #73 and the client:** clearing a Qt widget's
`objectName` does **not** remove its AutomationId -- Qt substitutes the class name, so
`login.loginButton` becomes `QApplication.login.QPushButton`. Measured for `QPushButton`,
`QLineEdit` and `QTableWidget` on three screens. Consequences: `uia_check --variant v2e` still
**passes** #33's "an AutomationId on every control" while no scenario's locator survives; the id
is no longer the logical name; and two same-class siblings that both lose their name would
collide (that last part is reasoned, not measured). A healer matching on `automationId` will see
a plausible-looking id that means nothing. In galip's inbox and in `learnings.md`.

Three more things the next session should not re-derive:

- **A grid's inner UIA elements inherit the grid's AutomationId** (Pane + four Headers), so a
  lookup by id finds six elements unless it filters with `uia_check.is_app_widget`.
- **A Qt signal keeps calling the method that existed when `connect` ran**, which is why #47's
  bugs patch module globals and *class* methods before the first window exists, while #46's UI
  changes use a per-window hook at the end of each `__init__`. Two layers, two shapes, one
  reason.
- **A window kept only in a temporary takes its C++ children with it**: both the ground-truth
  generator and #47's symptom probes hold each window in a local until they have read it.

Numbers, all run on this machine on 2026-11-15: `pytest eval` **241**, the CI invocation
(`cd eval; pytest -q`) **185**, the sample app's own suite **136**, ruff clean. #46's Windows
file is **23 tests / 17 app launches** and #47's is **5 / 5**. #238's five CI jobs all pass.

**What neither issue proves, and must not be claimed:** that a correct AYNA test catches these
bugs, or that a healer repairs these changes. That needs #62 (scenarios in the editor), #54/#55
(played by the agent) and #63 (triage); `bugs.md`'s last section and both task notes say so.

## #40, so the next session does not re-derive it

`playback/runner.py` had the shape from #26 and `IMPLEMENTED = {"Click", "Type"}`; it is now
every keyword of step schema v0.2, with four new modules: `playback/checkpoint.py` (one
property of one element), `playback/tree.py` (one read of the window, plus the schema's single
rule for the text a cell or an item shows), `playback/items.py` (`Select`) and
`playback/rows.py` (`SelectRow` and the row checks). `agent/tests/grids.py` holds the three
measured row shapes for both row test files.

**The five decisions most likely to be re-derived or broken:**
- **`Select` is not a pure action**: a closed combo box has no items at all, so the target is
  expanded and the window **read again** before looking (#33) — **every poll it shows nothing,
  not once**, because Qt's popup closes itself. The ladder is `SelectionItem` → `Invoke` →
  `LegacyIAccessible.DoDefaultAction`, **each rung confirmed by reading the target back** with
  one `POLL_INTERVAL_S` of grace (Qt applies a choice 32 ms late). An editable box takes the
  text through `SetValue` only after the whole wait, and that value is read back too — with no
  grace, which is a known open issue now that a late-applying provider is known to exist.
- **Three row shapes, by structure not by framework**: the item is the row (KeePass 2), the
  items are the cells and only `GridItem` says which row they belong to (Qt has no row
  element), or the item is a one-cell row (`QListWidget`).
- **`playback/rows.py:columns_of` duplicates `server/.../GridColumns.java` on purpose** and
  must stay identical: that rule fills the dropdown the tester picked the column from, so a
  divergence reads the cell *next to* the one they meant. omer has this in his inbox.
- **`SelectRow` never uses `Invoke`** (it would *activate* the row and open a window); the
  fallback is MSAA's `LegacyIAccessible.Select`, which KeePass 2 needs.
- **A `SelectRow` on a cell-selecting view passes with a `message`** — the first passing step
  that carries one, which the ADR asks for and the run report (#59) renders.

- **"Ready" is the pre-step wait and it is more than "resolves"**: a step waits until the target
  resolves *and* is neither disabled nor off screen -- what the issue text asks for ("exists, is
  visible and enabled") and what the schema calls ready. #26 waited only for resolution, so a
  disabled element resolved at once and the step then failed inside `actions` for an unstated
  reason. **HandBrake is the real case from #29**: with no source loaded *every* tab reads
  `enabled: false`.
- `enabled`/`offscreen` of **`None` count as ready** -- a provider reporting neither is common
  and `NEVER_MATCH` already calls both unreliable, so refusing would time out every step of such
  an application.
- **A `Verify` waits only for resolution**, because a checkpoint may be *about* a disabled or
  offscreen element and would otherwise be unplayable.
- **Three of `Verify`'s six properties are not in a descriptor** and are read live: `value`
  (`ValuePattern`, then `LegacyIAccessible` -- the ladder `Type` writes down), `checked`
  (`TogglePattern` **On**, so indeterminate is *not* checked) and `selected`
  (`SelectionItemPattern`). `name`, `enabled` and `visible` come from the walk's descriptor.
- **"Cannot be read" is its own failure, not `false`** -- no `TogglePattern` on the target means
  the check does not apply, and "expected true, got false" would blame the application instead.
- **`expected: ""` matches an element with no text**, or an empty error label could never be
  verified. A target that vanishes mid-check reports *that*, not a property failure.
- **The target is re-resolved on every poll**, never kept: a re-read gives new live elements and
  the old one is a stale handle (the same reason #22 compares identity rather than geometry).
- **Message wording is fixed by the PR #231 review and the tests assert the exact strings**,
  because the run report (#59) is written against them. ` after N ms` for a check that re-read
  until the time ran out, `within N ms` for an element that never appeared -- two waits, two
  words. **#40's third criterion says "after N ms" for element-not-found while #26 shipped
  "within": keep `within`** and say so on the issue rather than changing it silently.
- **A field on a keyword that forbids it is refused, not ignored** (`value` on a Click, `row` on
  a Verify): ignoring it would play a mis-built document as something else and report `passed`.

## #23 -- the win32 fallback, answered and deliberately not built

- The elements win32 can see are exactly the ones UIA already names, the number it offers is
  literally the same `automationId`, and it is **not stable across runs** (7 of 8 control ids
  changed between two launches). Everything UIA cannot name has **no HWND at all**: 58 of 74 in
  KeePass 2, and HandBrake is 149 elements with **one** HWND, the window. WPF and Qt cannot gain
  anything, structurally.
- **The one genuine finding**: `e58`, a native Win32 `Edit` (class `Edit`, no `WindowsForms10.`
  prefix), kept control id **1001** across a restart -- real identity that `_GENERATED_ID` throws
  away for being a bare number. Candidate rule: trust a bare number from a native Win32 class,
  not from `WindowsForms10.*`. **Sample size one**, and `model.py` is normative under #11, so it
  needs an ADR and a `FEATURE_VERSION` bump. Open issue, not a change.
- `eval/spikes/win32_probe.py`, 19 tests off Windows; report `eval/spikes/win32-fallback.md`.
  **Three of those tests exist because the probe got it wrong first, each in the direction that
  flatters the fallback** -- do not simplify them away.
- **`UiaDesktop()` needs `setup()` called by hand** in a script; #29's harness and this probe
  both tripped over it. Asked galip for a line in `agent/AGENTS.md`.
- `eval/spikes/` is excluded from ruff and has no CI job, so its tests only run when someone
  names the path. Worth one issue together with `eval/pyproject.toml`'s `testpaths`.

## #162 -- NFR-12 on Windows, so it is not re-measured

Report `eval/llm-latency/report.md`, 13 result files under `eval/llm-latency/results/`.

- **The issue's premise was wrong about this machine**: it has an **RTX 3060 Laptop, 6 GB**, so
  the default numbers beat the Mac's. Forced CPU-only it is **2.7x slower than the Mac**.
- **`qwen3:8b` does not fit in 6 GB** (6.0 GB loaded, 30 % CPU / 70 % GPU); **`gemma4:e4b-it-qat`
  does** (3.1 GB, 100 % GPU). So gemma4 is **3.2x faster here** and matched the expected keywords
  **10/10 against 9/10** -- while being the *slower* of the two on the M2. "Which model is
  faster" is a question about the box, not the model.
- p50/p95 s: CLI qwen GPU **5.34 / 8.38**, CLI gemma GPU **1.65 / 2.47**, CLI qwen CPU
  **15.30 / 22.68**, HTTP qwen GPU **8.59 / 16.04**, HTTP qwen CPU **23.24 / 41.30**.
- **Recommended: a 60 s Windows deadline, not 30 s** (~1.4x the worst measured p95 of 43.33 s),
  and **`reasons` opt-in per request, default off** (#78) -- CPU-only it is p95 22.68 s with 0/10
  over the deadline against 43.10 s with 2/10.
- **A fully VRAM-resident model is almost immune to the machine's own load** (gemma4 1.65 ->
  1.70 s at 59 % busy; qwen3 5.34 -> 6.29 s). Under load the damage is in the **tail**.
- **Warm every offered model, not just the default**: a first request against a non-default model
  pays 14.71 s on the GPU and **25-51 s CPU-only**.
- **Output is not reproducible run to run at temperature 0 with seed 42** -- 1 of 10 sentences
  differed between two runs that differed only in machine load. Contradicts
  `ai/spikes/llm-smoke.md` and matters for **RQ3 (#77)**. In galip's inbox with the `reasons`
  toggle and criterion 5.
- Two gotchas now in `learnings.md`: a subclassed warm-up that skips `request_body` warms the
  wrong offload, and **Ollama reuses a runner already loaded CPU-only** (so `ollama stop` before
  a GPU run, and read `size_vram` instead of trusting the configuration you asked for).

## #162 — the numbers, so they are not re-measured

Full report `eval/llm-latency/report.md`; 13 result files under `eval/llm-latency/results/`,
each carrying the machine, the offload in VRAM and every row. `run.py` drives **galip's**
`ayna_ai.generate` rather than a copy, the same way `eval/rq1/measure.py` drives `ayna_agent`.

- **This machine is not the machine NFR-12 is about.** It has an **RTX 3060 Laptop, 6 GB**, so
  its default numbers beat the Mac's. Forced CPU-only it is **2.7× slower than the Mac**. Every
  configuration was therefore run twice, GPU and CPU-only, and the pair is the result.
- **`qwen3:8b` does not fit in 6 GB**: loads as 6.0 GB, runs **30 % CPU / 70 % GPU**.
  **`gemma4:e4b-it-qat` does**: loads as 3.1 GB, **100 % GPU**. So gemma4 is **3.2× faster
  here** and matched the expected keywords **10/10 against qwen3's 9/10** — while being the
  *slower* of the two on the M2. **"Which model is faster" is a question about the box.**
- Headline p50/p95 seconds: CLI qwen GPU **5.34 / 8.38**, CLI gemma GPU **1.65 / 2.47**, CLI
  qwen CPU **15.30 / 22.68**, CLI gemma CPU **14.29 / 19.64**, HTTP qwen GPU **8.59 / 16.04**,
  HTTP gemma GPU **2.36 / 3.56**, HTTP qwen CPU **23.24 / 41.30**.
- **Recommendation: a 60 s Windows deadline, not 30 s** (~1.4× the worst measured p95 of
  43.33 s). 30 s only where the model sits wholly in VRAM. A deadline is not a latency target,
  so raising it does not weaken NFR-12.
- **Recommendation: `reasons` opt-in per request (#78), default off** — CPU-only, p95 22.68 s
  and 0/10 over the deadline without, 43.10 s and 2/10 with, for ~55 % more output tokens.
- **A fully VRAM-resident model is almost immune to the machine's own load**: gemma4 1.65 →
  1.70 s at 59 % busy; qwen3 5.34 → 6.29 s. Under load the damage is in the **tail** — the
  CPU-only service's p50 barely moved (23.24 → 22.75 s) while its deadline share went 2/10 →
  3/10. Relevant because the agent, client and server share the box during a run.
- **Warm every offered model, not just the default**: a first request against a non-default
  model pays 14.71 s on the GPU and **25–51 s CPU-only**.
- **Two gotchas now in `learnings.md`**: a subclassed warm-up that skips `request_body` warms
  the wrong offload (it produced a false `1/10 over 30 s`), and **Ollama reuses a runner
  already loaded CPU-only** rather than reloading it for a request with no `num_gpu` — which is
  the only reason the service can be measured CPU-only, and a trap in the other direction, so
  `ollama stop` before a GPU run and read `size_vram` instead of trusting the config.
- **Not established, and the report says so:** ten sentences and one run each, so every p95 is
  an interpolation between the 9th and 10th value; the `json` baseline scored **0/10** valid
  (the model writes `action` where the schema wants `keyword`, targets and values correct); and
  **output is not reproducible run to run at temperature 0 with seed 42** — 1 of 10 sentences
  differed between two runs that differed only in machine load, which contradicts
  `ai/spikes/llm-smoke.md` and matters for **RQ3 (#77)**. All in galip's inbox.
- **What is left on #162 is not mine**: criterion 5 is `ai/README.md` and `ai/API.md` labelling
  which latencies are Apple-silicon, and the `reasons` toggle needs `service.py:181`. Both
  requested in galip's inbox 2026-11-14, with the numbers.

## What is waiting on someone else

- **PR #239 (#47)**: both reviews requested from omer and galip. It is **already based on
  `main`** -- GitHub retargeted it by itself when #238 merged, so no `gh pr edit` was needed;
  what it did need was an `origin/main` merge, because #238 was squashed.
- **galip owes an answer on where `bug3` belongs** (in his inbox): the plan asks for a "wrong
  saved value" bug and the RS has no scenario for one, so it sits where SC-20 catches it (the
  wizard's summary carries the role instead of the department). Moving it is a one-row change.
- **PR #237 (#40)** waits on two reviews; its Windows check ran on 2026-11-14, 7 of 7.
- **PR #235 (#162)** and **PR #236 (#23)** wait on reviews.
- **#29 is merged and closed but a second independent labeller is still owed** -- the closing was
  a side effect of the Development-panel link, not a judgement that the work is done.
- **The Windows queue's other seven are omer's** (#206, #204, #184, #68, #38, #24, #17) and need
  him present. #24's check is mine to run after his fix to PR #234 (my CHANGES_REQUESTED there:
  `ELEMENT_FROM_POINT_TIMEOUT_MS` is 10 s while the Spy captures for 30 s and 120 s).

## Still live from earlier sessions

- **#40 (Playback v1)**: all six keywords, the ready gate, the three row shapes, the read-back
  ladder. `memory-bank/tasks/40-playback-v1.md` has the decisions, and the four defects the
  Windows check found are the lesson -- every one needed a real provider and every one passed
  612 unit tests. Open: `items.write`'s read-back has no grace period, and three branches of
  playback have never met a real provider (the cell-selecting view, a WPF `DataGrid`, an
  editable combo box). The manual `runSteps` driver stays inside #61's scope.
- **#162**: a 60 s Windows deadline, not 30; `gemma4:e4b-it-qat` fits 6 GB VRAM and `qwen3:8b`
  does not, so gemma4 is 3.2x faster *here* -- "which model is faster" is a question about the
  box. Output is **not** reproducible at temperature 0 with seed 42 (matters for RQ3, #77).
- **#23**: the win32 fallback is answered and deliberately not built. One genuine finding: a
  native Win32 `Edit` kept control id 1001 across a restart, which `_GENERATED_ID` throws away.
  Sample size one; it needs an ADR and a `FEATURE_VERSION` bump, so it is an open issue, not a
  change.
- **#29**: the first labelled rates, per screen, are the only quotable ones -- HandBrake `queue`
  **4/6 = 66.7 %**, KeePass 2 `options` **35/35 = 100 %**. Never quote the app totals, because
  `measure --labels` mixes labelled and unlabelled screens. Three more of its findings, kept here
  because `main` held them only in a preamble that this session replaced:
  - **The `e20` claim is retracted**: it is not a control (no `bounds` key at all,
    `enabled: false`, a WPF toolbar template part that is never rendered), so `siblingIndex` was
    never the issue and **a missing `bounds` is the cheap test for "not a control"**. The *real*
    limit is a **nameless WPF `MenuItem` inside a named `Menu`** (HandBrake's `Options` split
    button, `When Done` dropdown): the name sits on the parent, and a per-element descriptor does
    not reach for an ancestor's identity. The same shape is *recognised* in `main-summary`'s
    status bar only because it has no sibling -- one pattern giving both a pass and a fail, which
    belongs in #64.
  - **The unlabelled rate is not reliably the optimistic one** (I had this backwards and so did
    the guide; both are corrected). The denominator is wrong in **both** directions: a missed
    control flatters it, a composite control's inner parts punish it. KeePass 2's Options screen
    shows both at once (70.4 % unlabelled -> 100 % labelled, all 19 dropped rows non-controls).
  - **The eight-step capture check is done**, every screen with 0 read errors. HandBrake is
    3 screens (`main-summary`, `preferences`, `queue`); `main-video` is **dropped from
    `apps.json`**, because every tab reads `enabled: false` with no source loaded.
- **Four inbox items are still live**: (1) add `ayna_cli*` to `agent/pyproject.toml`'s packages
  when #61 starts; (2) galip's four Qt measurements from #147; (3) build
  `eval/nl/objects/sample.json` from `uia_check.py --json`, plus my §8 points for #57; (4)
  confirm for #67 that playback needs an unlocked interactive desktop, and settle TBD-3 (Windows
  versions, LTSC) with omer. The #10 literature entries are **done** (PR #171, 31 October).

## Machine and tooling facts that keep costing time

- **`capture` and anything importing the recognition backend run on `agent/.venv`**, not the
  repo-root one (`recognition/uia.py` -> `ayna_agent.rpc` -> `websockets`). The sample app and
  everything under `eval/` run on the **root** `.venv`, the only one with PySide6.
- **`pytest eval` is not the run CI does.** Reproduce CI with
  `cd eval; ../.venv/Scripts/python.exe -m pytest -q` before pushing anything that adds a module
  under `eval/`.
- **The Project status needs `--hostname`**: `gh auth refresh --hostname github.com --scopes
  project`. The option ids and the `item-edit` command are in
  `memory-bank/project/conventions.md`.
- **Leave no UIA-driven app open while the `eval` suite runs**, and expect the occasional flake:
  two were seen on 2026-11-15 (a modal dialog not yet in the tree; two `DetailWindow`s because a
  killed app had not been reaped -- `kill_process_tree` waits for it now). Both are #69 data.
- **Merging a PR is the agent's prohibition, not the user's.** An approved PR of mine is the
  user's to merge whenever they want -- do not tell them it is waiting on omer.
