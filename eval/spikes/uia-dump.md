# UIA tree dump of candidate pilot apps (#6)

Spike, started 2026-10-25, galip. Question: which open-source Windows apps expose enough identifying information through UI Automation to be AYNA's pilot apps, and how do WinForms, WPF, Qt and Win32 compare?

**Status: done.** The four dumps were taken on hasan's Windows machine on 2026-10-27; `keepassxc` was re-taken on 2026-10-29 on the entry form, because the first run had caught it on its unlock screen. All four are committed in [`uia-dumps/`](uia-dumps/). *Results*, *Findings* and *Recommendation* below come from them. The expectations were written before the run; each one is marked confirmed or refuted at the end of *Findings*.

## Method

- [`uia_dump.py`](uia_dump.py) `dump` finds every visible top-level window of a target process with pywinauto's `uia` backend and walks the raw view (pywinauto's `children()` with no filter uses a TrueCondition) depth-first, up to 20 000 elements and depth 64. It writes `uia-dumps/<id>.json`: a header with app, exe file version, Windows and pywinauto version, window DPI and walk time, then a flat element list with parent links, one element per line.
- Per element it records: control type, AutomationId, Name, ClassName, FrameworkId, localized control type, HelpText, AccessKey, AcceleratorKey, the Name of the LabeledBy element, enabled, offscreen, keyboard-focusable, password, control/content element, whether it has its own HWND, bounds and ten pattern-availability flags (Invoke, Value, Toggle, SelectionItem, ExpandCollapse, RangeValue, Text, Scroll, Window, LegacyIAccessible).
- Privacy: Value-pattern contents are never read, strings are cut at 200 characters, only the exe file name is kept (not its path), and the apps run on throwaway demo data.
- [`uia_dump.py`](uia_dump.py) `stats` (any OS) prints the tables below. **Interactive** means one of these control types: Button, CheckBox, ComboBox, DataItem, Document, Edit, Hyperlink, ListItem, MenuItem, RadioButton, Slider, Spinner, SplitButton, TabItem, TreeItem. Containers and labels (Text) are left out because tests address their items and the controls they label. Elements inside a window's TitleBar (system menu, minimise/maximise/close) are left out too: they belong to the Windows frame and never have an AutomationId (measured in #9). AutomationId and Name count only when they are not blank. Two extra columns describe the AutomationIds: the share that look **generated** (only digits, like Win32 control ids, or a GUID) and the share that are **unique in their window**.
- Targets and the window state to prepare are listed in [`uia-targets.json`](uia-targets.json).

## Candidates

