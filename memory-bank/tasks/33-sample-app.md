# #33 Sample app v1 (5-6 form-heavy screens)

- Issue: https://github.com/galipdg/AYNA/issues/33
- Owner: hasan · Branch: `hasan/33-sample-app`
- Started: 2026-11-12 · Last update: 2026-11-12

## Approach
The app under test for every later experiment, so it is built to be *measured*, not used.
Six screens in six top-level windows (`--screen` picks one, so a test never has to
navigate there first): login, customer list with a grid, detail form, tabbed settings,
three-page wizard, and the yes/no dialogs.

Layout under `eval/apps/sample/`, split so that most of it is testable without a display:
- `model.py` — all rules, no Qt: login, search/filter, required-field validation, wizard
  summary. Tested by `tests/test_model.py` on any OS.
- `texts.py` — every visible string in one place, plus `VERSION = "1.0"` and `title()`,
  which is what puts the version in every window title (criterion: version in title bar).
- `windows.py` — the six screens. Controls are built by small factories (`_combo`,
  `_edit`, `_label`, `_button`, `_box`) that always set `objectName`, so a control cannot
  reach a screen without an AutomationId.
- `app.py` — the one command, cross-platform; `--search-delay-ms` exposes the SC-18 delay.
- `uia_dump.py` — the dump *and* the acceptance check for criteria 1 and 2: counts the
  interactive controls per screen, reports controls without an AutomationId, exits
  non-zero on failure. `--json` is the source for the README's id table and later for
  `eval/nl/objects/sample.json` (#36).
- `tests/test_screens.py` — Qt widgets without UIA (runs on macOS too).
- `tests/test_uia.py` — `@pytest.mark.windows`, drives the real windows through pywinauto.

Behaviour the reference scenarios (`docs/rs/scenarios.md` §C.2) need is implemented on
purpose rather than by accident: a control that becomes ready late (SC-18, the Open button
after a search), a required field (SC-34), a modal dialog when leaving an edited form
(SC-22), a combo box with Turkish items (SC-20).

## Decisions (small, local to this task)
- 2026-11-12 — Six separate windows instead of a `QStackedWidget`, so each screen has its
  own UIA ClassName and `--screen` can open it directly. Keeps the UIA tests independent
  of navigation.
- 2026-11-12 — `accessibleName` only on controls with no useful visible text, following
  the #9 finding (Qt maps it onto the UIA **Name** and *replaces* the natural one).
- 2026-11-12 — The AutomationId check counts only controls whose UIA ClassName starts with
  `Q`: the window frame's Minimize/Maximize/Close buttons have no id (Windows, not the
  app), and grid cells, headers and tab items are not widgets.
- 2026-11-12 — `eval/pyproject.toml`: `apps/sample/tests` added to `testpaths` and
  `apps/sample` to ruff's `src`, so `pytest eval` collects it and the local imports lint.
- 2026-11-12 — **`app.py` renamed to `sample_app.py` as well, after CI.** I had argued it
  could keep its name because it is only ever run, never imported. Wrong: it is still
  importable, and the winner depends on the pytest invocation -- `pytest eval` from the root
  loads sample's conftest first and trial's `from app import ...` got trial, while CI's bare
  `pytest` from `eval/` loads them in `testpaths` order and the same import got *this* app.
  The rule has no exception for scripts; `learnings.md` 2026-11-12 has the mechanism.
- 2026-11-12 — **`uia_dump.py` renamed to `uia_check.py` and `tests/test_uia.py` to
  `tests/test_sample_uia.py`.** The trial app has files of both names, the tests import
  them by bare module name, and #199 already measured what that costs: `pytest eval`
  aborts in collection on the test module, and the source module is shadowed for the whole
  run. `app.py` keeps its name -- it is only ever run, never imported.
- 2026-11-12 — The offscreen Qt platform is chosen in `QApplication`'s argv instead of
  `QT_QPA_PLATFORM`; see Manual checks and `learnings.md` for what the environment variable
  did to every UIA test in the run.
- 2026-11-12 — `tests/test_sample_uia.py`'s `until()` treats `ElementNotFoundError` as
  "not ready yet", and the wizard test waits for each page before clicking Next again. Two
  clicks in a row sent the second before Qt had shown page two, so the wizard stayed put.

## Status
- [x] `model.py`, `texts.py`, `windows.py`, `app.py`, `uia_check.py` written
- [x] `README.md` with the run command, the Qt/UIA rules and the measured id tables,
      generated from `uia_check.py --json`
- [x] `uia_check.py` green on all five screens, 2026-11-12 on this Windows machine:
      login 9 interactive / 21 elements, main 10 / 26, detail 9 / 24, settings 8 / 26,
      wizard 8 / 22 -- **0 controls without an AutomationId**. Criteria 1 and 2 met.
- [x] `pytest eval/apps/sample/tests` 57/57 green in 37 s (32 display-independent + 25 UIA)
- [x] `pytest eval` (trial and sample together) 125/125 green in 45 s, after the two
      module renames and the `QT_QPA_PLATFORM` fix
