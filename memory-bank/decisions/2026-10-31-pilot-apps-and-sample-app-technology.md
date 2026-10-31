# D1: Sample app stays PySide6; pilots are KeePass 2 and HandBrake

- Date: 2026-10-31
- Status: Proposed (#21)
- Deciders: Galip, Ömerfaruk, Hasan
- Issues: #21 (this decision) · evidence from #6 and #9 · affects #33, #11, #12, #22, #23, #29, #46, #47, #64

## Context
D1 asks two questions the plan deliberately left to measurement: which UI technology the sample
app (#33) is built in, and which 2–3 open-source apps are the pilots for RQ1 (#64) and the
version-drift work (#22). The plan allowed a "WPF exception" if Qt's UIA tree turned out poor.

Both questions now have numbers:

- **#6** dumped the raw UIA tree of four portable apps on Windows 11 (DPI 120, pywinauto 0.6.9),
  with `read_errors: 0` and no truncated walk. Results, per-control-type tables, 7 findings and
  a recommendation are in [`eval/spikes/uia-dump.md`](../../eval/spikes/uia-dump.md), the dumps
  themselves in `eval/spikes/uia-dumps/`.
- **#9** built the one-screen PySide6 trial app and measured how Qt reaches UIA
  (`eval/apps/trial/`, findings in `learnings.md`).

Interactive elements only (the #6 definition: a fixed list of control types, window frame
excluded), so the shares are comparable across toolkits:

| App | Technology | Walk | Elements | id or Name | AutomationId | unique in window | Name |
|---|---|---|---|---|---|---|---|
| KeePass 2 2.61.1 | WinForms | 278.5 s | 106 | **98%** | 35% | 100% | 85% |
| HandBrake 1.11.2 | WPF | 1.97 s | 149 | **96%** | 73% | 100% | 71% |
| KeePassXC 2.8.0 | Qt Widgets | 0.47 s | 84 | **100%** | 100% | **10%** | 88% |
| Notepad++ 8.9.8.1 | Win32 | 1.04 s | 109 | **59%** | 29% | 100% | 57% |

## Decision

1. **The sample app (#33) is built in PySide6 (Qt Widgets). The WPF exception is not taken.**
2. **The pilots are KeePass 2 (WinForms) and HandBrake (WPF).** KeePassXC (Qt Widgets) is the
   third pilot, added only after the first two run end to end, and only if its locking
   behaviour can be switched off (see Consequences).
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
  list view. Long release history, so it is the subject for #22. It identifies by Name far more
  than by id (35% id), which makes it the app that will expose how brittle Name-first matching
  is — a reason to keep it, not to drop it.
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

The #6 note left one question open before D1: finding 7, the 278.5 s WinForms walk. It no longer
blocks this decision. The pattern-probe hypothesis was tested and refuted (probes cost 1.56 ms
per element against 2.79 ms for fifteen property reads), so the cost is tied to the window state
the dump captured, not to the WinForms bridge; it is now tracked as **#161** and bounds the
snapshot design (#12), not the choice of pilot. Were WinForms inherently unreadable, the pilot
set would have to change — that is the one result that can reopen this ADR.

## Consequences

- **#33 (sample app)**: PySide6. `objectName` is part of the app's public interface — the dotted
  AutomationId is a path, so renaming any ancestor renames every descendant id (#9). The sample
  app needs a naming convention, `accessibleName` set wherever a UIA Name is wanted (in Qt it
  replaces the Name, it does not add to it), and a test that fails when an interactive control
  has an empty or duplicated AutomationId.
- **#11 (descriptor)**: store the **full** AutomationId, never clipped — the 200-character clip
  is a dump artefact and 25 of KeePassXC's 84 elements exceed it (#6 finding 3). Keep the
  fallback properties the dumps show as populated; `LabeledBy` is confirmation for
  `nearestLabel`, not its primary source.
- **#12 / #161 (snapshot)**: KeePass 2 is the worst case, so the snapshot needs a bounded walk
  and a "snapshot incomplete" outcome regardless of what #161 finds; NFR-02's 2 s is scoped to
  the sample app, where Qt's 0.47 s baseline makes it reachable.
- **#22 / #46 / #47 / #64**: version drift and the RQ1 run use KeePass 2 and HandBrake; the
  dumped versions are the baseline (KeePass 2.61.1.0, HandBrake 1.11.2.0, KeePassXC 2.8.0.0,
  Notepad++ 8.9.8.1).
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