| id | App | Technology | Why it is a candidate |
|---|---|---|---|
| `keepass2` | KeePass 2 | WinForms (.NET Framework) | Form-heavy dialogs (entry editor, options), menus, list views; portable ZIP; long release history |
| `handbrake` | HandBrake | WPF (.NET 8) | Tabs, combo boxes, text and number fields; portable ZIP |
| `keepassxc` | KeePassXC | Qt Widgets | Same domain as KeePass 2 on another stack; entry form, wizards; portable ZIP. Its tree also hints at how good Qt is for the PySide6 sample app (#21) |
| `notepadpp` | Notepad++ | Win32 + Scintilla | Extra: classic Win32 dialogs; input for the win32 fallback trial (#23) |

All four are GPL-licensed, free and run without network access.

## Expectations (written before the run)

These are hypotheses, not results:

1. **WinForms** gives most designer-placed controls an AutomationId equal to the control's `Name` field. ToolStrip and menu items are not separate windows and may have an empty AutomationId and only a Name.
2. **WPF** gives an AutomationId only where the XAML sets `x:Name` or `AutomationProperties.AutomationId`, so the share depends on the app. Template parts (scroll bars, thumbs) add many non-interactive elements.
3. **Qt Widgets** builds AutomationIds from `objectName`s, so the share depends on whether the app names its widgets (`.ui` files usually do). Unnamed widgets may show up as `Custom` or `Pane`. (#9 has since measured on the PySide6 trial app that the id is the dotted path over the object chain, e.g. `QApplication.loginWindow.usernameInput`, and that `accessibleName` replaces the Name; see `memory-bank/learnings.md`.)
4. **Win32** AutomationIds are numeric dialog-control ids: present and unique within a dialog, but *generated*. Names of edit fields come from the label in front of them.

## Results

Measured on hasan's Windows machine, `Windows-11-10.0.26300-SP0`, DPI 120 (125% scaling),
Python 3.13.0, pywinauto 0.6.9 (the pinned version). `read_errors: 0` and `truncated: false`
for every target, so no number below is the result of a failed read or a cut-off walk. The
repo `.venv` was used instead of a throwaway `%TEMP%` venv -- same pywinauto, one step less.

Output of `python eval/spikes/uia_dump.py stats`:

| Dump | App | Technology | Version | Walk | Elements | Interactive | AutomationId | … generated | … unique in window | Name | AutomationId or Name |
|---|---|---|---|---|---|---|---|---|---|---|---|
| handbrake | HandBrake | WPF | 1.11.2.0 | 1.97 s | 149 | 45 | 73% (33/45) | 0% (0/33) | 100% (33/33) | 71% (32/45) | 96% (43/45) |
| keepass2 | KeePass 2 | WinForms | 2.61.1.0 | 278.5 s | 106 | 54 | 35% (19/54) | 11% (2/19) | 100% (19/19) | 85% (46/54) | 98% (53/54) |
| keepassxc | KeePassXC | Qt Widgets | 2.8.0.0 | 0.47 s | 84 | 41 | 100% (41/41) | 0% (0/41) | 10% (4/41) | 88% (36/41) | 100% (41/41) |
| notepadpp | Notepad++ | Win32 | 8.9.8.1 | 1.04 s | 109 | 79 | 29% (23/79) | 96% (22/23) | 100% (23/23) | 57% (45/79) | 59% (47/79) |

Interactive = control types Button, CheckBox, ComboBox, DataItem, Document, Edit, Hyperlink, ListItem, MenuItem, RadioButton, Slider, Spinner, SplitButton, TabItem, TreeItem, outside the window frame (TitleBar). AutomationId and Name count when non-blank. *… generated* (numeric or GUID) and *… unique in window* are shares of the interactive elements that have an AutomationId.

The same interactive sets, for the properties the descriptor of #11 might fall back on:

| Dump | LabeledBy | HelpText | AccessKey | AcceleratorKey | own HWND | neither id nor Name |
|---|---|---|---|---|---|---|
| handbrake | 0% (0/45) | 38% (17/45) | 13% (6/45) | 0% (0/45) | 0% (0/45) | 4% (2/45) |
| keepass2 | 0% (0/54) | 4% (2/54) | 31% (17/54) | 0% (0/54) | 35% (19/54) | 2% (1/54) |
| keepassxc | 12% (5/41) | 0% (0/41) | 27% (11/41) | 0% (0/41) | 0% (0/41) | 0% (0/41) |
| notepadpp | 0% (0/79) | 0% (0/79) | 39% (31/79) | 0% (0/79) | 28% (22/79) | 41% (32/79) |

The windows each number was measured on, so the counts can be read in context:

| Dump | Windows walked | Walk | Elements |
|---|---|---|---|
| handbrake | `HandBrake` | 1.97 s | 149 |
| keepass2 | `Add Entry`; `Database.kdbx* - KeePass` | 278.5 s | 106 |
| keepassxc | `Passwords - KeePassXC` | 0.47 s | 84 |
| notepadpp | `Find`; `new 1 - Notepad++` | 1.04 s | 109 |

Per-control-type tables come from `uia_dump.py stats --by-type`; the rows that carry a
finding are quoted below.

## Findings

**1. Three of the four apps clear the 90% bar; Win32 does not.** `AutomationId or Name` is
96% (HandBrake), 98% (KeePass 2) and 100% (KeePassXC) against 59% for Notepad++. RQ1's
"at least 90% for standard controls" is therefore reachable on managed and Qt toolkits with
UIA alone, and out of reach on a classic Win32 app without a second channel.

**2. Notepad++'s gap is one control group, not a spread.** 32 of its 79 interactive elements
have neither an AutomationId nor a Name, and **all 32 sit in the main toolbar**
(`ToolbarWindow32` inside `ReBarWindow32`): 31 `Button`s and one `SplitButton`, each with an
empty ClassName, an empty HelpText and nothing but a 27x26 px rectangle. Excluding the toolbar,
every remaining interactive element has an id or a Name -- 100% (47/47). So Notepad++ is not
"badly instrumented"; it has one blind spot, and that spot is exactly the input #23 (win32
fallback) needs. It also says what the fallback cannot do: there is no text to key on, so it
has to use the toolbar button index or the position.

**3. An AutomationId is not the same as a locator.** KeePassXC reports an AutomationId for
100% of its interactive elements, but only **10% (4/41) are unique inside their window**. Qt
builds the id as the dotted path of `objectName`s, and a widget without an `objectName`
contributes its class name instead, so whole groups collide:

```
14x  Application.MainWindow.toolBar.QToolButton
 6x  Application.MainWindow.menubar.QAction
 5x  Application.MainWindow.toolBar.QToolBarSeparator
 5x  ...DatabaseWidget.editEntryWidget.categoryList.categoryList
 2x  ...DatabaseWidget.editEntryWidget.buttonBox.QPushButton
```

Two further problems with the same scheme. The path grows with nesting depth: **25 of the 84
elements have an id longer than the dump's 200-character clip**, and the clipped prefixes form
5 groups covering 23 elements that cannot be told apart at all. The password box is the
clearest case -- the `Edit` that actually holds the password and the `Group` that wraps it
share a clipped id, so parent and child are indistinguishable. And any widget inserted above an
element rewrites its id. For #11 and #21 a Qt AutomationId has to be treated as a *weak*
property -- present, but neither unique nor stable -- while in WPF and WinForms every id that
exists is unique in its window (100% for both).

**4. WinForms identifies by Name, WPF by AutomationId.** KeePass 2: AutomationId 35%, Name
85%. HandBrake: AutomationId 73%, Name 71%. The split is visible per control type: every
KeePass 2 `Edit` and `CheckBox` has an id (8/8, 3/3) because WinForms derives it from the
designer's `Name` field, but its 23 `Button`s reach only 26% and its 9 `MenuItem`s and 7
`TreeItem`s 0% -- ToolStrip and menu items are not windows and expose text only. In HandBrake
the `ComboBox`es, `Edit`s, `CheckBox`es, `TabItem`s and `Hyperlink`s are all at 100% id, while
its `ComboBox`es, `Edit`s and `Hyperlink`s have no Name at all (0/6, 0/2, 0/3). A descriptor
that insists on one property for everything will fail on one of the two stacks: the primary
key has to be "AutomationId if present, else Name", with the technology recorded.

**5. Generated ids are a Win32 problem only.** 96% (22/23) of Notepad++'s AutomationIds are
numeric Win32 control ids. KeePass 2 has 2 numeric ones out of 19; HandBrake and KeePassXC have
none. Numeric ids are unique in their dialog (100% in all three apps that have any), so they
work as a secondary property, but they carry no meaning for the user and they are the ids most
likely to be renumbered between releases -- worth re-checking in the version-drift experiments
(#22).

**6. `LabeledBy` is populated only by Qt, and only on form rows.** 5 of 219 interactive
elements across the four apps (2%) have one, and **all five are in KeePassXC** (12% of its 41):
the Title, Username, Notes, URL and expiry controls of the entry form, labelled `Title:`,
`Username:`, `Notes:`, `URL:` and `Expires:`. WinForms, WPF and Win32 are at 0% over 178
interactive elements. The reader takes the property from the raw
`IUIAutomationElement.CurrentLabeledBy` and `read_errors` is 0, so those zeros are an absence,
not a read failure: neither KeePass 2, HandBrake nor Notepad++ sets
`AutomationProperties.LabeledBy`, while Qt derives it from the `QFormLayout` buddy label.

Two caveats before #11 counts on the Qt case. The property hangs off the **row container, not
the editable control**: the password row's `Group` carries `LabeledBy = "Password:"` while the
`Edit` inside it -- the one with `IsPassword` -- has no Name and no `LabeledBy`, so a
descriptor has to climb to the parent to find the label. And two elements outside the
interactive set (the password and tags `Group`s) carry one, which is why the dump holds 7
`LabeledBy` values where the table counts 5.

**So #11 still cannot rely on `LabeledBy` for `nearest_label`**: it has to find the label
geometrically (nearest `Text` to the left or above, inside the same container) and may use
`LabeledBy`, including the parent's, as a cheap confirmation where it exists. The same absence
holds for `AcceleratorKey`, 0% everywhere; `AccessKey` is populated for 13-39% (the `&`
mnemonics) and `HelpText` only in HandBrake (38%, its tooltips).

**7. A full walk is far from the 2 s target on WinForms.** HandBrake 1.97 s for 149 elements
and Notepad++ 1.04 s for 109, but **KeePass 2 took 278.5 s for 106 elements** -- about 2.6 s
per element, two orders of magnitude slower than WPF. `read_errors` is 0, so nothing timed out
and was swallowed; the cost is in the reads themselves. The suspect is the ten pattern probes
per element over the WinForms COM bridge, but that is a hypothesis: it was not isolated with
`--no-patterns` on the same window state. **#12 (snapshot export) cannot assume a
property-complete walk fits NFR-02's 2 s**, and should measure a WinForms window with and
without pattern probes before deciding what a snapshot reads.

**8. UIA covers the whole tree; win32 does not.** `NativeWindowHandle` is 0% in HandBrake and
KeePassXC -- WPF and Qt draw their controls, so none of them is a window. It is 35% in
KeePass 2 and 28% in Notepad++. A win32 fallback (#23) can therefore only ever see part of a
tree, and nothing at all on WPF or Qt: a supplement for Win32 dialogs, not a second
recognition engine.

**9. Non-interactive elements are a third to three quarters of every tree.** HandBrake 104/149
(76 of them `Text` labels), KeePass 2 52/106, KeePassXC 43/84 (20 `Group`s), Notepad++ 30/109.
The `Text` elements are worth keeping in a snapshot even though no step targets them:
HandBrake names 91% of them (69/76), and that is the material finding 6's geometric label
search needs.

### Verdicts on the pre-run expectations

1. **Partly refuted.** WinForms gives an AutomationId where the control is a window with a
   designer `Name` -- `Edit` 8/8, `CheckBox` 3/3, `Pane` 9/9 -- but only 35% of interactive
   elements overall, because `Button` (26%), `MenuItem` (0%), `TabItem` (0%) and `TreeItem`
   (0%) mostly do not get one. The second half of the expectation is **confirmed**: ToolStrip
   and menu items carry a Name (100%) and no id.
2. **Confirmed.** HandBrake's 73% is exactly the "depends on the app" case: the controls the
   XAML names are at 100% (`ComboBox`, `Edit`, `CheckBox`, `TabItem`, `Hyperlink`), the ones it
   does not are at 45% (`Button`) and 29% (`MenuItem`). Template parts do inflate the tree:
   76 of 149 elements are `Text`, plus `Image`, `Separator` and `Thumb`.
3. **Confirmed on the mechanism, refuted on the conclusion.** The id is the dotted `objectName`
   path #9 described, and KeePassXC names enough widgets that *every* interactive element has
   one -- but the unnamed ones fall back to their class name, so the ids collide (10% unique)
   and 25 of the 84 exceed the 200-character clip. "The share depends on whether the app names
   its widgets" turned out to be the wrong question; uniqueness is the real one. Unnamed
   widgets do show up as `Custom` (1) and `Pane` (4), as expected.
4. **Confirmed.** Notepad++'s ids are numeric (96% generated) and unique in their dialog
   (100%). Edit-field Names come from the preceding label -- the Find dialog's `Edit` is named
   `Find what :`. Not foreseen: the toolbar, where 30 buttons have neither id nor Name
   (finding 2).

## Recommendation

**Pilots: KeePass 2 (WinForms) and HandBrake (WPF); KeePassXC (Qt Widgets) as the third if the
schedule allows. Notepad++ is not a pilot** -- it stays as the fixture for the win32 fallback
(#23).

| App | C1 id-or-Name >= 90% | C2 form-heavy | C3 technology | C4 licence / portable / versions | C5 deterministic start |
|---|---|---|---|---|---|
| KeePass 2 | 98% yes | entry editor, options, tree + list | WinForms | GPL-2, portable ZIP, releases back to 2.0 | yes, once the update check is off |
| HandBrake | 96% yes | tabs, combo boxes, number fields | WPF | GPL-2, portable ZIP, many releases | yes, main window with no source |
| KeePassXC | 100% yes, but 10% unique ids | entry form, wizards | Qt Widgets | GPL-2/3, portable ZIP | no -- locks itself (see below) |
| Notepad++ | 59% **no** | dialogs, but editor-centred | Win32 | GPL-3, portable ZIP | yes |

- **KeePass 2** -- the highest `id or Name` share (98%) and the screens closest to the
  reference scenarios (#34): a modal entry editor with required fields, a tabbed options
  dialog, a tree beside a list view. Its long release history makes it the best subject for the
  version-drift experiments (#22). Two caveats to carry into #11 and #12: it identifies by Name
  far more than by id (35% id), so it is the app that will show how brittle Name-first matching
  is; and its 278.5 s walk (finding 7) makes it the worst case for the snapshot budget -- a
  reason to keep it, not to drop it.
- **HandBrake** -- the cleanest identification in the set: 73% AutomationId, none generated,
  all unique in their window, and a 2 s walk. A different technology from KeePass 2 and from
  our own sample app, and its tab / combo / number-field screens map onto the wizard and
  settings scenarios. It is the app against which "AutomationId is the primary property" will
  look best, so pairing it with KeePass 2 keeps the measurement honest.
- **KeePassXC** -- third, and useful despite sharing a toolkit with the PySide6 sample app
  (#33): it is the only app in the set where ids exist but are not unique, which is the case
  the recognition engine (#11, #21) is most likely to get wrong. It is also the only app that
  populates `LabeledBy` (finding 6), so it is the one target that can check a label-based
  descriptor against the toolkit's own answer. Two costs: it duplicates
  KeePass 2's domain, and it locks its database on inactivity and on workstation lock, throwing
  away the open form, so every run against it has to unlock first (see `learnings.md`). That is
  friction a pilot should not have -- take it only after the two above work.
- **Notepad++** -- fails criterion 1 by a wide margin (59%), and its main surface is a Scintilla
  editor that UIA does not expose as controls at all. Keeping it as a *pilot* would mean
  measuring RQ1 against a target UIA cannot reach. Keeping it as the **#23 fixture** is the
  right use: its 32 anonymous toolbar buttons are the clearest statement of what the win32
  fallback has to solve.

Open before #21 (D1) is decided: finding 7's walk time. If a WinForms snapshot cannot be read
in seconds, the architecture question is not only "which properties" but "how many elements per
snapshot", and that changes the answer for every pilot.

## How to run (Windows)

Setup, from the repo root in `cmd.exe` (the venv is throwaway; pywinauto is not a project dependency yet, and 0.6.9 is pinned for a reproducible run: the script was written against 0.6.9, not the 1.0.0b1 pre-release):

```
git switch main && git pull --ff-only
py -m venv %TEMP%\ayna-uia
%TEMP%\ayna-uia\Scripts\python -m pip install pywinauto==0.6.9
```

Unzip the portable builds listed under `source` in [`uia-targets.json`](uia-targets.json) and bring each app into its `state` (see the manual check in #6). Do not minimise the windows: minimised windows count as offscreen and are skipped. Then run all targets with one command. It prints one line per target and then the results table:

```
%TEMP%\ayna-uia\Scripts\python eval\spikes\uia_dump.py dump
```

Useful variants: `--only keepass2` (repeatable) re-dumps one target; `--id calc --process CalculatorApp.exe --app Calculator --technology UWP` dumps an app that is not in the list; `--no-patterns` skips the pattern checks if a walk is very slow.

Tests (any OS): `python3 -m unittest discover -s eval/spikes -p "test_*.py" -v`.

## Next

- #21 (D1 decision): use the tables and the recommendation as dump evidence, together with the trial-app dump from #9 (`eval/apps/trial/uia_dump.py`).
- #11 (descriptor v0): keep the properties that are actually populated; check how often LabeledBy is set before relying on it for `nearest_label`.
- #12 (snapshot export): the walk times show how far a full walk is from the 2 s target.
- #23 (win32 fallback): start from the interactive elements without AutomationId and Name.
