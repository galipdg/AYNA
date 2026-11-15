# The sample app's bug-injected versions (#47)

Five versions of the v1 app, `bug1` … `bug5`, each with **one real functional bug** a correct
test must catch, and each naming the reference scenario that **must fail** on it. They are what
the negative scenarios are run against, and what tells "the product is broken" apart from "the
test was always going to fail".

Issue: [#47](https://github.com/galipdg/AYNA/issues/47) · the app: [`README.md`](README.md) ·
the UI-change versions: [`variants.md`](variants.md)

```powershell
.venv/Scripts/python.exe eval/apps/sample/sample_app.py --bug bug2 --screen detail
.venv/Scripts/python.exe -m pytest eval/apps/sample/tests/test_bugs.py -v
.venv/Scripts/python.exe -m pytest eval/apps/sample/tests/test_bug_uia.py -v   # Windows
```

`--bug none` (the default) is the correct app. Every window of a bug build carries the version
in its title -- `AYNA Örnek 1.0-bug2 - Müşteri detayı` -- while its UIA ClassName stays
`DetailWindow`, so a screenshot says which build a failure came from and every existing test and
dump still finds the screen the same way.

## Which bug, and which scenario it has to fail

| | Kind | Screen · control | Must fail | The step that fails |
|---|---|---|---|---|
| `bug1` | `wrong-label` | `login` · `login.statusLabel` | **SC-21** · A checkpoint catches a wrong label | Verify login.statusLabel name contains the welcome text |
| `bug2` | `disabled-button` | `detail` · `detail.saveButton` | **SC-19** · A control that never becomes ready times out | Click detail.saveButton with timeoutMs 5000 |
| `bug3` | `wrong-saved-value` | `wizard` · `wizard.summaryLabel` | **SC-20** · Wizard with Select and a confirmation dialog | Verify wizard.summaryLabel name contains 'Kalite Güvence' |
| `bug4` | `missing-validation` | `detail` · `detail.nameInput` | **SC-34** · CLI run from a file fails the CI job on a bug-injected build | Verify detail.statusLabel name equals 'Ad alanı zorunlu' |
| `bug5` | `wrong-navigation` | `login` · `login.loginButton` | **SC-31** · Rejecting all candidates keeps a real bug visible | Type main.searchInput 'Yılmaz' (the step after the login) |

**Four of the five are not invented here.** `docs/rs/scenarios.md` already specifies them, down
to the control: SC-19 wants "the version in which the detail form's Save button stays disabled",
SC-21 "the version that shows a wrong text in the **login** status label", SC-31 "the version in
which logging in opens the wrong screen", SC-34 "the 'missing validation' version".
`tests/test_bugs.py` looks each scenario's id *and title* up in that file, so a renumbered
scenario fails the suite instead of rotting here.

**The fifth has no scenario of its own.** The plan's SA-B row asks for a "wrong saved value",
and the RS never says where. Rather than invent a check nothing runs, it is put where an
existing scenario already catches it: the wizard's summary, which SC-20 verifies contains the
department the author selected. If a scenario for the detail form's saved values is wanted
later, that is galip's call on `docs/rs/` (requested in his inbox) and this version can move
with it; nothing but the row above would change.

## How a version is built, and why it is not five copies of the app

| File | What it holds |
|---|---|
| [`bugs.py`](bugs.py) | The five bugs, declarative and free of Qt: kind, screen, control, scenario, the failing step, the symptom, what is patched, why it is realistic |
| [`bug_patch.py`](bug_patch.py) | Installs one bug, and `reset()` takes it back out |
| `bugs.md` | This file: the bug log |

The same shape and the same three reasons as #46's change layer (see `variants.md`): the
declaration *is* the log, `eval/AGENTS.md` allows a module name once in the whole tree (#199),
and five copies of `windows.py`/`model.py`/`texts.py` would each need a unique name while a fix
in the app's rules would be made six times.

**A bug is installed before the first window exists**, and patches module globals or *class*
methods -- never an instance. Qt binds a slot when `connect` is called, and `windows.py`
connects in `__init__`, so a method replaced on an instance afterwards would leave every
connected signal calling the correct one. It is also closer to what a buggy build is: the defect
is in the code, not in one window. `--bug` is therefore read in `main()` before `open_screen`.

Two consequences worth knowing:

* **A text bug patches `model`, not `texts`.** `model.py` does `from texts import …`, so the
  value was copied into `model`'s namespace at import time and patching `texts.LOGIN_WELCOME`
  would change nothing. `texts.py`'s docstring predicted the wrong-label version would be "a
  one-line change" there -- it is one line, in `model`.
* **`bug_patch.reset()` exists because the patches are process-wide.** `tests/test_bugs.py`
  compares the correct app with a broken one inside one pytest process, so every test undoes
  its bug; without that, the first bug installed would silently infect the rest of the run.

## The five bugs

### bug1 — the wrong label (SC-21)

A successful login shows the wrong text in the login status label: `Oturum kapatıldı, admin`
instead of `Hoş geldiniz, admin!`. Patched: `model.LOGIN_WELCOME`.

The user name is still in the message, so the only difference is the words -- a message constant
edited for one state and not the other, which is the commonest release defect there is. The
label **element is still found**, which is exactly what SC-21 needs: the step's category has to
be "assertion failed", the result has to show expected against actual, and **no healing proposal
may be made**. A version that moved or renamed the label would test the healer instead.

### bug2 — the disabled button (SC-19)

The detail form's Save button is built disabled and nothing ever enables it. Patched:
`windows.DetailWindow.__init__ (the button is disabled after the form is built)`.

The mirror image of SC-18's late control: a wait that cannot succeed. The button stays
**visible** on purpose -- hidden would be element-not-found, which is a different failure
category and a different scenario -- so the Click step waits out its whole `timeoutMs` and fails
on the `enabled` condition. It is the one bug here that playback has to tell apart from a merely
slow application, which it can only do by timing out.

### bug3 — the wrong saved value (SC-20)

The wizard's summary carries the role where the department belongs, so page three summarises the
record with the role twice. Patched: `model.wizard_summary`.

Two arguments of the same shape swapped at the call site: the defect a test with a checkpoint
catches and a test that only clicks does not. SC-20's `Verify wizard.summaryLabel name contains
'Kalite Güvence'` fails while every click in the scenario still passes, which is the point of
having checkpoints at all.

### bug4 — the missing validation (SC-34)

Saving the detail form with an empty name reports `Kayıt kaydedildi` instead of
`Ad alanı zorunlu`, so the form accepts a record it must refuse. Patched:
`model.validate_detail`.

**Exactly one rule is dropped**, as `model.validate_detail`'s own docstring promises: the e-mail
rule keeps working. A version that validated nothing would fail every detail-form test for the
wrong reason, and SC-34's CI job -- which exists to show a bug-injected build turning a CI job
red -- would prove nothing about the required field.

### bug5 — the wrong navigation (SC-31)

A successful login opens the settings screen instead of the customer list. Patched:
`windows.LoginWindow.on_login`.

The welcome message is still the correct one, so the failure of the *next* step cannot be blamed
on the login itself. This is the one bug that **looks** like a recognition failure and is not:
`main.searchInput` really is absent, a healer will offer candidates from the wrong screen, and
SC-31 is about the tester rejecting all of them so the defect stays visible instead of being
healed away. It is the version that makes "never auto-apply" (#73) worth its cost.

## What is checked, and what is not

`tests/test_bugs.py` (25 tests, no display, so macOS runs it) checks both of the issue's
criteria -- five bugs, and every bug naming a scenario that exists in the RS with that title --
and, most importantly, that **every version shows exactly its own bug**: all five symptoms are
read on every version, so a patch that broke something else, or leaked past `reset()` into the
next test, fails the suite.

`tests/test_bug_uia.py` (Windows, 5 app launches) reads each symptom the way playback will read
it: a Name through UI Automation, a Save button's `enabled`, a window that is not there.

**What no test here can claim**: that a *correct AYNA test* catches each bug. That needs the
reference scenarios built in the editor (#62) and played by the agent (#54, #55) against these
builds, and the categories SC-19/SC-21/SC-22/SC-31 ask for come from #63's triage. These
versions are the precondition for those measurements, not the measurement.
