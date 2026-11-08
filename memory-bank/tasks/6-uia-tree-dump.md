# #6 UIA tree dump spike on 3 candidate pilot apps

- Issue: https://github.com/galipdg/AYNA/issues/6
- Owner: hasan (handover from galip) · Branch: `hasan/6-uia-dumps`
- Started: 2026-10-25 · Last update: 2026-10-29 (KeePassXC retake done)

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
- [x] Script, targets file, unit tests (26, green on macOS and on Windows); pywinauto API names
      checked against the 0.6.9 source
- [x] Note skeleton: method, candidates, expectations written before the run, selection
      criteria, run instructions
- [x] PR https://github.com/galipdg/AYNA/pull/119 (tooling, `Refs #6`) merged; handover to hasan
- [x] 2026-10-27 the four portable apps downloaded to `C:\ayna-pilots\` and brought into their
      target state on hasan's Windows machine
- [x] `find_windows` fixed (commit ddc33b7): windows are found by handle, not through the UIA
      tree, and `walk()` deduplicates by handle
- [x] Dumps of all four targets committed (ae855ff). `keepassxc.json` in that commit still held
      the unlock screen; re-taken on the entry form on 2026-10-29 (84 elements, 41 interactive)
- [x] `eval/spikes/uia-dump.md` filled from the dumps (5ff8fcf): Results (stats table,
      secondary-property table, window states), nine Findings, a verdict on each pre-run
      expectation, and the Recommendation
- [x] Three cross-cutting findings appended to `learnings.md` (Qt ids are not unique, LabeledBy
      is never set, a WinForms walk is ~140x slower per element than WPF). The first two were
      measured on the locked KeePassXC screen and are corrected by the 2026-10-29 entries below
- [x] `keepassxc.json` re-taken on the entry form (human unlocked, agent dumped) and the note
      revised from it: both stats tables, the windows table, findings 3, 6 and 9, verdict 3 and
      the recommendation. Three corrections appended to `learnings.md` — the biggest is that
      **`LabeledBy` is not always empty**: Qt populates it on form rows (5/41), so the earlier
      "0 of 204" finding was an artifact of dumping the unlock screen
- [ ] Remove `needs-windows-test` from #6, open the PR with `Closes #6`
- Next step (hasan): remove the label and open the PR (`Closes #6`), requesting galip's review
  since he owns the spike's first half.

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
    `%TEMP%\ayna-uia` venv; same pywinauto, one less step.
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

