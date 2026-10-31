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

# run the trial app
.venv/Scripts/python.exe eval/apps/trial/app.py

# lint and format (CI runs both; `spikes/` is excluded)
.venv/Scripts/ruff.exe check eval
.venv/Scripts/ruff.exe format --check eval

# tests (`@pytest.mark.windows` ones skip themselves off Windows)
.venv/Scripts/python.exe -m pytest eval/apps/trial/tests -v

# UIA dump; exits non-zero if an app input/button has no AutomationId
.venv/Scripts/python.exe eval/apps/trial/uia_dump.py
```

CI (`eval` job, Windows runner) runs ruff and pytest in `eval/`, including the
`@pytest.mark.windows` tests.

## Rules
- Every experiment is reproducible with one documented command.
- Ground-truth files are never edited after an experiment has used them.
