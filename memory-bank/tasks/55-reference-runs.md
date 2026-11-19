# #55 First end-to-end runs of 10 reference scenarios

- Issue: https://github.com/galipdg/AYNA/issues/55
- Owner: hasan · Branch: `hasan/55-reference-runs`
- Started: 2026-11-17 · Last update: 2026-11-19

## Approach
Build 10 tests on sample app v1.0 (SA) in the editor, run each from the editor (#44 path:
client → server → agent), and log every result and failure cause in `eval/runs/week7.md`.
All 10 are expected to **pass** on the unchanged app, so the same set feeds RQ2 (#69: 10 runs
each) and NFR-26 / G2. Negative scenarios on SA-B (SC-19, SC-21, SC-34) and SC-22 are left for #62.

Draft set (gold steps of the 8 #36 scenarios were already played with `ayna run`, 8/8 pass):

| # | Test | From | Steps (short) |
|---|---|---|---|
| R01 | Login succeeds | SC-14/17, `sample-login-ok` | Type user, Type password, Click login, Verify status contains "admin" |
| R02 | Wrong password | `sample-login-wrong-password` | same with "1234", Verify error text |
| R03 | Settings checkpoint | SC-16 | Click notifications tab, Click e-mail check, Verify checked = true |
| R04 | Search and open (smart wait) | SC-18, `sample-list-search-open` | Type "Yılmaz", Click search, Click open, Verify `detail.nameInput` (cross-window) |
| R05 | Wizard + confirm dialog | SC-20 | Type name, Next, Select "Kalite Güvence", Next, Verify summary, **Click confirmCheck**, Finish, Yes, Verify "Kayıt oluşturuldu: Ayşe Çelik" |
| R06 | Form save | `sample-form-save` | Type name, Type e-mail, Select department, Save, Verify status |
| R07 | Required name | `sample-form-name-required` | Type e-mail, Save, Verify "Ad alanı zorunlu" |
| R08 | City + active filter | `sample-list-city-active` | Select İzmir, Click active only, Search, Verify "Kayıt bulunamadı" |
| R09 | Wait after refresh | `sample-wait-city-refresh` | Select Bursa, Refresh, Wait open button, Verify "1 kayıt bulundu" |
| R10 | Discard changes | C.2 detail form | (main) search "Yılmaz", Open, Type name "Değişti", Back, `discardDialog.yesButton`, Open, Verify name value "Ayşe Yılmaz" |

## Decisions (small, local to this task)
- 2026-11-17 — objects go in by script, tests by hand: NFR-26 measures editor-*built* steps, and
  a script is reproducible for RQ2 resets. Primary sets follow the Spy's `suggestUses` rule, so
  the grid and the three tab items get a Name (Qt shares their AutomationId).
- 2026-11-17 — R10 starts on `main`: with `--screen detail` Back only hides the form (no main
  window), so "list reached" says nothing; reopening and checking the name proves the discard.
- 2026-11-17 — branch merges `hasan/36-sample-objects` (#259) for `sample.json`; the PR is stacked.
- 2026-11-17 — started while #44 is still open: both its PRs (#193, #247) are merged, so running
  from the editor is on `main`; anything missing is logged as a failure cause, not worked around.

- 2026-11-19 — R05 gets `Click wizard.confirmCheck` before Finish, and a final Verify on
  `wizard.statusLabel`. The wizard opens no dialog until the box is ticked (`on_finish`); SC-20 in
  the RS omits it, so its Yes step can never pass (measured, see `eval/runs/week7.md`).
- 2026-11-19 — exact steps of all ten now live in `eval/runs/week7.md`, not here.

## Status
- [x] Branch, task note, board In progress
- [x] Set of 10 agreed with the user (2026-11-17)
- [x] Objects: `eval/apps/sample/load_repository.py` (user's choice over the Spy by hand); 88/88
      loaded into the local server as app "AYNA Örnek Uygulama", version 1.0; rerun creates 0
- [x] `eval/runs/week7.md`: the ten tests with exact steps and start screens, a results table
- [x] Pre-flight 2026-11-19 without server/client (each step a one-step `runSteps` in its
      object's window, the stored primary/fallback): **10/10 pass**; R05 without the tick fails
      at the Yes step. Script was scratch (`preflight55.py`), its method is in `week7.md`.
- [ ] Tests built in the editor by the user (manual check below), then runs, fill `week7.md`
- Next step: user starts server + client, builds R01–R10 in the editor from `week7.md`'s
  table, runs each once; fill the "Editor runs" rows; ticket every failure.

## Manual checks
- (planned) building and running each test in the client is manual, at the Windows machine.
  Setup: `docker compose up -d` (health on `AYNA_SERVER_PORT`, 8081 here), objects already
  loaded (rerun `load_repository.py` only if Neo4j was wiped), `cd client; npm run dev`, app via
  `sample_app.py --screen <start>`. Steps: per test, Testler → Yeni test → steps from
  `week7.md` → Kaydet → Çalıştır. Expected: every step passes. Report: result per test; for a
  failure the step, category and message, the `[agent]` console lines, a screenshot.

## Open issues
- R03 / SC-16: the tab items share one AutomationId; stored with primary {automationId, name}
  (`parentPath` too for "Genel"). 2026-11-19 pre-flight: playback finds and clicks them; the
  editor run is still the real answer.
- R04, R05, R10 cross windows. The client plays each step in its object's window (by the captured
  `windowTitle`; all 88 objects carry one); `ayna run --from-file` cannot (one window per test).
- 2026-11-17: the full `eval` suite had 11 UIA failures (main screen) while two hand-started
  `sample_app.py --screen main` processes were open; not caused by this branch, rerun when closed.

## Handoff

## Outcome (fill when the issue closes)
