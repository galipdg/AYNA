# #161 Root-cause the WinForms snapshot outlier from #6

- Issue: https://github.com/galipdg/AYNA/issues/161
- Owner: hasan · Branch: `hasan/161-winforms-walk`
- Started: 2026-10-31 · Last update: 2026-11-01

## Approach
Rebuild the window state the #6 dump was taken in, then walk it once per cost centre with a
new script, `eval/spikes/uia_probe.py`, timing every element separately. Totals alone cannot
tell "every element is slow" from "three elements are very slow", and the whole question is
which of the two the 278.5 s was. Result and recommendation: `eval/spikes/uia-walk-cost.md`.

## Decisions (small, local to this task)
- 2026-10-31 — A separate script rather than a flag on `uia_dump.py`. The dump writes one
  document per target and is the thing #6 measured; adding timing modes to it would change
  the artefact that the earlier result came from. `uia_probe.py` imports `find_windows`,
  `PATTERNS`, `MAX_NODES` and `MAX_DEPTH` from the dump, so the walk is the same walk.
- 2026-10-31 — The state is driven with pywinauto (`eval/spikes/kp_state.py`), not set up by
  hand. Driving the wizard blind does not work: six dialogs, two of them message boxes that
  appear only sometimes, and WinForms elements go stale as soon as a dialog is replaced
  (`COMError -2146233083`), so the script looks at what is on screen and does the one thing
  that moves it forward. It is committed unfinished: it reaches the master-key dialog
  reliably but has not yet completed the wizard unattended (see Open issues). The measured
  state in this session was reached with it plus two confirmations from a one-off helper.
- ~~2026-10-31 — The database keeps KeePass's default path and name (`Database.kdbx` under
  the user's Documents), because that is what the #6 dump's window title shows.~~
  **Superseded 2026-11-01** by galip's #170 review: that path is a OneDrive-synced folder
  and `--fresh` deletes what it points at, so matching the dump's title is not worth
  pointing a delete at a place where a person may keep a database. The demo database is
  `C:\ayna-pilots\ayna-demo.kdbx`; the window title differs from #6's and changes no
  element. One deviation from #6 remains: this run saves the file, so the title has no `*`.
- 2026-11-01 — Re-measured rather than rescaled after the deduplication fix. The duplicate
  pass inflated every total by ~26 % *and* flattered every per-element mean (a second walk
  of an already-realised subtree is cheaper), so scaling 154 → 114 would have produced a
  number nobody measured. Six runs today instead: the full walk is 18.5 ms per element, not
  11.6 ms. The #12 budget argument moved from "3× the measured walk" to "~330 elements at
  the descriptor rate", which is the headroom that actually matters.
- 2026-11-01 — Three reliability fixes to `kp_state.py` kept, although they are wider than
  the review asked for, because without them the state cannot be rebuilt: a **classic**
  message box (`#32770` with `Static` text) is answered over Win32 `BM_CLICK`, since while
  one is open UIA against the process blocks for minutes — the very thing this issue
  measured; the password and file-name boxes are **focused** (`set_focus`), never clicked,
  because a click leaves them unfocused and the keystrokes vanish (KeePass then complains
  about an *empty* master password); and a failed `invoke()` on a button whose dialog has
  since closed counts as success (`alive()` over Win32). KeePass's new-database notice is a
  *task dialog*, not a message box, and is deliberately left to UIA — pressing its OK made
  the script loop.
- 2026-10-31 — Measurement, not rescue: the point of #161 is a defensible budget for #12, so
  the note ends with a budget and a default property set. The mechanism found on the way (a
  modal message box) changes the budget's shape — a deadline enforced on a timer rather than
  between elements — but not the decision to have one.

## Status
- [x] `eval/spikes/uia_probe.py` with six cost centres, per-element timings and percentiles
- [x] `eval/spikes/test_uia_probe.py` — 32 tests; the spike suite is 56 tests, green
      (`python -m unittest discover -s eval/spikes -p "test_*.py"`). 11 of them walk fake
      nodes, so the deduplication #12 depends on is tested without UI Automation
