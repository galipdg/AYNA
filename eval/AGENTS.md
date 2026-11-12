# eval/ — Sample apps, experiment versions, measurements, datasets

Owner: hasan (`nl/`: galip). Read `/AGENTS.md` first; this file adds only what is specific to `eval/`.

## Layout
- `apps/trial/`, `apps/sample/` — PySide6 apps and their change/bug versions
- `rq1/` … `rq5/` — measurement scripts and reports
- `nl/` — Turkish NL/step dataset (held-out split is frozen)

## Commands
Dependencies are in `eval/pyproject.toml` (install with `[dev]` for ruff and pytest).
Commands run from the repository root.

```powershell
# setup, once
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e "eval[dev]"

# run an app (the sample app is the one under test; `--screen` opens one screen)
.venv/Scripts/python.exe eval/apps/sample/app.py
.venv/Scripts/python.exe eval/apps/trial/app.py

# lint and format (CI runs both; `spikes/` is excluded)
.venv/Scripts/ruff.exe check eval
.venv/Scripts/ruff.exe format --check eval

# tests (`@pytest.mark.windows` ones skip themselves off Windows)
.venv/Scripts/python.exe -m pytest eval -v
.venv/Scripts/python.exe -m pytest eval/apps/sample/tests -v

# UIA dump; exits non-zero if a control has no AutomationId
.venv/Scripts/python.exe eval/apps/sample/uia_check.py    # also counts controls per screen
.venv/Scripts/python.exe eval/apps/trial/uia_dump.py
```

Each app has its own `README.md` with its screens, its measured AutomationIds and what the
reference scenarios expect of it.

CI (`eval` job, Windows runner) runs ruff and pytest in `eval/`, including the
`@pytest.mark.windows` tests.

## Rules
- Every experiment is reproducible with one documented command.
- Ground-truth files are never edited after an experiment has used them.
- **One module name per tree.** The apps' tests import their own modules by bare name
  (`import windows`), so a name that exists twice under `eval/` shadows itself for a whole
  `pytest eval` run — hence `apps/sample/uia_check.py` beside `apps/trial/uia_dump.py`, and
  `test_sample_uia.py` beside `test_uia.py` (#199, `memory-bank/learnings.md` 2026-11-08).
- Never set a Qt environment variable (`QT_QPA_PLATFORM`) in a test process: the app under
  test is started as a child and inherits it (`learnings.md` 2026-11-12).
