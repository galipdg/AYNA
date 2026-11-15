# eval/apps/sample — the six-screen sample app (v1.0)

The application under test for everything AYNA measures: recognition, playback, healing and
the reference scenarios. PySide6, Turkish interface, English identifiers.
Issue: [#33](https://github.com/galipdg/AYNA/issues/33).

It exists to be *tested*, not used, which shows in three decisions:

* **Every control carries an AutomationId** — the ids below are the repository's logical
  names (#11, #25) with one prefix removed.
* **Every window title carries the app and its version**, so a screenshot or a snapshot
  says which copy it came from — #46 and #47 ship changed and bug-injected versions of this
  app.
* **Each screen is its own top-level window**, so a test can open the screen it needs
  (`--screen`) instead of clicking its way there, and a snapshot covers one screen (NFR-02).

## Setup (once)

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e "eval[dev]"
```

## Run it — one command, any platform

```powershell
.venv/Scripts/python.exe eval/apps/sample/sample_app.py      # Windows
```
```bash
.venv/bin/python eval/apps/sample/sample_app.py              # macOS, Linux
```

It opens on the login screen; `admin` / `admin` gets in and opens the customer list, which
leads to the other screens. Two options matter:

| Option | What it does |
|---|---|
| `--screen login\|main\|detail\|settings\|wizard` | Open that screen straight away |
| `--search-delay-ms MS` | How long after a search the grid fills and **Aç** becomes enabled (default 3000; `0` fills it at once) |
| `--variant v1\|v2a…v2f` | Run one of #46's controlled UI-change versions (default `v1`, the unchanged app) — see [`variants.md`](variants.md) |

The delay is what SC-18 is built on: playback has to wait for a control to become enabled
rather than sleep for a fixed time.

## The screens

| `--screen` | Window title | ClassName | Interactive controls | What it is there for |
|---|---|---|---|---|
| `login` | `AYNA Örnek 1.0 - Giriş` | `LoginWindow` | 9 | Credentials, and a status label that stays readable after a successful login (SC-14, SC-21) |
| `main` | `AYNA Örnek 1.0 - Müşteriler` | `MainWindow` | 10 | Search, filters and the row-selecting grid (SC-18, grid and row steps) |
| `detail` | `AYNA Örnek 1.0 - Müşteri detayı` | `DetailWindow` | 9 | A form with a required field (SC-34) and a modal dialog on leaving it edited (SC-22) |
| `settings` | `AYNA Örnek 1.0 - Ayarlar` | `SettingsWindow` | 8 per tab | Three tabs; the e-mail-notifications check box is SC-16 |
| `wizard` | `AYNA Örnek 1.0 - Yeni kayıt sihirbazı` | `WizardWindow` | 8 per page | Three pages, Turkish combo items and a confirmation dialog (SC-20) |

Both dialogs are windows of their own, nested under the screen that opened them:
`discardDialog` (`Değişiklikleri at?`) and `confirmDialog` (`Kaydı oluştur?`), each with a
`yesButton` and a `noButton`.

The last two counts are per **tab** and per **page**: a tab that is not selected and a
wizard page that is not showing are not in the UIA tree at all, which is why
`tests/test_screens.py` counts them on the widgets while `uia_check.py` counts what is on
screen.

## What Qt exposes to UI Automation

Measured on PySide6 6.12, Python 3.13, Windows 11; the trial app
(`eval/apps/trial/README.md`) established the rules and `memory-bank/learnings.md` keeps
them.

| Qt side | UIA property | Note |
|---|---|---|
| `objectName` | **AutomationId** | A dotted path over the whole object chain, so renaming a parent changes every id below it |
| `accessibleName` | **Name** | *Replaces* the Name a control would otherwise have |
| Python class name | **ClassName** | `LoginWindow` — how each screen's window is found |

So `accessibleName` is set **only** where there is no useful visible text: inputs, combo
boxes, spin boxes, the grid. Never on a window (it would hide the title), and never on a
label or a button (it would hide the text a checkpoint reads).

Two more measured details:

* A combo box has **no items in the tree until it is expanded**, and its current value is
  the ValuePattern value, not its Name.
* The window frame's Minimize/Maximize/Close buttons have no AutomationId — that is
  Windows, not the app — so every check here looks only at controls whose UIA ClassName
  starts with `Q`.

## The change versions (#46)

Six versions of this app with one kind of UI change each -- renamed captions, moved controls, a
different control type, a new parent, a cleared AutomationId -- plus one combining all five.
They are what the healing work is measured against, and every control they touch has a
generated old -> new mapping in `ground_truth.json`.

```powershell
.venv/Scripts/python.exe eval/apps/sample/sample_app.py --variant v2a --screen main
.venv/Scripts/python.exe eval/apps/sample/ground_truth.py --write      # regenerate the mapping
.venv/Scripts/python.exe eval/apps/sample/uia_check.py --variant v2e --screen login --table
```

Each version's window titles carry it (`AYNA Örnek 1.0-v2a - Giriş`) while the ClassName stays
`LoginWindow`, so everything here still finds the screens the same way. The change log, the
mapping's shape and what the Windows run measured are in [`variants.md`](variants.md); the
change sets themselves are declared in `variants.py`, not copied into six directories, and
`variants.md` says why.

## The acceptance check

One command answers both of #33's control criteria, for every screen, and exits non-zero
when a screen fails:

```powershell
.venv/Scripts/python.exe eval/apps/sample/uia_check.py                      # all screens
.venv/Scripts/python.exe eval/apps/sample/uia_check.py --screen settings --table
.venv/Scripts/python.exe eval/apps/sample/uia_check.py --json               # the tables below
.venv/Scripts/python.exe eval/apps/sample/uia_check.py --attach --screen main
```

Measured on 2026-11-12 (Windows 11, PySide6 6.12.0):

```
OK  login       9 interactive,  21 elements, 0 without an AutomationId
OK  main       10 interactive,  26 elements, 0 without an AutomationId
OK  detail      9 interactive,  24 elements, 0 without an AutomationId
OK  settings    8 interactive,  26 elements, 0 without an AutomationId
OK  wizard      8 interactive,  22 elements, 0 without an AutomationId

5 screen(s), 44 interactive controls in total.
```

## Tests

```powershell
.venv/Scripts/python.exe -m pytest eval/apps/sample/tests -v
```

| File | Needs Windows? | What it holds |
|---|---|---|
| `tests/test_model.py` | no | The rules in `model.py`: login, search, validation, the wizard summary |
| `tests/test_screens.py` | no | Control counts per screen, tab and page, the object names and the titles, on Qt's offscreen platform |
| `tests/test_sample_uia.py` | **yes** (`@pytest.mark.windows`) | #33's criteria through UI Automation, plus the behaviour the scenarios need |
| `tests/test_variants.py` | no | #46's change versions: the change sets, what they do to the widgets, that each changed screen still works, and that `ground_truth.json` is what the generator writes |
| `tests/test_variant_uia.py` | **yes** (`@pytest.mark.windows`) | Every row of `ground_truth.json` against a real provider, 17 app launches |

106 tests, all green on 2026-11-15 (#46 added 49 of them); `pytest eval` from the repository
root is 211 and the CI invocation, `cd eval; ../.venv/Scripts/python.exe -m pytest -q`, is 155.

Two of the UIA tests here are **flaky under load**, both seen once on 2026-11-15 and both green
on a re-run: `test_leaving_an_edited_form_opens_a_modal_dialog_of_its_own[detail]` (the modal
dialog had not reached the tree yet) and a `detail` case that found *two* `DetailWindow`s
because a previous app had been killed but not yet reaped — which is why `kill_process_tree`
now waits for the process. Data for #69 (RQ2, flaky rate), not something to re-run away.

The offscreen platform is chosen in Qt's own argv and **not** with `QT_QPA_PLATFORM`: that
variable is inherited by every process started later in the same pytest run, and both this
app's and the trial app's UIA tests start the real app as a child process, which would then
come up with no window and never be found.

## Module names

`sample_app.py`, `uia_check.py` and `tests/test_sample_uia.py` instead of `app.py`,
`uia_dump.py` and `tests/test_uia.py`: the trial app has files of all three names, the tests
import them by bare module name, and a module name may exist only once in the whole `eval/`
tree — two files with the same name shadow each other for a whole pytest run (#199).

A module that is only ever *run* is not exempt, which cost this PR a red CI run: both apps'
conftests put their own folder first on `sys.path`, and **which one wins depends on how
pytest was started**. `pytest eval` from the repository root walks the folders
alphabetically and the trial app's `from app import …` resolved to the trial app; CI runs
bare `pytest` from `eval/`, which loads the conftests in `testpaths` order, and the same
import resolved to *this* app and broke the trial app's tests. Both invocations are green
now — run the CI one before pushing:

```powershell
cd eval; ../.venv/Scripts/python.exe -m pytest -q    # 69 passed
```

## The ids, as measured

Generated from `uia_check.py --json`, never typed by hand — rerun it after any rename. A
control that is not showing (an unselected tab, a hidden wizard page) is not in the tree, so
those rows are missing here by design. Qt's own `qt_tabwidget_stackedwidget` level in the
settings ids is Qt's, not ours: a `QTabWidget` cannot avoid it, which is why the wizard
shows and hides its pages in place instead.

### `--screen login` — Giriş (`LoginWindow`)

| ControlType | AutomationId | UIA Name | ClassName |
|---|---|---|---|
| Text | `QApplication.login.headingLabel` | Kullanıcı girişi | `QLabel` |
| Text | `QApplication.login.userNameLabel` | Kullanıcı adı | `QLabel` |
| Edit | `QApplication.login.userNameInput` | Kullanıcı adı | `QLineEdit` |
| Text | `QApplication.login.passwordLabel` | Şifre | `QLabel` |
| Edit | `QApplication.login.passwordInput` | Şifre | `QLineEdit` |
| Text | `QApplication.login.serverLabel` | Sunucu | `QLabel` |
| ComboBox | `QApplication.login.serverCombo` | Sunucu | `QComboBox` |
| CheckBox | `QApplication.login.showPasswordCheck` | Şifreyi göster | `QCheckBox` |
| CheckBox | `QApplication.login.rememberMeCheck` | Beni hatırla | `QCheckBox` |
| Button | `QApplication.login.loginButton` | Giriş | `QPushButton` |
| Button | `QApplication.login.clearButton` | Temizle | `QPushButton` |
| Button | `QApplication.login.exitButton` | Çıkış | `QPushButton` |
| Button | `QApplication.login.forgotPasswordLink` | Şifremi unuttum | `QPushButton` |
| Text | `QApplication.login.statusLabel` | (empty) | `QLabel` |

### `--screen main` — Müşteriler (`MainWindow`)

| ControlType | AutomationId | UIA Name | ClassName |
|---|---|---|---|
| Text | `QApplication.main.headingLabel` | Müşteri listesi | `QLabel` |
| Text | `QApplication.main.searchLabel` | Müşteri ara | `QLabel` |
| Edit | `QApplication.main.searchInput` | Müşteri ara | `QLineEdit` |
| Button | `QApplication.main.searchButton` | Ara | `QPushButton` |
| Button | `QApplication.main.clearButton` | Temizle | `QPushButton` |
| Text | `QApplication.main.cityLabel` | Şehir | `QLabel` |
| ComboBox | `QApplication.main.cityFilterCombo` | Şehir | `QComboBox` |
| CheckBox | `QApplication.main.activeOnlyCheck` | Sadece etkin kayıtlar | `QCheckBox` |
| Button | `QApplication.main.refreshButton` | Yenile | `QPushButton` |
| Table | `QApplication.main.customerGrid` | Müşteri listesi | `QTableWidget` |
| Text | `QApplication.main.resultCountLabel` | (empty) | `QLabel` |
| Button | `QApplication.main.openButton` | Aç | `QPushButton` |
| Button | `QApplication.main.settingsButton` | Ayarlar | `QPushButton` |
| Button | `QApplication.main.wizardButton` | Yeni kayıt sihirbazı | `QPushButton` |

### `--screen detail` — Müşteri detayı (`DetailWindow`)

| ControlType | AutomationId | UIA Name | ClassName |
|---|---|---|---|
| Text | `QApplication.detail.headingLabel` | Müşteri bilgileri | `QLabel` |
| Text | `QApplication.detail.nameLabel` | Ad Soyad | `QLabel` |
| Edit | `QApplication.detail.nameInput` | Ad Soyad | `QLineEdit` |
| Text | `QApplication.detail.emailLabel` | E-posta | `QLabel` |
| Edit | `QApplication.detail.emailInput` | E-posta | `QLineEdit` |
| Text | `QApplication.detail.departmentLabel` | Departman | `QLabel` |
| ComboBox | `QApplication.detail.departmentCombo` | Departman | `QComboBox` |
| Text | `QApplication.detail.cityLabel` | Şehir | `QLabel` |
| ComboBox | `QApplication.detail.cityCombo` | Şehir | `QComboBox` |
| Text | `QApplication.detail.notesLabel` | Notlar | `QLabel` |
| Edit | `QApplication.detail.notesInput` | Notlar | `QPlainTextEdit` |
| Group | `QApplication.detail.notesInput.qt_scrollarea_viewport` | (empty) | `QWidget` |
| CheckBox | `QApplication.detail.activeCheck` | Etkin | `QCheckBox` |
| Button | `QApplication.detail.saveButton` | Kaydet | `QPushButton` |
| Button | `QApplication.detail.resetButton` | Sıfırla | `QPushButton` |
| Button | `QApplication.detail.backButton` | Geri | `QPushButton` |
| Text | `QApplication.detail.statusLabel` | (empty) | `QLabel` |

### `--screen settings` — Ayarlar (`SettingsWindow`)

| ControlType | AutomationId | UIA Name | ClassName |
|---|---|---|---|
| Group | `QApplication.settings.tabs` | (empty) | `QTabWidget` |
| Pane | `QApplication.settings.tabs.qt_tabwidget_stackedwidget` | (empty) | `QStackedWidget` |
| Group | `QApplication.settings.tabs.qt_tabwidget_stackedwidget.generalTab` | (empty) | `QWidget` |
| Text | `QApplication.settings.tabs.qt_tabwidget_stackedwidget.generalTab.themeLabel` | Tema | `QLabel` |
| ComboBox | `QApplication.settings.tabs.qt_tabwidget_stackedwidget.generalTab.themeCombo` | Tema | `QComboBox` |
| Text | `QApplication.settings.tabs.qt_tabwidget_stackedwidget.generalTab.languageLabel` | Dil | `QLabel` |
| ComboBox | `QApplication.settings.tabs.qt_tabwidget_stackedwidget.generalTab.languageCombo` | Dil | `QComboBox` |
| Text | `QApplication.settings.tabs.qt_tabwidget_stackedwidget.generalTab.timeoutLabel` | Zaman aşımı (sn) | `QLabel` |
| Spinner | `QApplication.settings.tabs.qt_tabwidget_stackedwidget.generalTab.timeoutSpin` | Zaman aşımı (sn) | `QSpinBox` |
| Text | `QApplication.settings.tabs.qt_tabwidget_stackedwidget.generalTab.fontSizeLabel` | Yazı boyutu | `QLabel` |
| Spinner | `QApplication.settings.tabs.qt_tabwidget_stackedwidget.generalTab.fontSizeSpin` | Yazı boyutu | `QSpinBox` |
| CheckBox | `QApplication.settings.tabs.qt_tabwidget_stackedwidget.generalTab.startupCheck` | Açılışta başlat | `QCheckBox` |
| Tab | `QApplication.settings.tabs.qt_tabwidget_tabbar` | Genel | `QTabBar` |
| Button | `QApplication.settings.saveButton` | Kaydet | `QPushButton` |
| Button | `QApplication.settings.closeButton` | Kapat | `QPushButton` |
| Text | `QApplication.settings.statusLabel` | (empty) | `QLabel` |

### `--screen wizard` — Yeni kayıt sihirbazı (`WizardWindow`)

| ControlType | AutomationId | UIA Name | ClassName |
|---|---|---|---|
| Text | `QApplication.wizard.stepLabel` | Adım 1 / 3 | `QLabel` |
| Text | `QApplication.wizard.pageLabel` | Kişi bilgileri | `QLabel` |
| Text | `QApplication.wizard.nameLabel` | Ad Soyad | `QLabel` |
| Edit | `QApplication.wizard.nameInput` | Ad Soyad | `QLineEdit` |
| Text | `QApplication.wizard.emailLabel` | E-posta | `QLabel` |
| Edit | `QApplication.wizard.emailInput` | E-posta | `QLineEdit` |
| Text | `QApplication.wizard.phoneLabel` | Telefon | `QLabel` |
| Edit | `QApplication.wizard.phoneInput` | Telefon | `QLineEdit` |
| Text | `QApplication.wizard.recordTypeLabel` | Kayıt türü | `QLabel` |
| ComboBox | `QApplication.wizard.recordTypeCombo` | Kayıt türü | `QComboBox` |
| Button | `QApplication.wizard.backButton` | Geri | `QPushButton` |
| Button | `QApplication.wizard.nextButton` | İleri | `QPushButton` |
| Button | `QApplication.wizard.finishButton` | Bitir | `QPushButton` |
| Button | `QApplication.wizard.cancelButton` | İptal | `QPushButton` |
| Text | `QApplication.wizard.statusLabel` | (empty) | `QLabel` |
