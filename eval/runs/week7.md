# Week 7 — first end-to-end runs of the 10 reference tests (#55)

What this file is: the log of #55. Ten tests of the sample app v1.0 (SA) are built **in the
editor** and run **from the editor** (client → server → agent, #44), and every result and every
failure cause is written down here. All ten are expected to pass on the unchanged app, so the
same set feeds RQ2 (#69, ten runs each) and NFR-26 / G2. The negative scenarios on SA-B
(SC-19, SC-21, SC-34) and SC-22 belong to #62.

## The ten tests

Objects: the 88 objects `eval/apps/sample/load_repository.py` puts into the repository as app
**"AYNA Örnek Uygulama"**, version **1.0** (`eval/nl/objects/sample.json` plus the three
settings tab items). Every object carries its window title, and the client plays each step in
its own object's window, so a test may cross windows (R04, R05, R10).

"Start" is the screen the app is opened on before the run:
`.venv\Scripts\python.exe eval\apps\sample\sample_app.py --screen <start>`. Restart the app
between runs, so no test reads what the previous one left behind.

Editor labels (Turkish UI): Click = *Tıkla*, Type = *Yaz*, Select = *Listeden seç*,
Wait = *Bekle*, Verify = *Kontrol et*; name = *Metin*, value = *Alan içeriği*,
checked = *İşaretli*; equals = *eşittir*, contains = *içerir*.

| # | Test name (in the editor) | From | Start | Steps |
|---|---|---|---|---|
| R01 | Başarılı giriş | SC-14/17, `sample-login-ok` | `login` | Type `login.userNameInput` "admin" · Type `login.passwordInput` "admin" · Click `login.loginButton` · Verify `login.statusLabel` name contains "admin" |
| R02 | Hatalı şifre | `sample-login-wrong-password` | `login` | Type `login.userNameInput` "admin" · Type `login.passwordInput` "1234" · Click `login.loginButton` · Verify `login.statusLabel` name equals "Kullanıcı adı veya şifre hatalı" |
| R03 | Ayarlar sekmesinde kontrol | SC-16 | `settings` | Click `settings.notificationsTab` · Click `settings.emailNotificationsCheck` · Verify `settings.emailNotificationsCheck` checked equals yes |
| R04 | Ara ve aç | SC-18, `sample-list-search-open` | `main` | Type `main.searchInput` "Yılmaz" · Click `main.searchButton` · Click `main.openButton` · Verify `detail.nameInput` value equals "Ayşe Yılmaz" |
| R05 | Sihirbaz ve onay penceresi | SC-20 (one step added, see below) | `wizard` | Type `wizard.nameInput` "Ayşe Çelik" · Click `wizard.nextButton` · Select `wizard.departmentCombo` "Kalite Güvence" · Click `wizard.nextButton` · Verify `wizard.summaryLabel` name contains "Kalite Güvence" · **Click `wizard.confirmCheck`** · Click `wizard.finishButton` · Click `confirmDialog.yesButton` · Verify `wizard.statusLabel` name equals "Kayıt oluşturuldu: Ayşe Çelik" |
| R06 | Formu kaydet | `sample-form-save` | `detail` | Type `detail.nameInput` "Ayşe Çelik" · Type `detail.emailInput` "ayse.celik@ornek.com" · Select `detail.departmentCombo` "Test ve Doğrulama" · Click `detail.saveButton` · Verify `detail.statusLabel` name equals "Kayıt kaydedildi" |
| R07 | Ad zorunlu | `sample-form-name-required` | `detail` | Type `detail.emailInput` "ali@ornek.com" · Click `detail.saveButton` · Verify `detail.statusLabel` name equals "Ad alanı zorunlu" |
| R08 | Şehir ve etkin filtresi | `sample-list-city-active` | `main` | Select `main.cityFilterCombo` "İzmir" · Click `main.activeOnlyCheck` · Click `main.searchButton` · Verify `main.resultCountLabel` name equals "Kayıt bulunamadı" |
| R09 | Yenile ve bekle | `sample-wait-city-refresh` | `main` | Select `main.cityFilterCombo` "Bursa" · Click `main.refreshButton` · Wait `main.openButton` (10 s) · Verify `main.resultCountLabel` name equals "1 kayıt bulundu" |
| R10 | Değişiklikleri at | C.2 detail form | `main` | Type `main.searchInput` "Yılmaz" · Click `main.searchButton` · Click `main.openButton` · Type `detail.nameInput` "Değişti" · Click `detail.backButton` · Click `discardDialog.yesButton` · Click `main.openButton` · Verify `detail.nameInput` value equals "Ayşe Yılmaz" |

**R05 has one step more than SC-20.** The wizard does not open its confirmation dialog until
"Bilgileri onaylıyorum" is ticked (`windows.py`, `WizardWindow.on_finish`; pinned by
`test_the_wizard_will_not_finish_before_the_confirmation_box_is_ticked`). SC-20 as written in
`docs/rs/scenarios.md` leaves the tick out, so its `confirmDialog.yesButton` step can never
pass. Measured below; reported to galip for the RS. The final Verify makes the test prove the
record was created rather than only that Yes was clicked.

**R10 starts on `main`**: opened with `--screen detail`, Back only hides the form and there is
no list to return to, so reopening the record and checking its name is what proves the discard.

## Pre-flight, without the editor (2026-11-19)

Before the editor runs, each test was played the way the client's step player does it
(`client/src/main/stepPlayer.ts`): every step as its own one-step `runSteps`, against the
window its object was captured in (found by title), with exactly the primary and fallback
properties `load_repository.py` stores. No server and no client were involved, so this says
the steps and the objects are right, **not** that the editor path works. Agent from `main` at
`c1d325d`, Windows 11 Pro 10.0.26300, display scaling 125 % (`AppliedDPI` 120). The script is scratch, not
committed; its logic is the paragraph above.

| # | Steps | Result | Notes |
|---|---|---|---|
| R01–R04 | 4, 4, 3, 4 | pass | R03 finds the tab item by `{automationId, name}`, which answers the open question in the task note; R04 crosses to the detail window |
| R05 | 9 | pass | Without the `confirmCheck` step: steps 1–6 pass, step 7 (`confirmDialog.yesButton`) fails, *no window with title 'Kaydı oluştur?' within 60 s* — the dialog never opens |
| R06–R09 | 5, 3, 4, 4 | pass | |
| R10 | 8 | pass | Crosses main → detail → dialog → main → detail |

## Editor runs

Each run: app started on the test's start screen, test opened in the editor, **Çalıştır**.
Fill one row per run. A failed step names its category and message as the result panel shows
them; every failure gets a cause and a ticket (issue number) before #55 closes.

| Date | # | Built in editor | Result | Failed step | Category / message | Cause | Ticket |
|---|---|---|---|---|---|---|---|
| | R01 | | | | | | |
| | R02 | | | | | | |
| | R03 | | | | | | |
| | R04 | | | | | | |
| | R05 | | | | | | |
| | R06 | | | | | | |
| | R07 | | | | | | |
| | R08 | | | | | | |
| | R09 | | | | | | |
| | R10 | | | | | | |

## Failures and their causes

| # | What failed | Cause | Ticket |
|---|---|---|---|
| SC-20 (pre-flight) | The scenario's Yes step, when built as `docs/rs/scenarios.md` writes it | The scenario omits ticking `wizard.confirmCheck`; the app is right | galip's inbox (RS is his); R05 carries the step |
