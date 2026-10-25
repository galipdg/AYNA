# UIA tree dump of candidate pilot apps (#6)

Spike, started 2026-10-25, galip. Question: which open-source Windows apps expose enough identifying information through UI Automation to be AYNA's pilot apps, and how do WinForms, WPF, Qt and Win32 compare?

**Status: tooling ready, dumps pending the weekly Windows session.** The script and its unit tests run on macOS; the dumps need a Windows machine. *Results*, *Findings* and *Recommendation* are filled in from the dumps. The expectations below were written before the run so that the run can confirm or refute them.

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

_Pending the Windows session. Paste the output of `python3 eval/spikes/uia_dump.py stats` here, and the `--by-type` tables under Findings where they explain something._

## Findings

_Pending._

## Recommendation

_Pending. The pilot apps (2–3) will be chosen with these criteria, in this order:_

1. At least 90% of the interactive elements have an AutomationId or a Name (the RQ1 target for standard controls is ≥ 90%).
2. Form-heavy screens close to the reference scenarios (#34).
3. Different UI technologies across the pilots.
4. Free licence, portable, runs offline, and several released versions are available for change experiments.
5. A deterministic start state: no sign-in, no network, no first-run wizard after the first start.

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
