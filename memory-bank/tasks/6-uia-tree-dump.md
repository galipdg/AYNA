# #6 UIA tree dump spike on 3 candidate pilot apps

- Issue: https://github.com/galipdg/AYNA/issues/6
- Owner: hasan (handover from galip) · Branch: `hasan/6-uia-dumps`
- Started: 2026-10-25 · Last update: 2026-10-27

## Approach
One script, `eval/spikes/uia_dump.py`, with two subcommands. `dump` (Windows only) walks the raw UIA view of every visible top-level window of a target process with pywinauto's `uia` backend and writes `eval/spikes/uia-dumps/<id>.json`. `stats` (any OS) reads the dumps and prints the property-richness tables for the note `eval/spikes/uia-dump.md`. Targets are listed in `eval/spikes/uia-targets.json`. Tests use stdlib `unittest` with fake nodes, so everything except the thin UIA reader runs on macOS.

## Decisions (small, local to this task)
- 2026-10-25 — Candidates (Galip): KeePass 2 (WinForms), HandBrake (WPF), KeePassXC (Qt Widgets), plus Notepad++ (Win32) as an extra for #23.
- 2026-10-25 — pywinauto only in a throwaway venv on the Windows machine; no `pyproject.toml` in `eval/` (Hasan's module, not scaffolded). Pinned to `0.6.9` (latest stable, 2025-01-06); a `1.0.0b1` pre-release exists (2026-10-15) and is untested. The dump records the installed version.
- 2026-10-25 — Script and note live in `eval/spikes/` next to the dumps the issue asks for, like `ai/spikes/` in #7. `eval/` is Hasan's; FYI left in his inbox.
- 2026-10-25 — "Interactive" = a fixed list of control types (`INTERACTIVE_TYPES` in the script), so the share is comparable across frameworks. Empty or whitespace-only AutomationId/Name counts as missing.
- 2026-10-25 — Dumps are a flat element list with parent links (closer to the future snapshot of #12 than a nested tree), one element per line so they diff well. Strings are cut at 200 characters; Value-pattern contents are never read; only the exe file name is kept, not its path.
- 2026-10-25 — Handover (Galip): everything galip has goes into PR #119 (`Refs #6`, so merging does not close the issue). hasan runs the Windows check from `main`; his agent fixes the script if it fails, commits the dumps, writes Results/Findings/Recommendation and closes #6 with its own PR from `hasan/6-uia-dumps`. Request in hasan's inbox. This replaces, for #6 only, the weekly-session rule of sending failures back to the owner's inbox.
- 2026-10-25 — Elements inside a TitleBar are excluded from "interactive": hasan measured in #9 that the window frame's controls never have an AutomationId, so counting them would lower every app's share for a reason that is not the app's.
- 2026-10-25 — Properties are read from the raw `IUIAutomationElement` (`element_info.element.Current*`), not pywinauto's wrappers, because the wrappers hide COM errors as `None`/`""` (checked in the 0.6.9 source). `read_errors` in each dump counts the failed reads.

## Status
- [x] Branch, task note
- [x] Script, targets file, 24 unit tests passing on macOS (Python 3.11 and 3.15); pywinauto API names checked against the 0.6.9 source on GitHub
- [x] Note skeleton: method, candidates, expectations written before the run, selection criteria, run instructions
- [x] PR https://github.com/galipdg/AYNA/pull/119 (tooling, `Refs #6`) opened 2026-10-25, merged `origin/main` in, marked ready; label `needs-windows-test` on #6
- [x] PR #119 merged, handover to hasan done
- [x] 2026-10-27 the four portable apps downloaded to `C:\ayna-pilots\` and brought into their target state on hasan's Windows machine
- [x] `find_windows` fixed (commit ddc33b7): windows are found by handle, not through the UIA tree, and `walk()` deduplicates by handle. 26 unit tests pass
- [x] Dumps of `keepass2`, `handbrake`, `notepadpp` in their target state
- [ ] `keepassxc` dump has to be retaken: the database locked itself before the final run, so the dump holds the unlock screen, not the entry form. Needs the workstation unlocked
- [ ] Fill Results, Findings and Recommendation in `eval/spikes/uia-dump.md` from `uia_dump.py stats`
- [ ] Commit the dumps, remove `needs-windows-test`, PR with `Closes #6`
- Next step (hasan): once the machine is unlocked, unlock KeePassXC (`ayna-demo`), open New Entry, run `.venv\Scripts\python eval\spikes\uia_dump.py dump --only keepassxc`, then write the note.

## Manual checks
- 2026-10-25 · pending Windows session · UIA dump of the four targets
  - **Setup**: Windows 10/11 machine with the repo cloned and Python 3.11+ (`py --version`). Then:
    - `git switch main && git pull --ff-only` (needs PR #119 merged)
    - `py -m venv %TEMP%\ayna-uia`
    - `%TEMP%\ayna-uia\Scripts\python -m pip install pywinauto==0.6.9`
    - Unzip the portable builds listed under `source` in `eval/spikes/uia-targets.json` into `C:\ayna-pilots\` (KeePass 2, KeePassXC, HandBrake, Notepad++). HandBrake needs the .NET 8 Desktop Runtime.
    - Note the display scaling (Settings → System → Display → Scale).
  - **Steps**:
    1. Start `KeePass.exe`; turn the update check off if it asks. File → New, save as `%TEMP%\ayna-demo.kdbx` with master password `ayna-demo`, finish the wizard. Then Edit → Add Entry (Ctrl+I) and leave the dialog open.
    2. Start `KeePassXC.exe`; turn the update check off if it asks. Database → New Database, name `ayna-demo`, password `ayna-demo`, save as `%TEMP%\ayna-demo-xc.kdbx`. Then Entries → New Entry (Ctrl+N) and leave the form open.
    3. Start `HandBrake.exe`. Close any first-start prompt without opening a source.
    4. Start `notepad++.exe`; press Ctrl+F and leave the Find dialog open.
    5. Make sure no window is minimised. In `cmd.exe` at the repo root run `%TEMP%\ayna-uia\Scripts\python eval\spikes\uia_dump.py dump`.
    6. Run `dir eval\spikes\uia-dumps`.
  - **Expected**:
    1. KeePass shows the empty demo database with the Add Entry dialog on top.
    2. KeePassXC shows the entry edit form.
    3. HandBrake shows its main window with no source.
    4. Notepad++ shows one empty tab and the Find dialog.
    5. One line per target such as `keepass2: 812 elements in 4.2 s -> …\keepass2.json`, none of them `(truncated)` or `skipped`. Then `Dumped 4 of 4 targets.` and a Markdown table with four rows. If one walk takes minutes, rerun it with `--only <id> --no-patterns` and say so.
    6. Four new files: `handbrake.json`, `keepass2.json`, `keepassxc.json`, `notepadpp.json`.
  - **Report back**: pass/fail per step; the whole console output of step 5 as an issue comment; the four JSON files, committed on `hasan/6-uia-dumps` (see the handover in hasan's inbox); Windows version (`winver`) and display scaling; for a failure, the traceback and a screenshot. If a target is skipped with "no visible window found", check its exe name in Task Manager and dump it as a one-off: `… uia_dump.py dump --id <id> --process <exe> --app "<app>" --technology <tech>`.

- 2026-10-25 · hasan · **pre-session smoke check of the untested `dump` path** · pass
  - Ran on the real Windows machine before the pilot apps were downloaded, because
    the note said the pywinauto/COM path had never executed. Used the repo `.venv`
    (Python 3.13.0, pywinauto 0.6.9 — the pinned version) instead of a throwaway
    `%TEMP%yna-uia` venv; same pywinauto, one less step.
  - `pytest eval/spikes/test_uia_dump.py` → **24 passed** on Windows as well
    (galip had only run them on macOS).
  - One-off dump against the already-open Notepad:
    `uia_dump.py dump --id smoke-notepad --process notepad.exe --app Notepad --technology Win32`
    → exit 0, `50 elements in 0.4 s`, `read_errors: 0`, `truncated: false`,
    stats table printed. Interactive 16, AutomationId 81% (13/16), Name 100%,
    AutomationId-or-Name 100%, generated ids 0%.
  - **No fix was needed**: the COM reads, the walker, the writer and the stats
    table all work as written. Machine: `Windows-11-10.0.26300-SP0`, DPI 120
    (125% scaling) — recorded because the dumps store it per window.
  - The smoke dump was written to a scratch folder, not to
    `eval/spikes/uia-dumps/`, so it does not pollute the deliverable.

- 2026-10-27 - hasan - **the real run of the four pilot apps** - pass for 3 of 4, keepassxc to redo
  - Ran on hasan's Windows machine (`Windows-11-10.0.26300-SP0`, DPI 120 = 125% scaling)
    from the repo `.venv` (Python 3.13.0, pywinauto 0.6.9), not a throwaway `%TEMP%` venv.
  - The four portable builds were downloaded to `C:\ayna-pilots\` (KeePass 2.61.1,
    KeePassXC 2.8.0, HandBrake 1.11.2, Notepad++ 8.9.8.1). The .NET 8 Desktop Runtime was
    already installed (8.0.20), so HandBrake needed nothing extra.
  - The app states were set by the agent through UIA and keystrokes instead of by hand; what
    that cost is in `learnings.md` (password fields, foreground focus, shell dialogs).
  - Deviation from the plan: KeePass 2's database is `Database.kdbx`, not `ayna-demo.kdbx` -
    the file-name box of the "Create New Database" dialog could not be set through UIA and the
    default name was kept. It changes a window title, nothing that is measured.
  - Step 5 result: `Dumped 4 of 4 targets.`, no target truncated, `read_errors: 0` everywhere.
    Walk times: keepass2 278.5 s, handbrake 2.0 s, keepassxc 0.5 s, notepadpp 1.0 s.
  - The first run exposed the script bug fixed in ddc33b7 (KeePass's modal dialog was missing).
  - `keepassxc.json` has to be retaken: KeePassXC locked itself between the state setup and the
    final run, so it dumped the unlock screen (58 elements) instead of the entry form (84).

## Open issues
- `ruff` is still not installed on this Mac and `eval/` has no `pyproject.toml`, so the spike is not linted (same as #7). Line length is kept at ~100.
- Check the TitleBar rule against the real dumps: if a frame `MenuItem "System"` or the min/max/close buttons sit outside the TitleBar in some framework, the `--by-type` table will show them.
- Idea, not done: the CI `agent` job already runs on `windows-latest`; a small manual (`workflow_dispatch`) job could run `uia_dump.py dump` against a built-in app and catch pywinauto API mistakes without waiting a week. CI is omer's area, so this would be a request to him.
- The `dump` path (pywinauto/COM) is untested until the Windows session; only the walker, reader logic (with fakes), writer and stats are unit-tested.
- Milestone Week 1 is due 2026-10-26, but the dumps can only come from the weekly Windows session. #21 (D1 decision, week 2) depends on this.

## Handoff
- To hasan (2026-10-25): he finishes and closes #6; his agent may edit `eval/spikes/` and this note's "Manual checks" and "Outcome".
- After the session: commit the dumps in `eval/spikes/uia-dumps/`, run `python3 eval/spikes/uia_dump.py stats` and `... stats --by-type`, paste into `uia-dump.md`, check the four expectations, then write Findings and the Recommendation against the five criteria in the note.
- The expectations section in the note is deliberately written before the run; do not rewrite it, mark each one confirmed or refuted.

## Outcome (fill when the issue closes)
