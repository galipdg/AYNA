# The sample app's controlled UI-change versions (#46)

Six versions of the v1 app (`v2a` … `v2f`), five of them making **one kind** of UI change and
the sixth combining all five the way a real release does. They are what RQ4 and the healing
work are measured on (#73 proposes a healed locator, #86 compares gated against auto-applied),
so every control they touch has a **ground truth** saying what it became.

Issue: [#46](https://github.com/galipdg/AYNA/issues/46) · the app: [`README.md`](README.md)

```powershell
.venv/Scripts/python.exe eval/apps/sample/sample_app.py --variant v2a --screen main
.venv/Scripts/python.exe eval/apps/sample/ground_truth.py --write     # regenerate the mapping
.venv/Scripts/python.exe eval/apps/sample/uia_check.py --variant v2e --screen login --table
.venv/Scripts/python.exe -m pytest eval/apps/sample/tests/test_variants.py -v
```

`--variant v1` (the default) is the unchanged app. Every window of a changed version carries
the version in its title -- `AYNA Örnek 1.0-v2a - Giriş` -- while its UIA ClassName stays
`LoginWindow`, so a screenshot says which copy it came from and every existing test and dump
still finds the screen the same way.

## How a version is built, and why it is not a copy of the app

The issue's expected output is six directories, `v2a..v2f`. There is one **change layer**
instead, agreed with the user on 2026-11-15:

| File | What it holds |
|---|---|
| [`variants.py`](variants.py) | The change sets, declarative and free of Qt |
| [`variant_patch.py`](variant_patch.py) | Applies one to a built window, and reports every widget it touched |
| [`ground_truth.py`](ground_truth.py) | Builds each screen twice and writes `ground_truth.json` from the two |
| [`ground_truth.json`](ground_truth.json) | The generated old -> new mapping. **Never edited by hand** |
| `variants.md` | This file: the change log |

Three reasons, in the order they decided it:

1. **The ground truth cannot drift from the app.** Both come out of the same declaration, so a
   change that is in the app is in the mapping, and a mapping row that is not in the app fails
   `tests/test_variants.py`. With six copies they would be two sources of truth that agree
   only as long as someone remembers to edit both.
2. `eval/AGENTS.md` allows a module name **once** in the whole `eval/` tree, with no exception
   for a file that is only ever run (#199 measured what a shadowed module costs: green locally,
   red in CI). Six copies of `windows.py`, `model.py` and `texts.py` would each need a unique
   name, and a fix in the app's rules would have to be made seven times.
3. A reviewer can read a change set. Nobody reads a diff of six trees.

Scope: the three screens the reference scenarios and the healing measurement actually cross --
`login`, `main` (the grid) and `detail`. The settings screen and the wizard are deliberately
untouched, because a change nothing plays over is a change nobody can score.

## What the mapping says

`ground_truth.json` has one row per changed control, keyed by the control's **v1**
`objectName`, with both sides described the way a locator sees them: `automationId`, `name`,
`value`, `className`, `controlType`, `parentPath`, and the layout place (`layoutIndex` or
`cell`). `new: null` means the control is gone.

Two fields are worth knowing before quoting a number from it:

* **`declared`** -- `false` means the change set does not name this control; the change moved it
  anyway. A `QFormLayout` row carries its label, and a row that leaves a form pushes the rows
  below it up. Those rows are in the mapping (`kind: "shifted"` for the ones nothing touched
  but a neighbour's change), so "a mapping for every changed control" means every control whose
  *description* changed -- which is what an index-based locator trips over.
* **`layoutIndex` is not the UIA sibling index.** It is the control's place in its own Qt
  layout, which is what can be read without a display. The mapping deliberately claims nothing
  about a provider's tree order, and the "Measured on Windows" section says why that turned out
  to be the right call.

The **mapping itself** is certain: it is what the patch reports it did. The property values on
each side are derived from the three Qt -> UIA rules measured on this app (README, "What Qt
exposes to UI Automation"), and every row of it is then checked against a real provider by
`tests/test_variant_uia.py` -- which corrected two of them on the first run, see the end of
this file.

## The six versions

### v2a — rename

Captions and accessible names change; every AutomationId stays as it was. The version a
locator that matched on `name` or on the nearest label fails on, and an `automationId` match
survives untouched.

| Control | Kind | What changed |
|---|---|---|
| `login.loginButton` | rename | name Giriş -> Oturum aç |
| `login.userNameLabel` | rename | name Kullanıcı adı -> Kullanıcı kodu |
| `login.userNameInput` | rename | name Kullanıcı adı -> Kullanıcı kodu |
| `main.searchButton` | rename | name Ara -> Sorgula |
| `main.openButton` | rename | name Aç -> Detay |
| `detail.saveButton` | rename | name Kaydet -> Güncelle |
| `detail.emailLabel` | rename | name E-posta -> E-posta adresi |
| `detail.emailInput` | rename | name E-posta -> E-posta adresi |

The input and its label are renamed **together** (`userNameLabel` + `userNameInput`), because
that is how a release renames a field: the caption and the accessible name of the control it
labels say the same thing before and after.

### v2b — move

Controls change place among their siblings. Ids, names and types are untouched, so only a
locator that leaned on an index or on geometry notices.

| Control | Kind | What changed |
|---|---|---|
| `login.loginButton` | move | index 0 -> 2 |
| `login.exitButton` | move | index 2 -> 0 |
| `main.clearButton` | move | cell [0, 3] -> [1, 3] |
| `main.refreshButton` | move | cell [1, 3] -> [0, 3] |
| `detail.departmentCombo` | move | index 2 -> 0 |
| `detail.departmentLabel` | move (dragged) | index 2 -> 0 |
| `detail.emailInput` | shifted (dragged) | index 1 -> 2 |
| `detail.emailLabel` | shifted (dragged) | index 1 -> 2 |
| `detail.nameInput` | shifted (dragged) | index 0 -> 1 |
| `detail.nameLabel` | shifted (dragged) | index 0 -> 1 |

Three moves of three shapes on purpose: a reversed button row (`QHBoxLayout`), two buttons
swapped between grid cells (`QGridLayout`), and a form row that becomes the first row and
pushes four controls down (`QFormLayout`). The last one is why the mapping has `shifted` rows
at all.

### v2c — retype

Five controls become another class, so their UIA ControlType changes.

| Control | Kind | What changed |
|---|---|---|
| `login.headingLabel` | retype | name Kullanıcı girişi -> (empty); QLabel -> QLineEdit (Text -> Edit); value (empty) -> Kullanıcı girişi |
| `login.serverCombo` | retype | QComboBox -> QLineEdit (ComboBox -> Edit) |
| `login.rememberMeCheck` | retype | QCheckBox -> QComboBox (CheckBox -> ComboBox); value (empty) -> Hayır |
| `main.resultCountLabel` | retype | QLabel -> QLineEdit (Text -> Edit) |
| `detail.statusLabel` | retype | QLabel -> QLineEdit (Text -> Edit) |

The first row is the interesting one: a label that becomes a read-only field keeps its string,
but the string **moves out of the Name and into the value**, so a checkpoint reading the Name
now reads nothing while the text is still on screen. The combo box that was a check box is the
other direction: a `Click` step has to become a `Select`.

What is *not* retyped, and why: a control the app reads back through an API the new class does
not have. `detail.notesInput` is read with `toPlainText()`, `main.activeOnlyCheck` and
`detail.activeCheck` with `isChecked()`, `main.cityFilterCombo` and `detail.cityCombo` with
`currentText()`. The retyped five are only ever `setText` or never read at all, so the app
behaves exactly as v1 does -- which `tests/test_variants.py` plays through for every version.

### v2d — reparent

Controls move into new `QGroupBox` containers. In Qt the AutomationId **is** the object chain,
so a re-parent is always an id change as well: there is no way to re-parent a control and keep
its id, and that is the measured fact this version exists to show.

| Control | Kind | What changed |
|---|---|---|
| `login.userNameInput` | reparent | id login.userNameInput -> login.credentialsGroup.userNameInput |
| `login.userNameLabel` | reparent (dragged) | id login.userNameLabel -> login.credentialsGroup.userNameLabel |
| `login.passwordInput` | reparent | id login.passwordInput -> login.credentialsGroup.passwordInput |
| `login.passwordLabel` | reparent (dragged) | id login.passwordLabel -> login.credentialsGroup.passwordLabel |
| `login.forgotPasswordLink` | shifted (dragged) | index 5 -> 6 |
| `login.rememberMeCheck` | shifted (dragged) | index 3 -> 4 |
| `login.serverCombo` | shifted (dragged) | index 2 -> 0 |
| `login.serverLabel` | shifted (dragged) | index 2 -> 0 |
| `login.showPasswordCheck` | shifted (dragged) | index 2 -> 3 |
| `login.statusLabel` | shifted (dragged) | index 6 -> 7 |
| `main.customerGrid` | reparent | id main.customerGrid -> main.resultsGroup.customerGrid; index 2 -> 0 |
| `detail.activeCheck` | reparent | id detail.activeCheck -> detail.flagsGroup.activeCheck; index 2 -> 0 |

The containers are new elements of their own: `credentialsGroup` ("Kimlik bilgileri"),
`resultsGroup` ("Sonuçlar") and `flagsGroup` ("Durum"). `main.customerGrid` is in there because
every grid and row step of step schema v0.2 points at that one control (#147), so this is the
version that says what a re-parented grid costs.

### v2e — id-removed

Six controls lose their AutomationId; their name, type and place stay exactly as they were, so
a locator has nothing left but the name, the label or the position.

| Control | Kind | What changed |
|---|---|---|
| `login.loginButton` | id-removed | id login.loginButton -> login.QPushButton |
| `login.passwordInput` | id-removed | id login.passwordInput -> login.QLineEdit |
| `main.searchButton` | id-removed | id main.searchButton -> main.QPushButton |
| `main.customerGrid` | id-removed | id main.customerGrid -> main.QTableWidget |
| `detail.saveButton` | id-removed | id detail.saveButton -> detail.QPushButton |
| `detail.nameInput` | id-removed | id detail.nameInput -> detail.QLineEdit |

**The id does not disappear -- it becomes the class name.** This version first predicted an
empty AutomationId and the Windows run (2026-11-15) said otherwise: Qt puts the control's
class name in the path where the `objectName` was, so `login.loginButton` becomes
`QApplication.login.QPushButton`. Three consequences, and they are why v2e earns its place in
the set:

* the id is still *there*, so **`uia_check.py --variant v2e` passes**: a check that counts
  controls without an AutomationId cannot see this change at all. #33's second criterion holds
  on a screen where no scenario's locator does;
* the id is no longer the logical name anything was written against;
* and it is **not unique** -- two same-class siblings that both lost their name would share one
  id. None of v2e's six screens has that case, so the collision is reasoned, not measured.

Two of the six are the hard cases for a healer: `passwordInput` and `nameInput` have no visible
text of their own, and `saveButton`'s caption (**Kaydet**) is also the settings screen's save
button.

An id is only ever cleared on a control with no named children of the app's own, because Qt's
id is the whole chain and clearing a container's name would silently take the id off everything
below it. Qt's *own* internals below the control do lose their path -- the grid's
`qt_scrollarea_viewport` is `…QTableWidget.qt_scrollarea_viewport` in v2e -- and that is a real
consequence of removing an id, not an artefact of how this is applied.

### v2f — combined

One release doing all five at once, plus a control that is simply gone.

| Control | Kind | What changed |
|---|---|---|
| `main.searchButton` | rename | name Ara -> Bul |
| `main.openButton` | id-removed | id main.openButton -> (none) |
| `main.clearButton` | move | cell [0, 3] -> [1, 3] |
| `main.refreshButton` | move | cell [1, 3] -> [0, 3] |
| `main.wizardButton` | removed | gone |
| `detail.statusLabel` | retype | QLabel -> QLineEdit (Text -> Edit) |
| `detail.activeCheck` | reparent | id detail.activeCheck -> detail.flagsGroup.activeCheck; index 2 -> 0 |

`main.wizardButton` is the one control in all six versions whose ground-truth counterpart is
`null`: the feature is gone with it, and the right answer for a healer is to **fail the step**,
not to propose the nearest button. A measurement that only scores "did it find something"
would give full marks for proposing `settingsButton` here.

`searchButton` is renamed to a different caption than v2a's (**Bul**, not **Sorgula**), so a
dump cannot be mistaken for the other version's.

## Measured on Windows, 2026-11-15

`tests/every_mapped_control…` in `tests/test_variant_uia.py` reads all six versions off a real
provider -- 17 app launches, every row of `ground_truth.json` -- and it ran here on 2026-11-15:
**23 tests pass**, after four corrections. Three of them changed what the mapping says:

1. **A cleared `objectName` becomes the class name, not nothing** (v2e, above). Measured for
   `QPushButton`, `QLineEdit` and `QTableWidget` on all three screens.
2. **A `QGroupBox` is a `Group`**, and the re-parented controls do hang below it with the longer
   id the mapping predicted (v2d). That one the derivation got right.
3. **A grid's inner elements inherit the grid's AutomationId.** `main.customerGrid`'s Pane and
   its four Headers are not Qt widgets and carry the *grid's* id, so a lookup by id finds six
   elements; the test filters by `uia_check.is_app_widget`, which is the rule the v1 dump
   already used for the window frame's buttons.
4. And one bug of this layer's own: a replacement widget built during `__init__` was given
   `setVisible(old.isVisible())`, which is `False` for every widget of a window that has not
   been shown yet -- so v2c's retyped controls were hidden for good and were not in the tree at
   all. It is `isHidden()` now.

One known deviation from what a real re-release would look like, worth knowing before anyone
scores a sibling index: **a retyped control moves to the end of its parent's UIA tree order**,
because the replacement widget is created last and Qt's tree follows the child order rather
than the layout. An application rebuilt from changed source would keep the control in place.
The ground truth claims nothing about tree order (only `layoutIndex`, which is unchanged by a
retype), so no measurement rests on it -- but a healer scored on "nth child" would see a change
v2c does not declare.
