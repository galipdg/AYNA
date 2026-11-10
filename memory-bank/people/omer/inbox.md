# Inbox — Ömerfaruk Sarıbal (`omer`)

Anyone may append; only omer removes handled items. Format:
`- YYYY-MM-DD · from <id> · #<issue> · <request or note>`

- 2026-11-08 · from hasan · #199 · **Two things from the `eval/` module-name collision fix (PR to follow, branch `hasan/199-eval-module-collision`).** (1) `eval/spikes/uia_dump.py` is now `eval/spikes/uia_tree_dump.py`; `docs/sdd/SDD.md` §RQ1 names the old path as the population source for RQ1, and that file is yours — please change the path there (the trial app's `eval/apps/trial/uia_dump.py` keeps its name, so only the `spikes/` one moved). (2) **Your call:** the 56 tests under `eval/spikes/` run in no CI job, because the `eval` job runs bare `pytest` and `eval/pyproject.toml` has `testpaths = ["apps/trial/tests"]`. Widening it to `["apps/trial/tests", "spikes"]` would cover them with no change in `.github/`, but it changes what your job runs — and those are throwaway spike scripts, excluded from ruff, so a broken spike would turn CI red. Say which you prefer on the PR and I will do it there; I left `testpaths` alone for now.
