# #47 Bug-injected versions of the sample app

- Issue: https://github.com/galipdg/AYNA/issues/47
- Owner: hasan · Branch: `hasan/47-bug-injected-versions` (stacked on `hasan/46-ui-change-versions`)
- Started: 2026-11-15 · Last update: 2026-11-15

## Approach
Five versions of the #33 app, `bug1` … `bug5`, each with **one** real functional bug, and each
naming the reference scenario that must fail on it. Same layer shape as #46 (`bugs.py` declares,
`bug_patch.py` patches, `bugs.md` is the log, `sample_app.py --bug bug2` runs it) and the same
agreed deviation from the issue's expected output: one layer, not five directories.

**Four of the five bugs are specified by the RS, not invented here**, which decided where each
one sits -- `docs/rs/scenarios.md` names them down to the control:

| | Kind | Control | Must fail |
|---|---|---|---|
| `bug1` | wrong label | `login.statusLabel` | SC-21 (a wrong text in the **login** status label) |
| `bug2` | disabled button | `detail.saveButton` | SC-19 (the Save button stays disabled) |
| `bug3` | wrong saved value | `wizard.summaryLabel` | SC-20 (no scenario asks for this bug; see below) |
| `bug4` | missing validation | `detail.nameInput` | SC-34 (the "missing validation" version) |
| `bug5` | wrong navigation | `login.loginButton` | SC-31 (logging in opens the wrong screen) |

**The patches are installed before the first window exists**, and they replace module globals or
*class* methods. This is the one real design constraint of the issue and it is not obvious: Qt
binds a slot when `connect` is called, `windows.py` connects in `__init__`, so #46's per-window
hook shape would leave every connected signal calling the correct method. It is also closer to
what a buggy build is -- the defect is in the code, not in one window.

## Decisions (small, local to this task)
- 2026-11-15 — One bug layer instead of five app directories, as agreed for #46.
- 2026-11-15 — **`bug3` sits on the wizard's summary (SC-20), not on the detail form.** The
  plan's SA-B row asks for a "wrong saved value" and the RS never says where. Rather than invent
  a check nothing runs, the bug is put where an existing scenario already catches it: SC-20
  verifies the summary contains the selected department, and the bug swaps the department for the
  role. If a detail-form scenario is wanted, that is galip's call on `docs/rs/` (asked in his
  inbox) and only the row in `bugs.md` would move.
- 2026-11-15 — **Exactly one rule is dropped in `bug4`**: the e-mail rule keeps working. A
  version that validated nothing would fail every detail-form test for the wrong reason and
  SC-34's CI job would prove nothing about the required field. `model.validate_detail`'s own
  docstring already promised this.
- 2026-11-15 — **`bug2` disables the button rather than hiding it.** SC-19 is about a wait that
  cannot succeed (category "timeout", condition `enabled`); a hidden control is
  element-not-found, which is a different category and a different scenario.
- 2026-11-15 — **`bug5` keeps the welcome message correct.** The failure has to land on the step
  *after* the login, or SC-31's run could be blamed on the login itself.
- 2026-11-15 — `bug_patch.install` refuses a second bug (`RuntimeError`): a version with two
  bugs is unusable as evidence, because a failing step could no longer be attributed.
- 2026-11-15 — A text bug patches `model.LOGIN_WELCOME`, not `texts.LOGIN_WELCOME`: `model.py`
  does `from texts import …`, so patching `texts` changes nothing (`learnings.md` 2026-11-15).

