# #6 UIA tree dump spike on 3 candidate pilot apps

- Issue: https://github.com/galipdg/AYNA/issues/6
- Owner: galip · Branch: `galip/6-uia-tree-dump`
- Started: 2026-10-25 · Last update: 2026-10-25

## Approach
One script, `eval/spikes/uia_dump.py`, with two subcommands. `dump` (Windows only) walks the raw UIA view of every visible top-level window of a target process with pywinauto's `uia` backend and writes `eval/spikes/uia-dumps/<id>.json`. `stats` (any OS) reads the dumps and prints the property-richness tables for the note `eval/spikes/uia-dump.md`. Targets are listed in `eval/spikes/uia-targets.json`. Tests use stdlib `unittest` with fake nodes, so everything except the thin UIA reader runs on macOS.

## Decisions (small, local to this task)
- 2026-10-25 — Candidates (Galip): KeePass 2 (WinForms), HandBrake (WPF), KeePassXC (Qt Widgets), plus Notepad++ (Win32) as an extra for #23.
- 2026-10-25 — pywinauto only in a throwaway venv on the Windows machine; no `pyproject.toml` in `eval/` (Hasan's module, not scaffolded). Pinned to `0.6.9` (latest stable, 2025-01-06); a `1.0.0b1` pre-release exists (2026-10-15) and is untested. The dump records the installed version.
- 2026-10-25 — Script and note live in `eval/spikes/` next to the dumps the issue asks for, like `ai/spikes/` in #7. `eval/` is Hasan's; FYI left in his inbox.
- 2026-10-25 — "Interactive" = a fixed list of control types (`INTERACTIVE_TYPES` in the script), so the share is comparable across frameworks. Empty or whitespace-only AutomationId/Name counts as missing.
- 2026-10-25 — Dumps are a flat element list with parent links (closer to the future snapshot of #12 than a nested tree), one element per line so they diff well. Strings are cut at 200 characters; Value-pattern contents are never read; only the exe file name is kept, not its path.
- 2026-10-25 — Properties are read from the raw `IUIAutomationElement` (`element_info.element.Current*`), not pywinauto's wrappers, because the wrappers hide COM errors as `None`/`""` (checked in the 0.6.9 source). `read_errors` in each dump counts the failed reads.

## Status
- [x] Branch, task note
- [x] Script, targets file, 23 unit tests passing on macOS (Python 3.11 and 3.15); pywinauto API names checked against the 0.6.9 source on GitHub
- [x] Note skeleton: method, candidates, expectations written before the run, selection criteria, run instructions
- [ ] Windows session: dumps of at least 3 apps (pending)
- [ ] Fill Results, Findings and Recommendation in `eval/spikes/uia-dump.md` from `uia_dump.py stats`
- Next step: push the branch, post the manual check below on #6 with label `needs-windows-test` (needs Galip's OK), then wait for the weekly Windows session.

## Manual checks
- 2026-10-25 · pending Windows session · UIA dump of the four targets
  - **Setup**: Windows 10/11 machine with the repo cloned and Python 3.11+ (`py --version`). Then:
    - `git fetch && git checkout galip/6-uia-tree-dump`
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
  - **Report back**: pass/fail per step; the whole console output of step 5 as an issue comment; the four JSON files (commit them on this branch together with Galip, or send them to him); Windows version (`winver`) and display scaling; for a failure, the traceback and a screenshot. If a target is skipped with "no visible window found", check its exe name in Task Manager and dump it as a one-off: `… uia_dump.py dump --id <id> --process <exe> --app "<app>" --technology <tech>`.

## Open issues
- `ruff` is still not installed on this Mac and `eval/` has no `pyproject.toml`, so the spike is not linted (same as #7). Line length is kept at ~100.
- The `dump` path (pywinauto/COM) is untested until the Windows session; only the walker, reader logic (with fakes), writer and stats are unit-tested.
- Milestone Week 1 is due 2026-10-26, but the dumps can only come from the weekly Windows session. #21 (D1 decision, week 2) depends on this.

## Handoff
- After the session: copy the dumps to `eval/spikes/uia-dumps/`, run `python3 eval/spikes/uia_dump.py stats` and `... stats --by-type`, paste into `uia-dump.md`, check the four expectations, then write Findings and the Recommendation against the five criteria in the note.
- The expectations section in the note is deliberately written before the run; do not rewrite it, mark each one confirmed or refuted.

## Outcome (fill when the issue closes)
