# #61 CLI runner skeleton (headless agent)

- Issue: https://github.com/galipdg/AYNA/issues/61
- Owner: hasan · Branch: `hasan/61-cli-runner`
- Started: 2026-11-15 · Last update: 2026-11-15

## Approach

`ayna run`, playing a suite with the agent's own playback and no Electron. **FR-23 is more
precise than the issue's three lines and is the specification I am building to**
(`docs/rs/RS.md`):

> either from the server (`--server URL --suite NAME`) or from a file (`--from-file`). When a
> server is given, it shall authenticate with an API token passed in `AYNA_SERVER_TOKEN` as a
> Bearer token and post the results to that server. It shall exit with **0** when every test
> passes **and every result is delivered**, **1** when a test fails or proposes a repair, and
> **2** on an operational failure (results not delivered, token refused, server unreachable),
> **even if every test passed**.

That last clause is the one worth repeating: a green suite whose results never reached the
server is a **2**, not a 0. A CI job that reported success there would be lying about the record.

### Scope: what is #61 and what is not

- **#61 (this):** `--from-file` and `--server`, the exit codes, and posting results.
- **#66 (Week 9):** JUnit XML. Deliberately **not** built here, even though `.github/suite/run_suite.py`
  (omer's stand-in for this command, #67/PR #249) already writes it. The reporting stays behind
  its own seam so #66 drops in.
- **#51's screenshots:** the agent writes a PNG per step (#54) and the step result carries
  `screenshotPath`. Uploading those is in omer's inbox note for #61 ("upload each screenshot
  after its result with the same retry rules"). Built here only if the rest lands early.

### Decisions taken before writing code

- **No new dependency.** HTTP goes through `urllib.request` from the standard library, not
  `requests` or `httpx`. The agent's dependency list was frozen at #52 and a closed-network
  install is one wheel fewer to carry. Same reasoning as #54's PNG encoder.
- **The suite file keeps `.github/suite/smoke.json`'s shape** for the `--from-file` case:
  `tests[]` with `name`, `scenario`, `targets` and a step document. I told omer so on PR #249.
  Two differences, which are not accidents: with a server the targets come from the repository,
  so `targets` is optional; and `launch`/`window` are the stand-in's way of being its own test
  runner, which this command does not do — it attaches to a window the user names.
- **Playback is used exactly as `run_suite.py` uses it**: `UiaDesktop()` → `setup()` →
  `run_steps()` on **one** thread. `setup()`'s own docstring is "make *this* thread able to read
  UI Automation" and it does the `CoInitializeEx` there, so the "single `ayna-uia` thread" rule
  is really "one thread, the one that was set up". Confirmed while reviewing #249.

## Decisions (small, local to this task)
- 2026-11-15 — build to FR-23's wording, not the issue's summary — the issue omits the token, the
  delivery condition on exit 0, and exit 2 entirely.

## Status
- [x] Branch, task note, contract read (`docs/api/openapi.yaml`, FR-23, UC-14)
- [x] `ayna_cli` package, `ayna_cli*` in `agent/pyproject.toml` (omer's inbox item from #3 --
      **done**) and an `ayna` console script
- [x] `--from-file`, and the exit codes with FR-23's precedence in one function
- [x] `--server`: applications, versions, tests and repository objects in, run created, results
      written, run finished; `AYNA_SERVER_TOKEN` as a Bearer token
- [x] 61 tests (`test_cli_run.py` 24, `test_cli_suite.py` 16, `test_cli_server.py` 25), none
      of which needs Windows or a server. **702 agent tests pass**, ruff clean.
- [x] **Run for real on Windows against the sample app** (below)
- [x] Screenshot upload (#51's `PUT …/screenshot`), omer's inbox request for this issue:
      the PNG goes **after** its result, because the server answers 404 before it. A file
      that is named but gone is logged, not fatal; a server that refuses it is a delivery
      failure and so exit 2. Dead until #248 merges, because `screenshotPath` is #54's.
- [ ] A `--server` run against a real server, which needs the Docker stack up
- Next step: open the PR (`Closes #61`), asking omer about the two readings under Open
  issues (what `--suite NAME` means, and whether the last version is the newest).

## Measurements and manual checks

- 2026-11-15 · hasan · **`ayna run --from-file` against the live sample app** · **pass** ·
  `python -m ayna_cli run --from-file cli-suite.json` with the app on its login screen: the
  four-step SC-14 test passed and the command exited **0**. Against `--bug bug1` the same suite
  exited **1** with
  `step 3: login.statusLabel: name should contain "Hoş geldiniz", it is "Oturum kapatıldı, admin"`.
  Two useful accidents on the way: a stray second app proved the ambiguity guard
  (`2 windows have className 'LoginWindow'; playback never picks one`), and piping the output
  mangled the Turkish, which is now fixed (see below).
- Not yet done: a `--server` run end to end. Every REST path is tested against a fake opener,
  but nothing has talked to the real server.

## Open issues
- **The server has no suite.** FR-23 says `--server URL --suite NAME`, but `docs/api/openapi.yaml`
  has applications, tests and runs — no suite entity, and nothing names a set of tests. For the
  skeleton `NAME` resolves to an **application**, and the command runs that application's tests
  (`GET /api/apps/{appId}/tests`). That is a reading, not a decision: if a suite is meant to be a
  named subset, it is a server change and omer's. Asked on the issue.
- **A run needs an `appVersionId`** (`POST /api/runs`), which nothing on the command line
  supplies. The newest version of the application is used, and `--app-version` overrides it.
  "Newest" is the last of `GET /api/apps/{id}/versions`, which is an assumption about the
  server's order rather than a documented promise -- worth confirming with omer.
- **The `eval` suite flaked twice while this branch was being written** (a modal dialog not yet
  in the tree, then a fixture error), on a branch that touches no `eval` file, and passed 209/209
  on the next run. Same intermittent UIA readiness family already recorded for #69.

## Handoff

- **The exit-code precedence lives in one function**, `exits.exit_code`, and FR-23's third code
  is the one worth protecting: **a green suite whose results were not stored exits 2**, not 0.
  `TestOutcome` keeps `error` (the test could not be played) and `delivery_error` (the server
  refused it) apart all the way to the end for exactly that reason -- collapsing them would
  make a server outage look like a broken application.
- **A test that cannot be played does not stop the suite.** Five outcomes are worth more to a
  CI log than the first one and a stack trace.
- **`run_id` is deliberately not passed to `run_steps`.** #54 opens one screenshot directory per
  call, and this command makes one call per *test*, so it already gets one directory per test.
  The run id only matters to a caller that sends a step at a time (#44's client). Passing it
  would also couple this branch to #248, which is not merged. Revisit when it is.
- **Output is forced to UTF-8** (`_speak_utf8`). Test names and the application's messages are
  Turkish, and a CI job redirects stdout to a pipe where Python falls back to the locale
  encoding -- cp1252 on a Windows runner has no ş or ı, and the command would have died with a
  `UnicodeEncodeError` *while reporting a test result*. A failed test would have looked like a
  crashed runner. Found by piping the output of the bug1 run.
- **`.github/suite/smoke.json`'s shape is pinned by a test** (`test_the_stand_ins_suite_shape_reads_unchanged`),
  inline so it holds whether or not #249 has merged. If the stand-in and this reader ever
  disagree, the nightly job and `ayna run` would run different things.

## Outcome (fill when the issue closes)
