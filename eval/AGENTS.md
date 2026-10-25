# eval/ — Sample apps, experiment versions, measurements, datasets

Owner: hasan (`nl/`: galip). Read `/AGENTS.md` first; this file adds only what is specific to `eval/`.

## Layout
- `apps/trial/`, `apps/sample/` — PySide6 apps and their change/bug versions
- `rq1/` … `rq5/` — measurement scripts and reports
- `nl/` — Turkish NL/step dataset (held-out split is frozen)

## Commands
To be filled in when the module is scaffolded (build, test, lint, run). Until then, ask before inventing tooling.

## Rules
- Every experiment is reproducible with one documented command.
- Ground-truth files are never edited after an experiment has used them.
