# #67 CI job runs the sample suite on a Windows runner

- Issue: https://github.com/galipdg/AYNA/issues/67
- Owner: omer · Branch: `omer/67-windows-suite-ci`
- Started: 2026-11-15 · Last update: 2026-11-15 (CLI switch)

## Approach
`.github/workflows/ayna-suite.yml` (nightly, dispatch with a `bug` choice, and PRs touching
`agent/ayna_agent/`, `eval/apps/sample/`, `.github/suite/`). Until the CLI exists (#61, #66, hasan),
`.github/suite/run_suite.py` stands in for `ayna run --from-file suite.json --junit out.xml`: one app
start per test, window by ClassName, steps played with `UiaDesktop.run_steps` (the product's playback),
JUnit XML + job summary. Suite: `.github/suite/smoke.json` (SC-14 login, SC-34 required name).

## Decisions (small, local to this task)
- 2026-11-15 — Skeleton without the CLI (omer's choice): #61/#66 are open; swap to the CLI when it lands.
- 2026-11-15 — Results on the job summary + `junit-*` artifact, no reporter action — no new third-party dependency. A reporter (e.g. dorny/test-reporter) needs the team's OK.
- 2026-11-15 — Nightly/PR `bug-builds` job: bug1 must fail "Login succeeds", bug4 must fail the required-name test (`--expect-failed`); the job fails if a bug slips through. A dispatch with a bug build makes the main job red (criterion 2).
- 2026-11-15 — Login Verify checks "Hoş geldiniz", not SC-14's "admin": bug1's text "Oturum kapatıldı, admin" also contains "admin".
- 2026-11-15 — Suite format is the stand-in's own (`launch`, `window`, `targets`, `steps`); #61 defines the real `suite.json`.

## Status
- [x] runner + 12 unittest tests (macOS, fake player), smoke suite valid against step schema 0.2
- [x] workflow written, YAML parses
- [x] PR #249 opened (Part of #67). First Windows run 2026-11-15: playback right (none 2/2 passed; bug1 failed the login Verify, bug4 the required-name Verify), but every job crashed printing the summary (cp1252 console) → fixed with stdout reconfigure.
- Next step: check the re-run is green on all three suite jobs and the summary shows; then hasan's review.

## Manual checks
- 2026-11-15 · CI (windows-latest) · run 43723769406 · JUnit artifacts right for none/bug1/bug4; jobs red only from the summary print crash · evidence: the run's `junit-*` artifacts

## Open issues
- `workflow_dispatch` shows in the Actions UI only once the file is on `main`.
- Agent playback acts on one window per test; a test that crosses windows needs the CLI (#61).

## Handoff
- Exit codes 0/1/2 as the CLI's. `--app-arg` takes values starting with `--` only as `--app-arg=--bug`.

## Outcome (fill when the issue closes)

## 2026-11-15 — switched to the CLI (branch `omer/67-suite-on-cli`)
- `run_suite.py` and its tests are gone; `.github/suite/ci_suite.py` is the pipeline's part: start each distinct `launch` of the suite once (login + detail windows side by side), run `python -m ayna_cli run --from-file`, job summary + `out/ayna-run.txt` artifact, `--expect-failed` verdict for bug builds.
- Decision: the CLI does not start the AUT (SC-33: the pipeline does), so the harness does — not a CLI option.
- Decision: until #66's `--junit`, the verdict reads the CLI's `pass  NAME` / `FAIL  NAME` lines; `test_ci_suite.py` builds those lines with `ayna_cli.cli._say` itself, so a format change fails the test.
- Criterion 3 (JUnit in the Actions UI) is back to pending until #66: the summary shows the CLI output, not JUnit.
- Checked on macOS: 13 harness tests; a real `ayna run` subprocess exits 2 (no UIA) and the apps are stopped. Windows run: this PR's CI.
- Next step: push and PR on omer's OK; read both jobs; after #66, add `--junit out/junit.xml` and read the XML instead of the lines.

## 2026-11-17 — PR #252 merged; JUnit follow-up (branch `omer/67-suite-junit`)
- PR #252 merged (squash) on hasan's approval. hasan ran all three jobs on Windows: none 2/2 passed, bug1 and bug4 each failed exactly their own test. PR CI also green for the suite jobs. The red `eval` check was the llm-latency CPU flake (0.962 vs 0.95), which this PR does not touch.
- Decision (criterion 3, answered on PR #254): no third-party reporter action. `ci_suite.py` reads `--junit out/junit.xml` with `ayna_cli.junit.summary_of()`, writes a per-test table to the job summary and uploads the XML as an artifact; the `LINE` regex and `_say` import go.
- Done on this branch: the module header says the script needs one environment with both the agent and PySide6 (hasan's review on #252).
- Next step: once #254 merges (it waits for CI, which is blocked by billing), switch `ci_suite.py` to the XML, update its tests and the workflow, open a PR "Closes #67".

## 2026-11-19 — JUnit switch (branch `omer/67-suite-junit`)
- #254 merged. `ci_suite.py` runs `ayna run --junit out/junit.xml`, reads it with `ayna_cli.junit.summary_of()`; the `LINE` regex and the `_say` coupling are gone. The workflow uploads `out/` (XML + log) as `ayna-run-*`.
- Decision: on a bug build only a `failure` counts as caught; an `error` (test not playable) fails the job. No XML with `--expect-failed` → exit 2.
- Decision: `out/junit.xml` is deleted before the run, so an old file never stands in for a run that wrote none.
- Job summary: a `Test | Result` table from the XML, the CLI log folded under `<details>`. That table is criterion 3's "visible in the Actions UI".
- Checked on macOS: 18 harness tests; a real `ayna run` subprocess exits 2 (no UIA), no XML, summary says so.
- Next step: a green run of the PR's suite jobs on Windows (none passes, bug1/bug4 caught, table shows) once Actions works again; then tick the three criteria and merge.