- [x] ruff check and `ruff format --check` clean over `eval` (ruff installed with
      `pip install -e "eval[dev]"`, user's OK 2026-11-12)
- [ ] Criterion 3 (one command on *every* member's machine) -- needs galip and omer on macOS
- [x] `eval/AGENTS.md`: the sample app's commands, plus the one-module-name-per-tree and
      the no-Qt-env-var rules (user's OK 2026-11-12)
- [x] Four commits, pushed, **PR #230** open with `Closes #33`, both teammates requested
- [x] CI's `eval` job failed on the first run and is fixed: `app.py` existed in both apps,
      and the trial app's `from app import ...` resolved to this app's. Renamed to
      `sample_app.py`. Both invocations green now: `cd eval; pytest -q` 69 passed (what CI
      runs) and `pytest eval` from the root 125 passed; ruff clean.
- [x] **CI 5/5 green** on PR #230 after the rename (run 43262203133): the `eval` job
      collected 69 items and all passed in 30.8 s on the Windows runner, so the 25 UIA tests
      really ran there, not only here.
- Next step: galip's and omer's macOS run (the last criterion) and their review of #230.

## Manual checks
- 2026-11-12 · hasan · `uia_check.py` on all five screens · **pass** · evidence: the
  numbers above, and the same counts are asserted by `tests/test_sample_uia.py`
- 2026-11-12 · hasan · the app started from the repository root and driven through all six
  screens by the UIA tests (login, grid, detail, settings, wizard, both dialogs) · **pass**
- Criterion 3 on macOS is **pending**: galip and omer have to run
  `python eval/apps/sample/sample_app.py` once. Nothing in the app is Windows-only (the UIA tests
  skip themselves elsewhere), but it has not been observed anywhere but here. Ask in the
  PR body.

### Reproducing CI
CI runs bare `pytest` **from `eval/`**, which is not the same run as `pytest eval` from the
repository root: they load the two apps' conftests in a different order, and that decides
whose module wins when a name exists twice. Run `cd eval; ../.venv/Scripts/python.exe -m
pytest -q` (69 passed) before pushing anything that adds a module under `eval/`.

### What the UIA run cost before it was green (2026-11-12)
First full run: **25 of 25 UIA tests errored**, 12:40 of it pure timeout, while each test
passed alone. Cause: `test_screens.py` set `QT_QPA_PLATFORM=offscreen` in the pytest
process, the launched app inherited it and had no window to find. Then `pytest eval` showed
the two module-name clashes with the trial app, and the trial app's own UIA tests errored
for the same offscreen reason. All three are fixed and recorded in `learnings.md`.

## Open issues
- The settings screen has 8 interactive controls **per tab** and the wizard 8 **per page**,
  not 8 on one visible surface: an unselected tab and a hidden page are not in the UIA tree
  at all. `tests/test_screens.py` checks them tab by tab and page by page on the widgets.
  Say this in the PR body so criterion 1 is not read as "8 visible at any moment".
- **Choosing a combo-box item through UI Automation does not work on Qt**: measured
  2026-11-12, `SelectionItem.Select`, `Invoke` on the item and `ValuePattern.SetValue` all
  leave a `QComboBox` unchanged (the items only exist after `ExpandCollapse`). SC-20 needs
  it, so it is playback's problem -- an open question for #40, not for this app.
- Qt inserts its own `qt_tabwidget_stackedwidget` level into every settings id
  (`QApplication.settings.tabs.qt_tabwidget_stackedwidget.generalTab.themeCombo`). It cannot
  be avoided with a `QTabWidget`, it is why the wizard shows and hides pages in place, and
  it is one more reason logical names must not be derived from the id path alone (#11).
- `.codex/` (hooks for another CLI) sits untracked in the working tree, unrelated to #33 and
  not part of this commit. Ask the user whether it should be ignored or committed by them.
- The same `eval/` module-name trap as #199 bit again four days later, which says the rule
  was in the wrong place: it is now in `eval/AGENTS.md`, where someone working in `eval/`
  actually reads it, not only in `learnings.md`.

## Handoff
The ids in the README are generated from `uia_dump.py --json`, never typed by hand — rerun
it after any rename, because the AutomationId is the dotted path over the whole object
chain, so renaming one parent changes every descendant's id (#9 finding).

## Outcome (fill when the issue closes)
Delivered `eval/apps/sample/` v1.0: six screens, `model.py` without Qt, `texts.py` for
every visible string, `uia_check.py` as the one-command acceptance check, a README whose id
tables are generated from it, and 57 tests. PR: https://github.com/galipdg/AYNA/pull/230.
Criteria 1 and 2 measured on Windows on 2026-11-12 (44 interactive controls over five
screens, 0 without an AutomationId); criterion 3 is **not ticked** -- the app has only been
run on Windows, and galip and omer were asked in the PR body to run it once on macOS.
