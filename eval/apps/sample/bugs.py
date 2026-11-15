"""The sample app's bug-injected versions, one real functional bug each (#47).

Five versions of the #33 app, `bug1` … `bug5`, each with **one** functional bug a correct test
must catch: a wrong label, a button that stays disabled, a wrong saved value, a validation rule
that is gone, and a login that opens the wrong screen. They are what the negative reference
scenarios are run against, and what tells a broken product apart from a test that was always
going to fail.

**Every bug names the scenario that must fail**, and four of the five are not invented here:
`docs/rs/scenarios.md` already specifies them, down to which control they sit on --

* SC-19 wants "the version in which the detail form's Save button stays disabled",
* SC-21 wants "the version that shows a wrong text in the **login** status label",
* SC-31 wants "the version in which logging in opens the wrong screen",
* SC-34 wants "the 'missing validation' version" of the detail form's required field.

The fifth, the wrong saved value, has no scenario of its own in the RS; it is put where an
existing one catches it -- the wizard's summary (SC-20) -- rather than being given a check
nothing runs. See `bugs.md`.

**Why a bug layer and not five copies of the app**, the same shape as #46's change versions:
the declaration below *is* the bug log, `eval/AGENTS.md` allows a module name once in the whole
tree (#199), and a bug nobody can read in one place is a bug nobody can review. This module
stays free of Qt and of the app's own modules, so the spec is testable anywhere;
`bug_patch.py` does the patching.

**Why the patches are installed before a window exists.** Qt binds a slot when `connect` is
called, so replacing a method on an instance after `__init__` would leave every already
connected signal calling the old one. So a bug version is activated once, before the first
window is built (`sample_app.py --bug bug2`), and it patches module globals and *class*
methods -- which is also closer to what a real buggy build is: the defect is in the code, not
in one instance.
"""

from __future__ import annotations

from dataclasses import dataclass

#: `sample_app.py --bug` for the correct app. Not a key of `BUGS`.
NO_BUG = "none"

# --- bug kinds, as the plan's SA-B row names them ------------------------------------------
WRONG_LABEL = "wrong-label"
DISABLED_CONTROL = "disabled-button"
WRONG_SAVED_VALUE = "wrong-saved-value"
MISSING_VALIDATION = "missing-validation"
WRONG_NAVIGATION = "wrong-navigation"

KINDS = (
    WRONG_LABEL,
    DISABLED_CONTROL,
    WRONG_SAVED_VALUE,
    MISSING_VALIDATION,
    WRONG_NAVIGATION,
)


@dataclass(frozen=True)
class Bug:
    """One functional bug, and the test that has to notice it."""

    id: str
    kind: str
    #: What the code does wrong, in one line.
    summary: str
    #: Where a tester meets it: the screen and the control the symptom shows on.
    screen: str
    control: str
    #: The reference scenario that **must fail** on this version, and its title.
    scenario: str
    scenario_title: str
    #: The step or check of that scenario which is the one that fails.
    must_fail: str
    #: What the failure looks like, so a run report can be read against it.
    symptom: str
    #: What is patched, named so a reviewer can find it.
    patched: str
    #: Why this is a realistic defect rather than a hole punched in the app.
    note: str


BUG1 = Bug(
    id="bug1",
    kind=WRONG_LABEL,
    summary="A successful login shows the wrong text in the login status label.",
    screen="login",
    control="login.statusLabel",
    scenario="SC-21",
    scenario_title="A checkpoint catches a wrong label",
    must_fail="Verify login.statusLabel name contains the welcome text",
    symptom=(
        "the login succeeds and the list screen opens, but the status label reads "
        "'Oturum kapatıldı, admin' instead of 'Hoş geldiniz, admin!'"
    ),
    patched="model.LOGIN_WELCOME",
    note=(
        "A message constant edited for one state and not the other is the commonest "
        "release defect there is. The element is still found, which is what SC-21 needs: "
        "the category has to be 'assertion failed' and no healing may be proposed."
    ),
)

BUG2 = Bug(
    id="bug2",
    kind=DISABLED_CONTROL,
    summary="The detail form's Save button is disabled and nothing ever enables it.",
    screen="detail",
    control="detail.saveButton",
    scenario="SC-19",
    scenario_title="A control that never becomes ready times out",
    must_fail="Click detail.saveButton with timeoutMs 5000",
    symptom=(
        "the form takes input and the button is visible, but it stays greyed out, so the "
        "step waits the whole 5 000 ms and fails on the 'enabled' condition"
    ),
    patched="windows.DetailWindow.__init__ (the button is disabled after the form is built)",
    note=(
        "The mirror image of SC-18's late control: a wait that cannot succeed. It is the "
        "only bug here that playback must distinguish from a slow application, which is why "
        "the button is disabled rather than hidden -- hidden would be element-not-found."
    ),
)

