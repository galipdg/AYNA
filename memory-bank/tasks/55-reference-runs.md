# #55 First end-to-end runs of 10 reference scenarios

- Issue: https://github.com/galipdg/AYNA/issues/55
- Owner: hasan · Branch: `hasan/55-reference-runs`
- Started: 2026-11-17 · Last update: 2026-11-17

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
| R05 | Wizard + confirm dialog | SC-20 | Type name, Next, Select "Kalite Güvence", Next, Verify summary, Finish, Yes |
| R06 | Form save | `sample-form-save` | Type name, Type e-mail, Select department, Save, Verify status |
| R07 | Required name | `sample-form-name-required` | Type e-mail, Save, Verify "Ad alanı zorunlu" |
| R08 | City + active filter | `sample-list-city-active` | Select İzmir, Click active only, Search, Verify "Kayıt bulunamadı" |
| R09 | Wait after refresh | `sample-wait-city-refresh` | Select Bursa, Refresh, Wait open button, Verify "1 kayıt bulundu" |
| R10 | Discard changes | C.2 detail form | Type name, Back, Click `discardDialog.yesButton`, Verify list screen reached |

## Decisions (small, local to this task)
- 2026-11-17 — started while #44 is still open: both its PRs (#193, #247) are merged, so running
  from the editor is on `main`; anything missing is logged as a failure cause, not worked around.

## Status
- [x] Branch, task note, board In progress
- [ ] Set of 10 agreed with the user
- [ ] Stack up on Windows (Docker Desktop was not running on 2026-11-17)
- [ ] Repository objects for SA, tests built in the editor, runs, `eval/runs/week7.md`
- Next step: agree the set and how objects get into the repository; start Docker Desktop.

## Manual checks
- (planned) building and running each test in the client is manual, at the Windows machine.

## Open issues
- R03 / SC-16: the settings tab items share one AutomationId (#259, open question to galip), so
  `settings.notificationsTab` may not be addressable. If so, it is a failure with a cause and a ticket.
- R04 ends with a Verify on another window (`detail`); `ayna run` could not play it from one window.

## Handoff

## Outcome (fill when the issue closes)
