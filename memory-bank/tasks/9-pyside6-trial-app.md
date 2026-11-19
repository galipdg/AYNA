# #9 One-screen PySide6 trial app

- Issue: https://github.com/galipdg/AYNA/issues/9
- Owner: hasan · Branch: `hasan/9-pyside6-trial-app`
- Started: 2026-10-25 · Last update: 2026-10-25

## Approach
First Python code in the repo, so the footprint stays small and the commands are
explicit (`eval/AGENTS.md` still has an empty "Commands" section, so tooling was
agreed with the user rather than invented): a local
`eval/apps/trial/requirements.txt` and a `.venv`, no repo-wide `pyproject.toml`.

Layout under `eval/apps/trial/`:
- `app.py` — the login screen (the issue's expected output), with `authenticate()`
  as a pure function so the credential rules are testable without a display.
- `uia_dump.py` — the one documented command that prints the UIA tree with each
  AutomationId and exits 1 if one of the app's own inputs/buttons/checkboxes has
  none. This is what criterion 2 is judged on.
- `tests/test_authenticate.py` — pure tests, run on any OS.
- `tests/test_uia.py` — `@pytest.mark.windows`: launches the real window, checks
  the AutomationIds and drives both login flows. Automating criteria 2 and 3 now
  means they do not need a manual check every week (§10.5).
- `tests/conftest.py` — registers the `windows` marker and skips those tests off
  Windows, so the suite stays green on galip's macOS.
- `README.md` — commands plus the Qt→UIA mapping table.

Why a trial app at all: #21 (D1 — sample-app technology) depends on this, so #9 is
the spike that decides whether PySide6 gives us clean UIA data before the 5-6
screen sample app in #33.

## Decisions (small, local to this task)
- 2026-10-25 — Credential rules kept as a pure `authenticate()` function instead of
  inline widget code, so criterion 3 is covered by an OS-independent test as well as
  by the UIA test.
- **2026-11-12 — superseded:** `eval/apps/trial/requirements.txt` is gone since #122
  (omer, merged 2026-10-31). Dependencies live in `eval/pyproject.toml` and the setup command
  is `.venv/Scripts/python.exe -m pip install -e "eval[dev]"` from the repository root. The
  decision below records what was true in #9.
- 2026-10-25 — Dependencies recorded in `eval/apps/trial/requirements.txt` and
  installed into `.venv` (user's choice, asked per §7). A repo-wide `pyproject.toml`
  was rejected for now: it is devops territory and would need an ADR.
- 2026-10-25 — **`accessibleName` is set only on the two input fields, not on every
  control as #9's description suggests.** Measured reason: Qt maps `accessibleName`
  onto the UIA Name and it replaces the natural Name, so on the window it hides the
  title and on a label it hides the text — which would make criterion 3 ("shows a
  'Welcome' label") unverifiable through UIA. The description's advice is wrong for
  Qt; the acceptance criteria themselves do not require it. Raised with the user.
- 2026-10-25 — The app is launched with `subprocess.Popen` and found by UIA
  ClassName instead of `pywinauto.Application.start()`, because of the venv-launcher
  problem below.

## Status
- [x] Branch created, task note opened
- [x] Dependencies agreed and installed: PySide6 6.12.0, pywinauto 0.6.9, pytest 9.1.1
- [x] `app.py` written; starts and shows the window
- [x] `uia_dump.py` reports an AutomationId for all 4 inputs/buttons/checkboxes (exit 0)
- [x] admin/admin shows `Welcome, admin!`; wrong password shows the error message
- [x] 12/12 tests pass (7 pure + 5 UIA), verified on this Windows machine 2026-10-25
- [x] `eval/AGENTS.md` "Commands" section filled in (user OK 2026-10-25)
- [x] Committed (5e23d15, 350071c), pushed and PR #116 opened with `Closes #9`
- [x] The accessibleName finding posted as a comment on #9 (user OK 2026-10-25)
- Next step: get one approving review on PR #116 and merge it; then tell omer so the last #2 criterion can be ticked.

## Manual checks
No manual check needed: criteria 2 and 3 are covered by `tests/test_uia.py`, which
ran green on the real window in this session. Criterion 1 (`starts with python
app.py`) was observed directly — the window appeared with the title
`AYNA Trial - Login` and `Responding=True`.

## Open issues
- 2026-10-25 — `eval/AGENTS.md` Commands is now filled in. `agent/AGENTS.md` still
  says "to be filled in"; it should get the same treatment when `agent/` is
  scaffolded (#26), and `ayna_agent/playback/` is hasan's lane anyway.
- 2026-10-25 — No CI and no Python linter exist in the repo (`.github/workflows/` is
  absent), so two Definition-of-Done items on PR #116 cannot be ticked. Worth a
  separate issue for omer (devops) rather than smuggling it into #9.
- 2026-10-25 — #9's description ("objectName and accessibleName set on every
  control") is wrong for Qt, see the decision above. Suggest editing the issue
  description so #33 and the testability guideline (#94) do not repeat the mistake.
- 2026-10-25 — The dotted AutomationId means renaming any ancestor changes every
  descendant's id. That is a real fragility source and a candidate input for RQ1;
  worth a line in D1 (#21) rather than a silent assumption.
- 2026-10-25 — Inbox from omer (#2): hasan still owes one merged PR for the monorepo
  criterion. The #9 PR is a real change in hasan's area and should satisfy it, so a
  throwaway PR is probably unnecessary — confirm with omer.

## Handoff
The four UIA findings (venv launcher, dotted AutomationId, accessibleName replacing
Name, window-frame controls without ids) are in `memory-bank/learnings.md`; they
affect galip's recognition work and the sample app, not just this app.

## Outcome (fill when the issue closes)
Delivered `eval/apps/trial/` (app, UIA dump, 12 tests, README) and the Qt→UIA
findings in `memory-bank/learnings.md`. PR: https://github.com/galipdg/AYNA/pull/116.
All three acceptance criteria verified on the Windows machine on 2026-10-25, with one
documented deviation: the window frame's own buttons have no AutomationId, so that
check is scoped to the app's `Q*` widgets. Not done: CI and linter runs, because
neither exists in the repo yet.
