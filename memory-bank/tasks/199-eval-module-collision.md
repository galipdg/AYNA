# #199 eval: two different uia_dump.py modules collide, so `pytest eval/` fails

- Issue: https://github.com/galipdg/AYNA/issues/199
- Owner: hasan · Branch: `hasan/199-eval-module-collision`
- Started: 2026-11-08 · Last update: 2026-11-08

## Approach

Renamed `eval/spikes/uia_dump.py` to `eval/spikes/uia_tree_dump.py` (option 1 in the issue), with
its test file (`test_uia_tree_dump.py`) and every reference in `spikes/` and in
`agent/ayna_agent/model.py`'s comment. The trial app's `eval/apps/trial/uia_dump.py` keeps its
name: it is the one named in `eval/AGENTS.md` and `apps/trial/README.md` as a documented command.

## Decisions (small, local to this task)

- 2026-11-08 — **`--import-mode=importlib` (my preferred option 2 in the issue) does not fix this;
  withdrawn.** Measured: `pytest eval -q --import-mode=importlib` still fails collection with
  `ImportError: cannot import name 'MAX_DEPTH' from 'uia_dump'`. The clash is not between the two
  *test* modules, which is what the import mode governs, but between two *source* modules of the
  same name imported by other source modules (`spikes/uia_probe.py` and `spikes/kp_state.py` do
  `from uia_dump import …`). What puts the wrong one first is
  `apps/trial/tests/conftest.py`'s `sys.path.insert(0, …/apps/trial)`, which lasts for the whole
  process. Adding `pythonpath` for both folders would only re-create the ambiguity, so a unique
  module name is the fix. Option 3 (packages everywhere) would also work and is more invasive.
- 2026-11-08 — Renamed the spike, not the trial script: the spike tree is throwaway scripts and
  ruff-excluded, while the trial script is in two documented command lists.
- 2026-11-08 — `uia-dumps/*.json` do not record the script name, so no result file had to change
  (and they must not be edited after an experiment used them).

## Status

- [x] Reproduced on Windows: `pytest eval` aborts in collection; the two trees pass separately
- [x] Renamed the module and its test, rewrote every reference
- [x] `pytest eval` → **68 passed** (12 trial + 56 spikes); bare `pytest` in `eval/` (the CI
      command) → 12 passed; `ruff check .` and `ruff format --check .` clean; the renamed script
      still runs (`uia_tree_dump.py stats` prints the four-dump table)
- [ ] Decide whether `testpaths` should also cover `spikes/`, which needs omer (it changes what the
      CI `eval` job runs, because CI runs bare `pytest`)
- Next step: ask omer about `testpaths`, then open the PR with `Closes #199`.

## Manual checks

None needed: everything here is verified by the test suites above, on Windows.

## Open issues

- **`spikes/` tests are in no CI job.** CI runs bare `pytest` in `eval/`, and
  `testpaths = ["apps/trial/tests"]`, so the 56 spike tests never run on a runner. Widening
  `testpaths` to `["apps/trial/tests", "spikes"]` would fix that without touching `.github/`,
  but it changes what omer's job runs, so it is his call (asked in the PR).
- `docs/sdd/SDD.md` §RQ1 names `eval/spikes/uia_dump.py stats` as the population source for RQ1.
  That file is omer's; the path needs updating there. Noted in his inbox.

## Handoff

The collision is a `sys.path` property of the whole pytest process, not of one test file: if
anyone adds a second module with a name that already exists anywhere under `eval/`, this comes
back. There is no guard for it in CI.

## Outcome (fill when the issue closes)
