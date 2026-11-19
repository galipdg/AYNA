# What a UIA walk costs, and what the 278.5 s was not (#161)

Follow-up to finding 7 of [`uia-dump.md`](uia-dump.md): the #6 dump measured a
property-complete UI Automation walk of one KeePass 2 (WinForms) window state at
**278.5 s for 106 elements** — 2.63 s per element, against 1.97 s *in total* for
HandBrake's 149 (WPF), 1.04 s for Notepad++'s 109 (Win32) and 0.47 s for KeePassXC's 84
(Qt). This note answers the three questions #161 asks: does it reproduce, what is the
time spent on, and what budget #12 can defend.

**Short answer: the state itself does not reproduce it, but one condition does.** The same
application in the same window state walks in **2.1 s for 114 elements** (18.5 ms per
element, 1.86–2.26 s over six runs) — about **140× faster per element** than the dumped
run, on the same machine, the same Python and the same pywinauto, and about the same factor
in total, because the element counts are comparable (114 here against the dump's 106). But
with **a modal message box open on top of the dialog**, a traversal of the main window that
normally costs 0.6 s took **230.05 s for 85 elements: 2.71 s per element, against the
dumped run's 2.63 s**. The cost of a WinForms walk is ordinary and stable until the
application stops pumping messages; then it collapses, and it collapses to exactly the
number #6 recorded.

## Method

`uia_probe.py` (new, next to `uia_tree_dump.py`) walks the same windows once per cost centre
and times every element on its own, so a total can be read together with its
distribution. Modes: `navigate` (traversal only), `properties` (the 17 plain properties
the dump reads), `patterns` (the 10 pattern-availability probes), `labeledby`
(`CurrentLabeledBy` plus the label's name), `full` (all of it: exactly what
`uia_tree_dump.py dump` does) and `cached` (one `FindAllBuildCache` over the subtree, then
every read from the cache).

The state was rebuilt to the one `uia-targets.json` describes: KeePass 2.61.1.0 portable,
a database open, the **Add Entry** dialog on top. It was driven with pywinauto rather than
by hand, through six dialogs: new-database notice → Save As → Create Master Key →
weak-password warning → Configure New Database → emergency-sheet prompt, then Ctrl+S and
Ctrl+I. `kp_state.py` encodes that sequence and now runs it unattended: 16 s from an
existing database, which is how the runs below were taken, and about six minutes for a cold
`--fresh` run that has to build the database — nearly all of it inside one UIA call that
blocks right after the weak-password box, which is this note's own subject seen from the
driver's side. Two deviations from the #6 state: the database here was saved, so its title
has no `*`, and it lives in the pilot folder as `ayna-demo.kdbx` rather than in the user's
Documents (#170 review: `--fresh` deletes that file, so it may not sit among a person's
own). The raw result committed here was captured just before that move, so its window title
still reads `Database.kdbx`; the tree it walked is the same one.

Element counts are deduplicated by window handle, the way `uia_tree_dump.walk` does it, and
the windows are walked owner-first. This matters for every number below: KeePass's `Add
Entry` is both a top-level window and a child of the main form, so the first version of
`uia_probe.py` walked its 40 elements twice — once as a root and once as a descendant —
and reported 154 "elements" for a tree of 114. The giveaway is in that run's slowest
table, which lists the same `m_tabEntry` pane twice (90.0 and 77.7 ms). The measurement
below was taken again after the fix (#170 review); the totals it replaces were inflated by
that second pass, while the per-element figures were *deflated* by it, because walking a
subtree whose containers have already been realised is cheaper than walking it cold.

Measured 2026-11-01 on `Windows-11-10.0.26300-SP0`, DPI 120 (125 % scaling), Python
3.13.0, pywinauto 0.6.9 — the same machine and versions as the #6 dump. Raw result:
[`uia-probe-keepass2.json`](uia-probe-keepass2.json), six further runs summarised in the
ranges below.

## Results

Both windows together (`Add Entry` + the main window), 114 elements — 74 of the main
window's own and the dialog's 40, each counted once:

| Mode | Elements | Total s | Mean ms | p50 ms | p90 ms | p99 ms | Max ms | Share of full |
|---|---|---|---|---|---|---|---|---|
| navigate | 114 | 0.82 | 7.21 | 1.70 | 9.91 | 52.65 | 123.64 | 36% |
| properties | 114 | 1.71 | 14.98 | 8.56 | 23.26 | 51.50 | 120.72 | 75% |
| patterns | 114 | 1.33 | 11.67 | 7.08 | 16.24 | 53.37 | 133.42 | 59% |
| labeledby | 114 | 0.92 | 8.09 | 2.30 | 13.35 | 53.00 | 151.42 | 41% |
| full | 114 | 2.26 | 19.84 | 12.99 | 29.74 | 59.19 | 138.96 | 100% |
| cached | 113 | 2.28 | 20.19 | — | — | — | — | 101% |

Across six runs of the same state in one session the full walk took 1.86–2.26 s
(16.3–19.8 ms per element) and the traversal-only walk 0.64–0.82 s, so a single run's total
is good to about ±10 %. Every number below is from the run in the table unless it says
otherwise.

Every mode includes the traversal, so the cost centres are the differences:

| Cost centre | Per element | Share of the full walk |
|---|---|---|
| traversal (asking for children) | 7.2 ms | 36% |
| 17 plain properties | 7.8 ms | 39% |
| 10 pattern probes | 4.5 ms | 23% |
| `LabeledBy` + the label's name | 0.9 ms | 4% |

They add up: 0.82 + 0.89 + 0.51 + 0.10 = 2.32 s against the 2.26 s measured directly, so
nothing hides between them. The walk makes roughly 30 cross-process calls per element,
which puts one call at about **0.66 ms**. The dumped run implies **88 ms per call** — not
a different amount of work, the same work waiting for something.

**The slowest elements are containers, not leaves.** The `m_tabEntry` pane of the `Add
Entry` dialog costs 139.0 ms, the two window roots 59.2 and 47.9 ms, then list and tree
items at 34–43 ms; the median element is 13.0 ms. A tab control that has to realise its
pages before it can answer about its children is the shape of this distribution, and it is
the same shape in every mode (`navigate` already has a p99 of 52.7 ms), so it is traversal
cost, not property cost.

## What the 278.5 s was not

| Hypothesis | Test | Result |
|---|---|---|
| The ten pattern probes (finding 7's suspect) | timed separately | **Refuted** before this note: 4.5 ms per element, 23 % of the walk. Even at ten times the cost they cannot make 278 s |
| The WinForms UIA bridge is inherently slow | full walk on the documented state | **Refuted**: 18.5 ms per element, 1.86–2.26 s over six runs |
| The machine was under CPU load | full walk with 16 busy processes on 16 logical CPUs | **Refuted**: +16 % (measured 2026-10-31 before the deduplication fix: 1.79 → 1.92 s; the ratio is what matters) — not two orders of magnitude |
| The provider was in a modal message loop (open menu) | full walk with the File menu open | **Refuted**: 1.55 s with the menu open against 1.65 s without, same run of 2026-10-31 |
| The state differed from the dumped one | element count per window, each window measured on its own | The `Add Entry` subtree is **40 elements in both** runs; the main window's own tree is **74** now against 66 then, the two sample entries this database has against the empty #6 one. Deduplicated totals: **114** against the dump's **106**. Comparable size, 140× less time |

## What does reproduce it: a modal message box

The hypotheses above were tested by making the application busy from the outside. The one
that works makes it busy from the inside: a **modal message box** (KeePass's
"the master password is weak", a Yes/No box owned by the *Create Master Key* dialog, which
is itself modal to the main window). While that box was open, `uia_probe.py --modes
navigate` over the main window — traversal only, not a single property read:

| Condition | Elements | Total | Per element | p50 | p90 | p99 / max |
|---|---|---|---|---|---|---|
| normal (navigate, main window alone) | 114 | 0.55–0.62 s | 4.8–5.4 ms | 1.6 ms | 10.0 ms | 46 / 131 ms |
| modal message box open (navigate, main window alone) | 85 | **230.05 s** | **2706 ms** | 1.4 ms | 9 059 ms | 72 509 ms |
| #6 dump (full walk, both windows) | 106 | 278.5 s | 2627 ms | — | — | — |

Both navigate rows are the main window as the only root, three runs for the normal one; the
modal run had a single root as well, so the deduplication fix does not change it. The
percentiles in the normal row are from the run of the results table above.

Two things in that table matter more than the totals.

**The per-element cost matches the #6 dump almost exactly** — 2.71 s against 2.63 s — which
is a strong hint that the dumped run was taken while KeePass was in a comparable
non-pumping state, even though the dump's window list shows no message box (it records only
what `find_windows` saw at the moment it started).

**The median element is still 1.4 ms.** The time is not spread over the tree; it sits in a
handful of containers whose child enumeration blocks:

| ms | Control | AutomationId | Depth |
|---|---|---|---|
| 72 509 | Window *Create Master Key* | `KeyCreationForm` | 1 |
| 30 162 | Window *KeePass* | `MainForm` | 0 |
| 24 114 | ComboBox | `1836666` | 2 |
| 18 322 | ToolBar | `m_toolMain` | 1 |
| 12 060 | List | `m_lvEntries` | 5 |
| 12 059 | Pane | `1311980` | 4 |

Six elements account for about 170 s of the 230 s. The provider answers the cheap questions
from its own cache and blocks on the ones that need its UI thread, which is sitting in the
message box's own loop. That is also why the pattern probes (finding 7's suspect) could
never have explained the dump: they are per-element property reads, and the per-element
property reads are the part that stayed fast.

What remains, in the order I would bet on, with what would decide each:

1. **The dumped run hit the same non-pumping state as the reproduction above** — a message
   box, a drag, a menu being tracked, or a dialog in the middle of its own modal loop. This
   is now the leading explanation, not a guess: the per-element cost matches to within 3 %.
   What it cannot explain by itself is why the dump's window list shows no third window;
   the box may have been dismissed between `find_windows` and the walk, or the blocking
   loop may have been something else that is not a window at all.
2. **Something outside both processes serialising cross-process COM calls** — an
   anti-malware real-time scanner, Windows Search, or OneDrive syncing while the database
   path sat under `OneDrive\Belgeler`. Decided by re-running the dump with the scanner's
   exclusion list changed; not something to hold #12 up for.
3. **An interactive-desktop condition** (a locked or screensaver-blanked session during
   the walk). Decided by re-measuring in that state; worth testing before #67 runs
   playback on a CI Windows runner, where the desktop state is not ours.

None of them changes the design of #12, and that is the point: the snapshot needs a
deadline and an "incomplete" outcome **whatever** the cause turns out to be. A window that
answers 150× slower than the measured norm is not a freak event — it is what a modal
message box does, and a test run meets those all the time.

## Does #12 need the UIA cache API? No

`FindAllBuildCache` over the subtree with 17 properties cached: **2.28 s**, against 2.26 s
for per-property reads — a 0.9 % difference, 2.08 against 2.08 s and 2.09 against 2.13 s in
the two further runs, and all of it inside the `FindAll` call (2.28 s of 2.28 s; reading the
cached values afterwards is free). The provider does the same work either way; batching
only moves where it is paid. The cache API costs an extra
code path and a second way to be wrong about staleness, so **#12 reads properties
directly**. Revisit only if a pilot window ever shows a wide gap between the two numbers —
`uia_probe.py --modes full,cached` answers that in one run.

## Budget for #12

From the measured per-element costs, for a snapshot that reads what the descriptor (#11)
needs — the plain properties and `LabeledBy`, **without** the pattern probes, which no
matching property uses:

| Framework | Measured | Per element (full walk) | Without the pattern probes | Elements inside 2 s |
|---|---|---|---|---|
| WinForms (KeePass 2) | this note, 114 elements in 2.26 s | ~19.8 ms | ~15.3 ms | ~130 |
| WPF (HandBrake) | #6 dump, 149 elements in 1.97 s | ~13 ms | ~10 ms (23 % less, as measured here) | ~200 |
| Win32 (Notepad++) | #6 dump, 109 in 1.04 s | ~9.5 ms | ~7.3 ms | ~270 |
| Qt (KeePassXC) | #6 dump, 84 in 0.47 s | ~5.6 ms | ~4.3 ms | ~460 |

Only the WinForms row is decomposed by measurement; the other three are scaled by the 23 %
the pattern probes cost here, which is the one number this note can lend them.

Recommendation for #12, and the numbers behind each part:

- **Default property set**: the 17 plain properties plus `LabeledBy`. Dropping the pattern
  probes saves 20 % of the walk and loses nothing the scorer or the step schema uses;
  `Spy` can ask for them on demand with a flag.
- **Default budget: 5 000 ms per window**, which is 2.2× the slowest full walk measured on
  a pilot window (2.26 s) and covers about **330 elements** at the WinForms descriptor rate
  of 15.3 ms — nearly three times the 114 this pilot window has. (The "3× the measured
  walk" of this note's first version came from the inflated total; the headroom that
  matters is in elements, not in seconds.) Not 2 s: NFR-02's 2 s is scoped to the *sample
  app* (Qt, ~4.3 ms per element without the probes), where 2 s covers roughly 460 elements
  — comfortable — while a WinForms pilot window of 200 elements would breach it through no
  fault of the agent.
- **The budget is a deadline, not a per-element timeout**: the walk checks the clock
  between elements and gives up as a whole, because the p99 element (78 ms) is 10× the
  median and a per-element limit would cut exactly the tab containers that matter. Under a
  modal message box a single container blocked for **72 s**, so the deadline has to be
  enforced on a timer, not only between elements — a walk that is inside one blocking
  `FindAll` cannot check a clock. Practically: run the walk on the UIA worker thread
  (`ayna-uia`, PR #135) and let the caller's deadline win.
- **A blocking modal is a first-class outcome, not an error**: when the deadline expires,
  the most likely cause is not a huge window but an application that is not pumping. The
  snapshot should say which, because "the app is showing a message box" is actionable for
  a tester and "snapshot timed out" is not. Cheap signal to record with the timeout: the
  number of elements reached and the handle of the element it was blocked on.
- **On expiry: `SnapshotTimeout` (-32002), no partial document**, as `docs/agent-rpc.md`
  already specifies, and the triage category is RS 0.6's **search incomplete** (FR-35),
  which never starts healing (FR-29).
- **Every snapshot carries its own duration and element count**, so the next outlier is
  attributable instead of being a single number nobody can decompose. That is the one
  change this investigation would have needed to be unnecessary.

## How to repeat this

```powershell
# bring KeePass into the dumped state (prints the window handles; see its docstring for
# the dialog sequence, and expect to confirm a dialog by hand if it stalls). The demo
# database is C:\ayna-pilots\ayna-demo.kdbx and --fresh deletes that file only
python eval/spikes/kp_state.py entry

# all six cost centres on those windows
python eval/spikes/uia_probe.py --process KeePass.exe --json eval/spikes/uia-probe-keepass2.json

# one cost centre, three times, for stability
python eval/spikes/uia_probe.py --process KeePass.exe --modes full --repeat 3
```

Tests (any OS): `python -m unittest discover -s eval/spikes -p "test_*.py"` — 56 tests,
32 of them for this script's percentiles, tables, mode selection, root ordering and the
deduplication of the walk itself (fake nodes, no UI Automation).