- [x] State rebuilt and measured; raw results committed as `eval/spikes/uia-probe-keepass2.json`
      (the documented state) and `eval/spikes/uia-probe-keepass2-modal.json` (with a modal
      message box open, the run that reproduces the #6 per-element cost)
- [x] Note `eval/spikes/uia-walk-cost.md`: results, refuted hypotheses, cache answer, budget
- [x] PR #170 with `Closes #161`, reviewed by galip 2026-10-31 (changes requested)
- [x] 2026-11-01 — all three review points addressed: the pilot process is killed by image
      path and the demo database lives under `C:\ayna-pilots`; `uia_probe.run` deduplicates
      by handle with owner-first roots; every number re-measured and the note rewritten
- [ ] galip's re-review, then merge (it changes the #12 budget he depends on in `heal/` and
      the snapshot contract of #16). #169 merges first — this branch is stacked on it
- Next step: push, answer the review on #170, then take the budget into #12 and tell galip
  the snapshot duration is part of the document.

## Results (summary; the numbers and their tables are in the note)
- **The cause is a non-pumping application, and it reproduces.** With a modal message box
  open (KeePass's weak-password warning), a traversal-only walk of the main window took
  **230.05 s for 85 elements = 2.71 s per element**, against **2.63 s per element** in the
  #6 dump and 4.8–5.4 ms per element for the same traversal with no message box. The median element stayed at 1.4 ms:
  six containers (the dialog window 72.5 s, the main window 30 s, a ComboBox 24 s, the
  ToolBar 18 s, the entry List 12 s, a Pane 12 s) absorbed about 170 s of the 230 s.
- **The documented state alone does not reproduce it.** Same machine, same versions, same
  state: **114 elements in 2.1 s** (18.5 ms per element, 1.86–2.26 s over six runs) against
  106 elements in 278.5 s (2.63 s per element) — about 140× per element, and about the same
  factor in total now that the counts are comparable. Measured window by window: the `Add
  Entry` subtree is 40 elements in both runs, so the state matches; the main window's own
  tree is 74 against 66 then, the two sample entries this database has.
- **Cost centres**: traversal 7.2 ms per element (36 %), 17 plain properties 7.8 ms (39 %),
  10 pattern probes 4.5 ms (23 %), `LabeledBy` 0.9 ms (4 %). They are additive (2.32 s
  against 2.26 s measured).
- **Shape**: p50 13.0 ms, p90 29.7 ms, p99 59.2 ms, max 139.0 ms. The slowest elements are
  containers (the `m_tabEntry` pane, the window roots), not leaves, and they are already
  slow in `navigate`, so it is traversal cost.
- **Refuted**: pattern probes (23 %), WinForms being inherently slow (1.86–2.26 s over six
  runs), CPU contention (16 busy processes: +16 %, not two orders of magnitude), an open
  *menu* (1.55 s with the File menu open — a tracked menu still pumps; a message box does
  not). The contention and menu numbers are from 2026-10-31, before the deduplication fix;
  they are ratios between two runs of the same code, so the fix does not touch them.
- **Cache API: not needed.** `FindAllBuildCache` over the subtree is 2.28 s against 2.26 s
  (2.08/2.08 and 2.09/2.13 in two further runs), and all of it is inside the `FindAll` call.
- **Budget for #12**: default property set = plain properties + `LabeledBy`, no pattern probes
  (−23 % for nothing lost, leaving 15.3 ms per element); **5 000 ms per window** as a deadline
  checked between elements, not a per-element timeout — 2.2× the slowest measured walk and
  ~330 elements at that rate, against this pilot window's 114 — but enforced on a timer, because one container blocked for 72 s
  inside a single call; on expiry `SnapshotTimeout` (-32002) with no partial document, triaged
  as RS 0.6's *search incomplete*; every snapshot carries its own duration and element count,
  and a timeout reports how far it got and which element blocked it.

## Manual checks
- 2026-10-31 · hasan · rebuild the #6 state and measure · pass · evidence:
  `eval/spikes/uia-probe-keepass2.json`, tables quoted in `eval/spikes/uia-walk-cost.md`
- 2026-10-31 · hasan · stability and contention runs (3 idle, 2 under full CPU load, 3 with and
  without an open menu) · pass · numbers in the note's "What the 278.5 s was not"
- 2026-10-31 · hasan · traversal with a modal message box open · pass (reproduced the outlier:
  230.05 s / 85 elements) · evidence: `eval/spikes/uia-probe-keepass2-modal.json`

- 2026-11-01 · hasan · re-measure after the deduplication fix (3 all-mode runs, 3 further
  full/navigate runs, main window and dialog each alone) · pass · 114 elements with 1
  duplicate skipped in every run; `Add Entry` alone 40, main window alone 114 (74 + the
  nested dialog); evidence `eval/spikes/uia-probe-keepass2.json` and the note's tables
- 2026-11-01 · hasan · `kp_state.py` kills only the pilot KeePass · pass · the pilot started
  from `C:\ayna-pilots\keepass2\KeePass.exe` was found by image path (pid 2376) and killed,
  and `pilot_pids()` is empty for any other copy; `is_pilot_path` refuses
  `C:\Users\pc\OneDrive\Belgeler\Database.kdbx` and `C:\ayna-pilots\..\Users\pc\x.kdbx`
- 2026-11-01 · hasan · the demo database lands under `C:\ayna-pilots` · pass · after the Save
  As fix the wizard produced `C:\ayna-pilots\ayna-demo.kdbx` (title `ayna-demo.kdbx -
  KeePass`); the one file the old code had left in the user's OneDrive folder was deleted
  with the user's agreement
- 2026-11-01 · hasan · `kp_state.py entry --fresh` end to end, unattended · pass, after
  three failures that were the fix · the stalls were real but not where the docstring
  guessed: a click leaves KeePass's secure boxes unfocused, a classic message box blocks
  UIA so it has to be answered over Win32, the new-database *task dialog* must not be, and
  `STEP_TIMEOUT` was budgeting a step rather than the sequence. With all four addressed a
  cold run built `C:\ayna-pilots\ayna-demo.kdbx` and reached Add Entry unattended in about
  six minutes, nearly all of it inside one blocked UIA call; 16 s from an existing database

## Open issues
- The original outlier is explained by mechanism, not proven for that run: the dump's window
  list shows no message box, so either it was dismissed between `find_windows` and the walk,
  or the blocking loop was something else (a drag, a tracked menu, a dialog inside its own
  loop). It cannot be decided after the fact, because the dump recorded one total and no
  per-element timings. The fix is forward-looking: #12 records duration and element count per
  snapshot, and `uia_probe.py` exists for the next outlier.
- `kp_state.py` now completes the wizard unattended, but a cold `--fresh` run spends about
  six minutes of its 420 s budget inside one blocked UIA call. Making that fast needs what
  #12 needs anyway — a deadline on a timer around every UIA call — or driving the whole
  wizard over Win32. Good enough for #12 and #22 as it stands; not worth more of this
  issue's time.
- `uia_dump.find_windows` loses every window when one of them closes mid-enumeration
  (`UIA_E_ELEMENTNOTAVAILABLE` from `ElementFromHandle`). `kp_state.windows()` now swallows
  it, but the dump tool itself should skip the vanished window and keep the rest; #12 will
  need exactly that. Worth a small issue.
- `uia_dump.py` could take a `--timings` flag so a future dump is self-explaining. Out of
  scope here; worth an issue if #12 does not make it redundant.
- The spike suite still does not run in CI (`eval` job's `testpaths` is `apps/trial/tests`
  only, and `spikes/` is excluded from ruff). Raised in my review of PR #167; with
  `uia_probe.py` now carrying the measurement that #12's budget rests on, it matters more.

## Handoff
`eval/spikes/kp_state.py entry` prints the two window handles (run it with the demo
database already built — `--fresh` is the unreliable path); `uia_probe.py --handle …
--modes full,cached` is the one command that re-answers both the budget and the cache
question on any pilot app. Nothing in either script is KeePass-specific except `kp_state.py`.
If a count ever looks too high, read `duplicates_skipped` in the JSON before believing the
total.

## Outcome (fill when the issue closes)
