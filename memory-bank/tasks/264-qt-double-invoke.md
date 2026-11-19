# #264 A second Click on the same Qt button within 100 ms is lost but reported passed

- Issue: https://github.com/galipdg/AYNA/issues/264
- Owner: hasan · Branch: `hasan/264-qt-double-invoke`
- Started: 2026-11-19 · Last update: 2026-11-19

## Approach
Qt's UIA `Invoke` on a button is `animateClick()` (released after 100 ms; a second call before
that only restarts the timer). The runner now keeps the time of the last `Invoke` per logical
name (`actions.InvokeSpacing`) and, before the next Click on the same target, sleeps what is
left of `INVOKE_GAP_S` = 200 ms. Process-wide default (`runner.INVOKE_SPACING`) because the
client sends one step per `runSteps` call; tests reset it in `agent/tests/conftest.py`.

## Decisions (small, local to this task)
- 2026-11-19 — keyed by logical name, not RuntimeId: within a run a name is one element, it
  needs no COM call, and the fakes have no RuntimeId. A wrong merge costs at most 200 ms.
- 2026-11-19 — only after an `Invoke` (not Toggle/Select/Legacy): those are synchronous.
- 2026-11-19 — 200 ms, not 120: 120 was the first gap measured to work; margin for a busy loop.
- 2026-11-19 — the wait sits just before the action, after the readiness wait, so time already
  spent waiting for the button counts toward the gap.

## Status
- [x] `InvokeSpacing` + runner wiring + 7 unit tests (fake clock)
- [x] Windows test `agent/tests/test_playback_qt_double_click.py` on the sample app's wizard:
      fix passes, and a control without the gap shows the click lost (3/3 runs each, 2026-11-19)
- [x] #62's pre-flight R24 passes 9/9 with the fix; R01–R24 rerun: 23/24 (R14 is #265)
- [ ] PR
- Next step: open the PR, request galip and omer.

## Manual checks
- 2026-11-19 · hasan's machine (agent) · `pytest tests/test_playback_qt_double_click.py` ×3 · pass

## Open issues
- The agent job in CI runs on `windows-latest` without PySide6, so the Windows test skips
  there, like `test_playback_trial_app.py`.

## Handoff

## Outcome (fill when the issue closes)
