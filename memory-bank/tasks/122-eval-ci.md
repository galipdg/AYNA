# #122 eval: pyproject + ruff + CI job

- Issue: https://github.com/galipdg/AYNA/issues/122
- Owner: omer (CI job) + hasan (`eval/` part) · Branch: `omer/122-eval-ci`
- Started: 2026-10-31 · Last update: 2026-10-31

## Approach
One `eval/pyproject.toml` for the whole module, like `agent/` and `ai/`: not a package
(`packages = []`), it only declares dependencies plus `[dev]` (pytest, ruff ~0.17.2).
CI job `eval` on `windows-latest`, same steps as `agent` (ruff check, ruff format
--check, pytest), so the trial app's `@pytest.mark.windows` UIA tests run too.

## Decisions (small, local to this task)
- 2026-10-31 — omer does hasan's `eval/` part too (user's choice): hasan had not
  started it and Week 2 ends 2 Nov. hasan is asked to review the PR.
- 2026-10-31 — Commands stay run from the repository root with the root `.venv`
  (`pip install -e "eval[dev]"`), so hasan's README/AGENTS commands barely change.
- 2026-10-31 — `spikes/` excluded from ruff (as in `ai/`); pytest `testpaths` is only
  `apps/trial/tests`: `spikes/uia_dump.py` and `apps/trial/uia_dump.py` share a module
  name and would clash in one pytest session. Spike tests stay on `unittest`.
- 2026-10-31 — `jsonschema~=4.26` declared for `nl/check_pairs.py` (galip's script still
  documents `ai/.venv`; both work). `pywinauto` only on `win32`, so macOS installs.
- 2026-10-31 — ruff `src = [".", "apps/trial"]` so `app`/`uia_dump` sort as first-party
  and the author's import groups stay as they are.

## Status
- [x] `eval/pyproject.toml`, `requirements.txt` removed, ruff clean (2 unused `noqa`)
- [x] `eval` job in `.github/workflows/ci.yml`
- [x] macOS check 2026-10-31 (fresh py3.11 venv): ruff check/format clean, pytest
      7 passed 1 skipped, spike unittest 24 OK, `check_pairs.py --min-styles 0` OK
- [x] PR #167 (`Closes #122`, review requested from hasan); CI green 2026-10-31
      (run 41190050901): `eval` job 12 passed, the 5 `test_uia.py` UIA tests included
- Next step: answer hasan's review on #167; nothing else left.

## Manual checks
- none needed: the CI job itself is the check.

## Open issues
- none. Learned for #67: GitHub-hosted `windows-latest` can launch a PySide6 window and
  drive it with pywinauto UIA (the `eval` job does it in ~3 s).

## Handoff
- Not touched on purpose: hasan's task note `tasks/9-*.md` and `tasks/8-*.md` still say
  `requirements.txt`; hasan was told in his inbox.
