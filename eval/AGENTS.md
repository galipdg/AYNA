# eval/ — Sample apps, experiment versions, measurements, datasets

Owner: hasan (`nl/`: galip). Read `/AGENTS.md` first; this file adds only what is specific to `eval/`.

## Layout
- `apps/trial/`, `apps/sample/` — PySide6 apps and their change/bug versions
- `rq1/` … `rq5/` — measurement scripts and reports
- `nl/` — Turkish NL/step dataset (held-out split is frozen)

## Commands
Dependencies live next to what needs them (`eval/apps/trial/requirements.txt`), not in
a repo-wide `pyproject.toml` — that is still an open devops decision.

```powershell
# setup, once
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r eval/apps/trial/requirements.txt

# run the trial app
.venv/Scripts/python.exe eval/apps/trial/app.py

# tests (`@pytest.mark.windows` ones skip themselves off Windows)
.venv/Scripts/python.exe -m pytest eval/apps/trial/tests -v

# UIA dump; exits non-zero if an app input/button has no AutomationId
.venv/Scripts/python.exe eval/apps/trial/uia_dump.py
```

No linter is set up yet; ask before adding one.

## Rules
- Every experiment is reproducible with one documented command.
- Ground-truth files are never edited after an experiment has used them.