## Status
- [x] Branch (stacked on #46's), task note, #47 In progress on the Project
- [x] `bugs.py` (5 bugs, each with kind, control, scenario, failing step, symptom, patch target)
- [x] `bug_patch.py` (install/reset), `--bug` on `sample_app.py`, `bug` on `uia_check.launch_app`
- [x] `bugs.md` — the bug log, with what each bug patches and what no test here can claim
- [x] `tests/test_bugs.py` (25, offscreen) and `tests/test_bug_uia.py` (5, Windows)
- [x] Both acceptance criteria met (≥5 bugs; every bug names the scenario that must fail), each
      with a test — the scenario check reads `docs/rs/scenarios.md` itself
- [x] Committed (`11c28e1`), pushed, **PR #239** open **against `hasan/46-ui-change-versions`**
      (stacked on #238), both reviews requested, both criteria ticked on the issue; galip has the
      wrong-saved-value question in his inbox and in the PR body
- Next step: **retarget PR #239 to `main` once #238 merges** (`gh pr edit 239 --base main`), and
  take galip's answer on where bug3 belongs.

## Manual checks
- 2026-11-15 · hasan · `pytest eval/apps/sample/tests/test_bug_uia.py` (5 app launches, each
  bug's symptom read through UI Automation) · **pass, 5 of 5, first run** · evidence: this
  session. Nothing had to be corrected, which is the difference from #46: these bugs are read
  through properties the v1 dump already measured (`Name`, `enabled`, a window's existence).
- 2026-11-15 · hasan · full suites · `pytest eval` **241 pass**, `cd eval; pytest -q` **185
  pass**, `pytest eval/apps/sample/tests` **136 pass**, ruff check + format clean.

## Open issues
- **"A correct test must catch each bug" is not proven here and must not be claimed.** These
  versions are the *precondition*: the proof needs the reference scenarios built in the editor
  (#62), played by the agent (#54, #55) against these builds, with the categories SC-19/SC-21/
  SC-31 ask for coming from #63's triage. `bugs.md` says so in its last section.
- **No scenario asks for a wrong saved value** (bug3's placement above). galip's call; in his
  inbox.
- **`test_sample_uia.py` flakes when the bug tests run before it, and the cause is not found.**
  Measured on 2026-11-15, resolving #239's merge: the CI invocation failed once with
  `test_the_right_credentials_are_welcomed_by_name` ("wrong credentials" for `admin`/`admin`),
  and the pair `test_bug_uia.py test_sample_uia.py` then failed twice running on its own, the
  second time on `test_saving_without_a_name_shows_the_required_message` ("Kayit kaydedildi"
  instead of the required-field message). Both symptoms are "the text I set did not land", so
  the suspect is the readiness gate, not the bug versions. What was ruled out:
  - **Not a window leak.** `kill_process_tree` leaves 0 windows of the app's classes in the UIA
    tree the moment it returns (measured 3x, the tree is clear within 0.3 s).
  - **Not a cross-window mix-up either way.** Two live windows of one class make pywinauto raise
    `ElementAmbiguousError` at `wait("visible ready")`, so a stale window would error, not answer.
  - **Not any single bug version**: each bug test followed by the two sample tests passes.
  - **Not `set_edit_text` on a fresh app**: 12 launches of the login screen, text read back
    correctly every time.
  - **Not `eval/`'s other UIA file**: `test_variant_uia.py` then `test_sample_uia.py` is 48/48.
  It is a Heisenbug: four runs of the failing pair under a plugin that enumerates windows around
  every launch, find and kill all passed, and the full suite is **185 green** on the re-run that
  the merge was committed on. Left alone deliberately -- `test_sample_uia.py` is #33's file and a
  fix guessed at without a reproduction is worse than the flake. It is **#69 data** (RQ2
  flaky-rate), and the diagnostic plugin is worth rebuilding there.
- A bug version and a #46 change version can be run together (`--variant v2a --bug bug1`) and
  nothing stops it. That is a combination nobody has asked for; it is not tested and the title
  then reads `1.0-v2a-bug1`. Worth a scenario only if #86 wants "heal a changed *and* broken
  build", which would be a measurement of its own.

## Handoff
- **The bug set is driven by `docs/rs/scenarios.md`.** `test_every_bug_names_a_scenario_that_exists`
  looks up each `SC-xx · <title>` heading in that file, and
  `test_four_of_the_five_bugs_are_the_ones_the_scenarios_ask_for` pins the controls the RS
  specifies. If galip renumbers or retitles a scenario, this suite goes red on purpose -- fix the
  declaration in `bugs.py`, not the test.
- **`test_every_version_shows_exactly_its_own_bug` is the test to keep.** It reads all five
  symptoms on every version, so a patch that broke something else, or leaked past `reset()` into
  the next test, fails. The symptom probes keep each window in a local: a window that goes out of
  scope takes its C++ children with it (the same trap as #46's generator).
- The Windows file costs **5 app launches** (~14 s) and does not play the scenarios on purpose;
  its docstring says which issues own that.

## Outcome (fill when the issue closes)