- 2026-10-29 - hasan - **KeePassXC retake** - blocked on a human action, not on the code
  - The agent's attempt to set the state automatically (launch KeePassXC with the database,
    focus the window, send the master password, Ctrl+N) was refused by the Claude Code
    permission classifier: a script that types a password into a password manager is not a
    thing it will run. The refusal is correct, and the state setup is a manual check anyway.
  - The dump command itself is allowed, so the split is: a human unlocks, the agent dumps.
  - **Setup**: nothing to install; `C:\ayna-pilots\keepassxc\KeePassXC-2.8.0-x64\` and
    `C:\Users\pc\Passwords.kdbx` are already on the machine from the 2026-10-27 run.
  - **Steps**:
    1. Start `C:\ayna-pilots\keepassxc\KeePassXC-2.8.0-x64\KeePassXC.exe`.
    2. Enter the master password `ayna-demo` and press Enter.
    3. Press Ctrl+N (Entries -> New Entry) and leave the form open. Do not minimise the window
       and do not lock the workstation.
    4. Tell the agent; it runs
       `.venv\Scripts\python eval\spikes\uia_dump.py dump --only keepassxc` straight away.
  - **Expected**: step 4 prints something like `keepassxc: 84 elements in 0.5 s -> ...`, not
    `(truncated)` or `skipped`, and the dump's `windows` list shows a title *without*
    `[Locked]`.
  - **Report back**: the console output of step 4; if the title still says `[Locked]`, the
    database re-locked and steps 1-4 have to be repeated faster.
  - **Result: pass (2026-10-29, hasan at the machine, agent ran the dump).** The human did
    steps 1-3; the agent then ran
    `.venv\Scripts\python eval\spikes\uia_dump.py dump --only keepassxc` →
    `keepassxc: 84 elements in 0.5 s`, `read_errors: 0`, `truncated: false`, window title
    `Passwords - KeePassXC` (no `[Locked]`). The split "a human unlocks, the agent dumps"
    worked on the first try.
  - What the new numbers changed in the note: interactive 26 → 41, unique AutomationIds
    8% → 10%, Name 92% → 88%, `AutomationId or Name` stays 100%, and **`LabeledBy` 0% → 12%
    (5/41)** — the one result that overturns a published finding (finding 6) and two
    `learnings.md` entries, both of which had been measured on the form-less unlock screen.
    Also new: 25 of the 84 ids exceed the 200-character clip, in 5 indistinguishable groups.
    The pilot recommendation did not change.

## Open issues
- **New issue worth opening (performance):** a property-complete UIA walk of a WinForms window
  took 278.5 s for 106 elements against HandBrake's 1.97 s for 149, with `read_errors: 0`.
  The suspect is the ten pattern probes per element over the WinForms COM bridge, but it was
  not isolated. #12 (snapshot export) has a 2 s target (NFR-02) and cannot be designed on the
  WPF number alone. Proposed: "measure UIA read cost per property on WinForms vs WPF" - dump
  the same window with and without `--no-patterns`, and with the pattern list cut down.
- The TitleBar rule held: in all four dumps the frame's controls sit inside a `TitleBar` and
  none of them has an AutomationId, so excluding them does not hide any app control.
- `eval/` still has no `pyproject.toml` and the spike is not linted (#122 covers it, omer waits
  on it for the CI job). Line length is kept at ~100.
- Idea, not done: a `workflow_dispatch` CI job on `windows-latest` running `uia_dump.py dump`
  against a built-in app would catch pywinauto API mistakes without waiting for a weekly
  session. CI is omer's area, so this is a request to him.
- The `dump` path is now exercised on real apps, so it is no longer untested; the state *setup*
  is the part that stays manual.

## Handoff
- To hasan (2026-10-25): he finishes and closes #6; his agent may edit `eval/spikes/` and this note's "Manual checks" and "Outcome".
- After the session: commit the dumps in `eval/spikes/uia-dumps/`, run `python3 eval/spikes/uia_dump.py stats` and `... stats --by-type`, paste into `uia-dump.md`, check the four expectations, then write Findings and the Recommendation against the five criteria in the note.
- The expectations section in the note is deliberately written before the run; do not rewrite it, mark each one confirmed or refuted.

## Outcome (fill when the issue closes)
- Dumps of four apps on four UI technologies, with the property-richness note and a pilot
  recommendation: **KeePass 2 (WinForms) and HandBrake (WPF)** as the pilots, **KeePassXC (Qt)**
  as an optional third, **Notepad++ not a pilot** but kept as the fixture for #23.
- The numbers that decided it: `AutomationId or Name` over interactive elements is 98%
  (KeePass 2), 96% (HandBrake), 100% (KeePassXC) and 59% (Notepad++) - and all 32 of
  Notepad++'s unidentifiable elements sit in one toolbar, so the rest of it is at 100% (47/47).
- What the issue did not ask for but changes other issues: `LabeledBy` is unset in WinForms,
  WPF and Win32 (0/178) and set by Qt only on form rows (5/41), and there on the row
  *container* rather than the editable control — so #11 must still find labels geometrically
  and may use `LabeledBy` only as a confirmation; Qt AutomationIds are present but collide and
  overflow a 200-character field (#11, #21 must not match on them alone); and the WinForms walk
  time puts NFR-02 at risk (#12).
