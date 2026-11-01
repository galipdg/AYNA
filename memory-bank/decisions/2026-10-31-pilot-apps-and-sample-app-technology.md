# D1: Sample app stays PySide6; pilots are KeePass 2 and HandBrake

- Date: 2026-10-31
- Status: Proposed (#21)
- Deciders: Galip, Ömerfaruk, Hasan
- Issues: #21 (this decision) · evidence from #6, #9 and #161 · affects #11, #12, #23, #24, #29,
  #33, #42, #44, #46, #47, #64, #76

## Context
D1 asks two questions the plan deliberately left to measurement: which UI technology the sample
app (#33) is built in, and which 2–3 open-source apps are the pilots for RQ1 (#64) and for
repeatable playback on a toolkit we did not write (SC-06, SC-07, SC-23). The plan allowed a
"WPF exception" if Qt's UIA tree turned out poor.

Both questions now have numbers:

- **#6** dumped the raw UIA tree of four portable apps on Windows 11 (DPI 120, pywinauto 0.6.9),
  with `read_errors: 0` and no truncated walk. Results, per-control-type tables, 7 findings and
  a recommendation are in [`eval/spikes/uia-dump.md`](../../eval/spikes/uia-dump.md), the dumps
  themselves in `eval/spikes/uia-dumps/`.
- **#9** built the one-screen PySide6 trial app and measured how Qt reaches UIA
  (`eval/apps/trial/`, findings in `learnings.md`).

Interactive elements only (the #6 definition: a fixed list of control types, window frame
excluded), so the shares are comparable across toolkits:

| App | Technology | Walk | Elements walked | Interactive | id or Name | AutomationId | unique in window | Name |
|---|---|---|---|---|---|---|---|---|
| KeePass 2 2.61.1 | WinForms | 278.5 s | 106 | 54 | **98%** | 35% | 100% | 85% |
| HandBrake 1.11.2 | WPF | 1.97 s | 149 | 45 | **96%** | 73% | 100% | 71% |
| KeePassXC 2.8.0 | Qt Widgets | 0.47 s | 84 | 41 | **100%** | 100% | **10%** | 88% |
| Notepad++ 8.9.8.1 | Win32 | 1.04 s | 109 | 79 | **59%** | 29% | 100% | 57% |

*Elements walked* and *Walk* are the whole tree the dump visited; every share after
*Interactive* is of the interactive subset, and *unique in window* is a share of the
interactive elements that have an AutomationId.

## Decision

1. **The sample app (#33) is built in PySide6 (Qt Widgets). The WPF exception is not taken.**
2. **The pilots are KeePass 2 (WinForms) and HandBrake (WPF)** — in the RS's codes (TBD-1),
   **P1 = HandBrake** and **P2 = KeePass 2**. KeePassXC (Qt Widgets) is the third pilot, added
   only after the first two run end to end, and only if its locking behaviour can be switched
   off (see Consequences).
3. **Notepad++ is not a pilot.** It stays the fixture for the win32 fallback trial (#23).

### Why PySide6 survives the WPF exception
KeePassXC is the weakest app in the set on one property only: **id uniqueness, 10%**. The cause
is not Qt's UIA bridge but unnamed widgets — Qt builds the AutomationId from the `objectName`
chain, and a widget without an `objectName` falls back to its class name, so sibling
`QPushButton`s collide (#6, finding 3). In an app we write, `objectName` is ours to set. Measured
again today on the trial app (`python eval/apps/trial/uia_dump.py`): every app-owned control has
a **unique** dotted AutomationId (8/8, e.g. `QApplication.loginWindow.usernameInput`); the only
elements without one are the window frame's TitleBar and its Minimize/Maximize/Close buttons,
which carry no id in any toolkit (#9) and are excluded from the #6 interactive set.

Two more points favour Qt for our own app: it was the **fastest walk** in the set (0.47 s for 84
elements, against 1.97 s for WPF and 278.5 s for WinForms), which is the budget NFR-02 has to fit
(2 s per sample-app window); and it is the **only** toolkit in the set that populates `LabeledBy`
(12% of KeePassXC's interactive elements, #6 finding 6), which gives the descriptor's
`nearestLabel` a second source to check itself against.

WPF was not chosen because the stack is Python end to end (agent, AI service, eval), adding .NET
to the deliverable buys nothing a pilot does not already give us — HandBrake covers WPF as a
pilot — and dropping Qt from the sample app would leave the toolkit of our own product untested.

### Why these pilots
Against the five criteria of the #6 note (C1 id-or-Name ≥ 90%, C2 form-heavy, C3 different
technology, C4 free licence / portable / many releases, C5 deterministic start):

- **KeePass 2** — highest `id or Name` share (98%) and the screens closest to the reference
  scenarios (#34): modal entry editor with required fields, tabbed options dialog, tree beside a
  list view. It identifies by Name far more than by id (35% id), which makes it the app that
  will expose how brittle Name-first matching is — a reason to keep it, not to drop it. Its long
  release history is a bonus for reading real UI-change patterns into #46, not an issue of its
  own: no semester-1 issue upgrades a pilot.
- **HandBrake** — the cleanest identification in the set: 73% AutomationId, none generated, all
  unique in their window, 2 s walk. Tabs, combo boxes and number fields map onto the wizard and
  settings scenarios. Pairing it with KeePass 2 keeps the measurement honest: one app where
  "AutomationId is the primary property" looks best, one where it barely applies.
- **KeePassXC, third** — the only app in the set where ids exist but are not unique, the case
  recognition is most likely to get wrong, and the only `LabeledBy` source. Costs: it duplicates
  KeePass 2's domain and it locks its database on inactivity and on workstation lock, discarding
  any open form (`learnings.md`).
- **Notepad++, not a pilot** — fails C1 by a wide margin (59%) and its main surface is a
  Scintilla editor UIA does not expose as controls at all, so RQ1 against it would measure a
  target the technology cannot reach. Its 32 anonymous toolbar buttons are exactly what #23 needs.

**Which pilot is P1 and which is P2**, because the RS asks different things of them. SC-07 needs
P2 to hold a control for which UIA gives neither an AutomationId nor a Name, and the dumps show
only one app has a *usable* one: KeePass 2's single such interactive control is the main toolbar's
quick-search **ComboBox**, a real 160×28 px control a test would want to type into (1/54
interactive elements, measured in `keepass2.json`). HandBrake's two (2/45) are a Button with
zero-size bounds and a menu item — nothing a scenario can act on. So **P2 = KeePass 2** and
**P1 = HandBrake**, which also satisfies SC-06's only requirement of P1 (a pilot not built with
Qt). SC-23 runs on both and does not care which is which.

The #6 note left one question open before D1: finding 7, the 278.5 s WinForms walk. **#161 has
since answered it, and the answer does not reopen this ADR.** The window state the dump describes
is not the cause: rebuilt and re-walked, the same two KeePass 2 windows are **114 elements in
1.86–2.26 s over six runs** (about 18.5 ms per element, 140× faster per element than the dumped
run). What does reproduce the outlier is a **modal message box** open on top of the dialog: with
one, a traversal of the main window that normally costs 0.6 s took **230.05 s for 85 elements**,
2.71 s per element against the dumped run's 2.63 s. The provider answers from its own cache until
a question needs its UI thread, which is sitting in the box's message loop; the median element is
still 1.4 ms and six containers account for 170 s of the 230 s. The pattern-probe hypothesis was
refuted separately (10 probes cost 4.5 ms per element, 23% of the walk).

So **the reopening condition did not trigger**: WinForms is not inherently unreadable, and the
pilot set stands. #161 bounds the snapshot design (#12) instead — a deadline and an "incomplete"
outcome are needed because any app can show a modal box, not because of WinForms. Numbers and
method in `eval/spikes/uia-walk-cost.md` (#170).

## Consequences

- **#33 (sample app)**: PySide6. `objectName` is part of the app's public interface — the dotted
  AutomationId is a path, so renaming any ancestor renames every descendant id (#9). The sample
  app needs a naming convention and `accessibleName` set wherever a UIA Name is wanted (in Qt it
  replaces the Name, it does not add to it).
- **#33's uniqueness test must exclude item-view children.** A test that simply fails when an
  interactive control has an empty or duplicated AutomationId would fail on the results grid:
  Qt gives an item view's children no `objectName` of their own, so every row, cell and list
  item carries its **container's** AutomationId. Measured both ways — each of KeePassXC's four
  `QListWidget` ListItems repeats its List parent's id (`keepassxc.json`), and #150 measured the
  same for every cell of a Qt table. So the test covers interactive controls **except**
  ListItem, DataItem and TreeItem, which are addressed by Name or, from step schema v0.2, by
  row and cell.
- **#11 (descriptor)**: store the **full** AutomationId, never clipped — the 200-character clip
  is a dump artefact and 25 of KeePassXC's 84 elements exceed it (#6 finding 3). Keep the
  fallback properties the dumps show as populated; `LabeledBy` is confirmation for
  `nearestLabel`, not its primary source.
- **#12 / #161 (snapshot)**: KeePass 2 is the worst case, so the snapshot needs a bounded walk
  and a "snapshot incomplete" outcome — #161 found the cause to be a modal message box, which no
  app is free of, so the deadline is not WinForms-specific. NFR-02's 2 s is scoped to the sample
  app, where Qt's 0.47 s baseline makes it reachable. **This reaches the client too**: the Spy
  (#24) and playback (#44) will see `-32002` Snapshot timeout on KeePass 2 windows, so "snapshot
  incomplete" is a UI state to design, not only an agent outcome.
- **#64 (RQ1)**: runs on KeePass 2 and HandBrake; the dumped versions are the baseline
  (KeePass 2.61.1.0, HandBrake 1.11.2.0, KeePassXC 2.8.0.0, Notepad++ 8.9.8.1), and a pilot is
  re-dumped before RQ1 if its version changes.
- **#46 / #47 (UI change and bug injection)**: these are versions of **our sample app**, not of
  the pilots, so #42 and RQ4 (#76) measure healing against controlled Qt changes. The pilots
  contribute their real release history as a *source* of realistic change patterns for #46; no
  semester-1 issue drives a pilot upgrade, so nothing here is blocked on KeePass 2's release
  cadence.
- **Installation**: portable builds in `C:\ayna-pilots\`, sources under `source` in
  `eval/spikes/uia-targets.json`, versions pinned as above. HandBrake needs the .NET 8 Desktop
  Runtime.
- **Before KeePassXC is promoted to pilot 3**: verify Galip's lead that Settings → Security can
  switch off "lock after inactivity" and "lock when the session is locked", and that the
  portable build keeps that setting in the config file next to the exe. If it holds, the only
  cost left is the domain overlap with KeePass 2.

## Alternatives considered
- **WPF sample app** (the plan's exception): rejected — Qt's measured weakness is id uniqueness
  in *other people's* apps, which does not apply to one we name ourselves; the stack is Python;
  HandBrake already covers WPF.
- **Qt sample app plus KeePassXC as the only pilot**: rejected — no technology diversity, and
  RQ1 would measure one bridge.
- **Notepad++ as a third pilot**: rejected on C1 (59%) and on Scintilla being invisible to UIA.
- **All four as pilots**: rejected on schedule; three pilot apps already stretch Week 9 (#64).
