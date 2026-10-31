# #161 Root-cause the WinForms snapshot outlier from #6

- Issue: https://github.com/galipdg/AYNA/issues/161
- Owner: hasan · Branch: `hasan/161-winforms-walk`
- Started: 2026-10-31 · Last update: 2026-10-31

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
- 2026-10-31 — The database keeps KeePass's default path and name (`Database.kdbx` under the
  user's Documents), because that is what the #6 dump's window title shows. One deviation
  from #6: this run saves the file, so the title has no `*`. It changes no element.
- 2026-10-31 — Measurement, not rescue: the point of #161 is a defensible budget for #12, so
  the note ends with a budget and a default property set. The mechanism found on the way (a
  modal message box) changes the budget's shape — a deadline enforced on a timer rather than
  between elements — but not the decision to have one.

## Status
- [x] `eval/spikes/uia_probe.py` with six cost centres, per-element timings and percentiles
- [x] `eval/spikes/test_uia_probe.py` — 21 tests; the spike suite is 45 tests, green on
      Windows (`python -m unittest discover -s eval/spikes -p "test_*.py"`)
- [x] State rebuilt and measured; raw results committed as `eval/spikes/uia-probe-keepass2.json`
      (the documented state) and `eval/spikes/uia-probe-keepass2-modal.json` (with a modal
      message box open, the run that reproduces the #6 per-element cost)
- [x] Note `eval/spikes/uia-walk-cost.md`: results, refuted hypotheses, cache answer, budget
- [ ] PR with `Closes #161`, review from galip (it changes the #12 budget he depends on in
      `heal/` and the snapshot contract of #16)
- Next step: open the PR; then take the budget into #12 and tell galip the snapshot duration
  is part of the document.

## Results (summary; the numbers and their tables are in the note)
- **The cause is a non-pumping application, and it reproduces.** With a modal message box
  open (KeePass's weak-password warning), a traversal-only walk of the main window took
  **230.05 s for 85 elements = 2.71 s per element**, against **2.63 s per element** in the
  #6 dump and 14 ms per element with no message box. The median element stayed at 1.4 ms:
  six containers (the dialog window 72.5 s, the main window 30 s, a ComboBox 24 s, the
  ToolBar 18 s, the entry List 12 s, a Pane 12 s) absorbed about 170 s of the 230 s.
- **The documented state alone does not reproduce it.** Same machine, same versions, same state: 154 elements
  in **1.79 s** (11.6 ms per element) against 106 elements in 278.5 s (2.63 s per element).
  The `Add Entry` subtree is 40 elements in both runs, so the state matches; the main window
  has more elements now (114 against 66) because this database has KeePass's sample entries.
- **Cost centres**: traversal 4.5 ms per element (39 %), 17 plain properties 4.6 ms (40 %),
  10 pattern probes 2.3 ms (20 %), `LabeledBy` 0.5 ms (4 %). They are additive.
- **Shape**: p50 7.3 ms, p90 17.4 ms, p99 77.7 ms, max 90.0 ms. The slowest elements are
  containers (the two `m_tabEntry` panes, the window roots), not leaves, and they are already
  slow in `navigate`, so it is traversal cost.
- **Refuted**: pattern probes (20 %), WinForms being inherently slow (stable 1.63/1.66/1.65 s),
  CPU contention (16 busy processes: +16 %, not 155×), an open *menu* (1.55 s with the File
  menu open — a tracked menu still pumps; a message box does not).
- **Cache API: not needed.** `FindAllBuildCache` over the subtree is 1.78 s against 1.79 s,
  and all of it is inside the `FindAll` call.
- **Budget for #12**: default property set = plain properties + `LabeledBy`, no pattern probes
  (−20 % for nothing lost); **5 000 ms per window** as a deadline checked between elements, not
  a per-element timeout — but enforced on a timer, because one container blocked for 72 s
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

## Open issues
- The original outlier is explained by mechanism, not proven for that run: the dump's window
  list shows no message box, so either it was dismissed between `find_windows` and the walk,
  or the blocking loop was something else (a drag, a tracked menu, a dialog inside its own
  loop). It cannot be decided after the fact, because the dump recorded one total and no
  per-element timings. The fix is forward-looking: #12 records duration and element count per
  snapshot, and `uia_probe.py` exists for the next outlier.
- `kp_state.py` does not yet complete the wizard unattended: after the Save As dialog closes,
  its controls stay in the main form's UIA tree and a pass can answer the wrong dialog. The
  fix is a liveness check on a control before pressing it. Worth finishing when #12 or #22
  needs the state repeatedly; not worth more of this issue's time.
- `uia_dump.py` could take a `--timings` flag so a future dump is self-explaining. Out of
  scope here; worth an issue if #12 does not make it redundant.
- The spike suite still does not run in CI (`eval` job's `testpaths` is `apps/trial/tests`
  only, and `spikes/` is excluded from ruff). Raised in my review of PR #167; with
  `uia_probe.py` now carrying the measurement that #12's budget rests on, it matters more.

## Handoff
`eval/spikes/kp_state.py entry` prints the two window handles; `uia_probe.py --handle …
--modes full,cached` is the one command that re-answers both the budget and the cache
question on any pilot app. Nothing in either script is KeePass-specific except `kp_state.py`.

## Outcome (fill when the issue closes)
