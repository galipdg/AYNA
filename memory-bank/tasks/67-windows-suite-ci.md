# #67 CI job runs the sample suite on a Windows runner

- Issue: https://github.com/galipdg/AYNA/issues/67
- Owner: omer · Branch: `omer/67-windows-suite-ci`
- Started: 2026-11-15 · Last update: 2026-11-15

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