BUG3 = Bug(
    id="bug3",
    kind=WRONG_SAVED_VALUE,
    summary="The wizard's summary carries the role where the department belongs.",
    screen="wizard",
    control="wizard.summaryLabel",
    scenario="SC-20",
    scenario_title="Wizard with Select and a confirmation dialog",
    must_fail="Verify wizard.summaryLabel name contains 'Kalite Güvence'",
    symptom=(
        "page three summarises the record with the role twice, so the department the "
        "author selected on page two is nowhere in the summary"
    ),
    patched="model.wizard_summary",
    note=(
        "Two values of the same shape swapped at the call site -- the defect a test with a "
        "checkpoint catches and a test that only clicks does not. It is the one bug of the "
        "five that no scenario was written for; SC-20's Verify step catches it as it stands, "
        "which is why it is here rather than on the detail form (see bugs.md)."
    ),
)

BUG4 = Bug(
    id="bug4",
    kind=MISSING_VALIDATION,
    summary="The detail form's required-name rule is gone; the e-mail rule still works.",
    screen="detail",
    control="detail.nameInput",
    scenario="SC-34",
    scenario_title="CLI run from a file fails the CI job on a bug-injected build",
    must_fail="Verify detail.statusLabel name equals 'Ad alanı zorunlu'",
    symptom=(
        "saving with an empty name reports 'Kayıt kaydedildi' instead of the required-field "
        "message, so the form accepts a record it must refuse"
    ),
    patched="model.validate_detail",
    note=(
        "Exactly one rule is dropped, as `model.validate_detail`'s own docstring promises: "
        "the e-mail rule has to keep working, or the version would fail every detail-form "
        "test for the wrong reason and SC-34's CI job would prove nothing."
    ),
)

BUG5 = Bug(
    id="bug5",
    kind=WRONG_NAVIGATION,
    summary="A successful login opens the settings screen instead of the customer list.",
    screen="login",
    control="login.loginButton",
    scenario="SC-31",
    scenario_title="Rejecting all candidates keeps a real bug visible",
    must_fail="Type main.searchInput 'Yılmaz' (the step after the login)",
    symptom=(
        "the welcome message appears, but the window that opens is Ayarlar, so every "
        "control of the list screen is missing and the next step cannot resolve its target"
    ),
    patched="windows.LoginWindow.on_login",
    note=(
        "The one bug here that looks like a recognition failure and is not: the element "
        "really is gone, a healer will offer candidates from the wrong screen, and SC-31 is "
        "about the tester rejecting them so the defect stays visible. The welcome message is "
        "still correct, so the failure cannot be blamed on the login itself."
    ),
)

#: Every bug version, in the order `bugs.md` lists them.
BUGS: dict[str, Bug] = {bug.id: bug for bug in (BUG1, BUG2, BUG3, BUG4, BUG5)}

#: `--bug` values: the correct app and the five bug versions.
BUG_CHOICES = (NO_BUG, *BUGS)


def validate() -> list[str]:
    """Everything wrong with the bug set, as messages (empty when sound).

    The issue's two criteria are "at least five bugs" and "for each bug, the scenario that
    must fail is named", so a bug without a scenario, a step or a kind of its own is a failure
    of the deliverable and not a detail -- `tests/test_bugs.py` fails on any message here.
    """
    problems: list[str] = []
    kinds: dict[str, str] = {}
    for bug_id, bug in BUGS.items():
        if bug_id != bug.id:
            problems.append(f"{bug_id}: keyed as {bug_id}, says {bug.id}")
        if bug.kind not in KINDS:
            problems.append(f"{bug.id}: kind {bug.kind!r} is not one of {KINDS}")
        if bug.kind in kinds:
            problems.append(
                f"{bug.id}: same kind as {kinds[bug.kind]}; the five kinds the plan names "
                f"are meant to be one version each"
            )
        kinds[bug.kind] = bug.id
        for field_name in (
            "summary",
            "screen",
            "control",
            "scenario",
            "scenario_title",
            "must_fail",
            "symptom",
            "patched",
            "note",
        ):
            if not getattr(bug, field_name):
                problems.append(f"{bug.id}: {field_name} is empty")
        if not bug.scenario.startswith("SC-"):
            problems.append(f"{bug.id}: {bug.scenario!r} is not an SC-xx id")
        if not bug.control.startswith(bug.screen + "."):
            problems.append(
                f"{bug.id}: control {bug.control!r} is not on screen {bug.screen!r}"
            )
    return problems
