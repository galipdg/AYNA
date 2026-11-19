# #62 Build the remaining reference scenarios in the editor

- Issue: https://github.com/galipdg/AYNA/issues/62
- Owner: hasan · Branch: `hasan/62-remaining-scenarios` (stacked on `hasan/55-reference-runs`)
- Started: 2026-11-19 · Last update: 2026-11-19

## Approach
Grow #55's ten (R01–R10) to at least 20 passing on sample app v1.0 with R11–R24, chosen to
cover what R01–R10 do not: the grid (SelectRow, `cell`, `rowCount`, `rowExists`), `enabled`,
the validation messages, Reset, the discard dialog's No, settings save and defaults, the wizard's
own checks, and navigation from the list to settings and the wizard. Fourteen rather than ten,
so the ≥ 20 criterion does not hang on one test. Built in the editor and run from it, same as
#55, ideally in the same Windows sitting. Same start-screen rule as `eval/runs/week7.md`.

Started early (#55 still open) because #55's remaining work is the user's editor session and
these can be pre-flighted the same way; nothing here is built in the editor yet.

| # | Start | Steps |
|---|---|---|
| R11 | `login` | Click `login.loginButton` · Verify `login.statusLabel` name equals "Kullanıcı adı ve şifre zorunlu" |
| R12 | `login` | Click `login.forgotPasswordLink` · Verify `login.statusLabel` name equals "Şifre sıfırlama için sistem yöneticisine başvurun" |
| R13 | `main` | Verify `main.openButton` enabled = no · Click `main.searchButton` · Wait `main.openButton` · Verify `main.openButton` enabled = yes · Verify `main.resultCountLabel` name equals "6 kayıt bulundu" |
| R14 | `main` | Click `main.searchButton` · Wait `main.openButton` · SelectRow `main.customerGrid` {value "Demir", column "Soyad"} · Click `main.openButton` · Verify `detail.nameInput` value equals "Mehmet Demir" |
| R15 | `main` | Select `main.cityFilterCombo` "Ankara" · Click `main.searchButton` · Wait `main.openButton` · Verify `main.customerGrid` rowCount = 2 · Verify `main.customerGrid` cell (row 2, "Ad") equals "Elif" |
| R16 | `main` | Type `main.searchInput` "Kaya" · Click `main.searchButton` · Wait `main.openButton` · Verify `main.customerGrid` rowExists {value "Zeynep"} = yes · Verify cell (row 1, "Durum") equals "Pasif" |
| R17 | `detail` | Type `detail.nameInput` "Ali Veli" · Type `detail.emailInput` "gecersiz" · Click `detail.saveButton` · Verify `detail.statusLabel` name equals "E-posta adresi geçersiz" |
| R18 | `main` | Type `main.searchInput` "Yılmaz" · Click `main.searchButton` · Click `main.openButton` · Type `detail.nameInput` "Değişti" · Click `detail.resetButton` · Verify `detail.nameInput` value equals "Ayşe Yılmaz" |
| R19 | `main` | (as R18 to the Type) · Click `detail.backButton` · Click `discardDialog.noButton` · Verify `detail.nameInput` value equals "Değişti" |
| R20 | `main` | Click `main.settingsButton` · Click `settings.advancedTab` · Select `settings.logLevelCombo` "Ayrıntılı" · Click `settings.saveButton` · Verify `settings.statusLabel` name equals "Ayarlar kaydedildi" |
| R21 | `settings` | Click `settings.advancedTab` · Click `settings.experimentalCheck` · Verify it checked = yes · Click `settings.defaultsButton` · Verify it checked = no · Verify `settings.statusLabel` name equals "Ayarlar varsayılana döndürüldü" |
| R22 | `wizard` | Click `wizard.nextButton` · Verify `wizard.statusLabel` name equals "Ad Soyad alanı zorunlu" · Verify `wizard.stepLabel` name equals "Adım 1 / 3" |
| R23 | `wizard` | Type `wizard.nameInput` "Ayşe Çelik" · Click `wizard.nextButton` · Verify `wizard.stepLabel` name equals "Adım 2 / 3" · Click `wizard.backButton` · Verify `wizard.nameInput` value equals "Ayşe Çelik" |
| R24 | `main` | Click `main.wizardButton` · Type `wizard.nameInput` "Ayşe Çelik" · Click `wizard.nextButton` · Click `wizard.nextButton` · Click `wizard.confirmCheck` · Click `wizard.finishButton` · Click `confirmDialog.yesButton` · Verify `main.customerGrid` cell (row 1, "Soyad") equals "Çelik" · Verify `main.resultCountLabel` name equals "1 kayıt bulundu" |

## Decisions (small, local to this task)
- 2026-11-19 — R14 and R24 stay in the set although they fail today: each fails on a real
  playback bug (#265, #264), and dropping them would hide exactly what the set is for.
- 2026-11-19 — the negative scenarios (SC-19, SC-21, SC-34 on SA-B; SC-22) are not counted
  toward "≥ 20 pass on v1": they are meant to fail, on another build. Built separately.

## Status
- [x] Set of 14 drafted; pre-flight 2026-11-19 (same method as `eval/runs/week7.md`):
      **12/14 pass**. R14 fails at its Verify (opens "Ayşe Yılmaz") → #265. R24 fails at step 5
      (`elementNotFound` on `wizard.confirmCheck`: the second Next was swallowed) → #264.
- [ ] Built in the editor and run (with #55's ten, one sitting)
- Next step: after #55's editor runs, build R11–R24 the same way; re-run R14/R24 once #264/#265 land.

## Manual checks
- (planned) with #55's: build and run in the client at the Windows machine.

## Open issues
- The negative set needs its own home (here or a new issue); SC-22 needs #102 (unexpected window).

## Handoff

## Outcome (fill when the issue closes)
