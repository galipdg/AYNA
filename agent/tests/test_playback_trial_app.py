"""#26's acceptance criteria, against the real trial app on a real desktop.

> - 3-step login test on the trial app passes 10/10 runs
> - No coordinates are stored in the test

The first needs Windows, UI Automation and the app on screen, so it is
`@pytest.mark.windows`. It also needs a Python that can import PySide6, which the agent's own
environment does not have -- the trial app belongs to `eval/` (#9) and so does its dependency.
Rather than pull a 100 MB GUI toolkit into the agent, the fixture **looks for** an interpreter
that has it (this one, then the repository's `.venv`) and skips with the reason when there is
none. So this file passes on a developer's Windows machine and skips in CI; the unit tests in
`test_playback_runner.py` are what CI has to rely on, and they cover every rule except "a real
provider answers these patterns".

The second criterion is structural and runs everywhere.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

from ayna_agent.playback.resolve import MATCHABLE
from ayna_agent.playback.runner import run_steps
from ayna_agent.recognition.uia import UiaDesktop

REPO = Path(__file__).resolve().parents[2]
TRIAL_APP = REPO / "eval" / "apps" / "trial" / "app.py"

WINDOW_TITLE = "AYNA Trial - Login"
#: `eval/apps/trial/app.py`: the credentials it accepts and what it says afterwards.
USERNAME = PASSWORD = "admin"
WELCOME = "Welcome, admin!"

#: Long enough for a cold PySide6 import on a laptop; the wait ends as soon as the window is
#: there, so a fast machine does not pay it.
START_TIMEOUT_S = 60.0

TARGETS = {
    "login.userNameInput": {
        "properties": {"automationId": "QApplication.loginWindow.usernameInput"},
        "fallback": {"nearestLabel": "Username", "controlType": "Edit"},
    },
    "login.passwordInput": {
        "properties": {"automationId": "QApplication.loginWindow.passwordInput"},
        "fallback": {"nearestLabel": "Password", "controlType": "Edit"},
    },
    "login.loginButton": {
        "properties": {"automationId": "QApplication.loginWindow.loginButton"},
        "fallback": {"name": "Login", "controlType": "Button"},
    },
}

LOGIN_STEPS = {
    "version": "0.1",
    "steps": [
        {"keyword": "Type", "target": "login.userNameInput", "value": USERNAME},
        {"keyword": "Type", "target": "login.passwordInput", "value": PASSWORD},
        {"keyword": "Click", "target": "login.loginButton"},
    ],
}

#: The same three steps with empty values: clears both fields and submits, which puts the
#: status label into a known state before a run is measured.
RESET_STEPS = {
    "version": "0.1",
    "steps": [
        {"keyword": "Type", "target": "login.userNameInput", "value": ""},
        {"keyword": "Type", "target": "login.passwordInput", "value": ""},
        {"keyword": "Click", "target": "login.loginButton"},
    ],
}


# --- "No coordinates are stored in the test" -----------------------------------------------


def test_no_coordinate_can_be_stored_in_a_test():
    """The second acceptance criterion, as a property of the contract rather than of this file.

    A step names its target by logical name only (step schema v0), and a target's property set
    cannot carry geometry: `bounds` and `dpi` are in `model.NEVER_MATCH`, so playback refuses
    them (`resolve.MATCHABLE`) and so does the server (`RepoObjectService.NEVER_MATCH`). There
    is therefore nowhere for a coordinate to be stored, which is stronger than this test
    document happening not to have one.
    """
    assert "bounds" not in MATCHABLE
    assert "dpi" not in MATCHABLE
    assert "nativeWindowHandle" not in MATCHABLE

    text = json.dumps([LOGIN_STEPS, TARGETS])
    for forbidden in ("bounds", "dpi", "nativeWindowHandle", "x", "y"):
        assert f'"{forbidden}"' not in text
    for step in LOGIN_STEPS["steps"]:
        assert set(step) <= {
            "id",
            "keyword",
            "target",
            "value",
            "checkpoint",
            "timeoutMs",
        }


# --- the real desktop ----------------------------------------------------------------------


def _python_with_pyside() -> str | None:
    """An interpreter that can import PySide6: this one, or the repository's `.venv`."""
    candidates = [sys.executable, str(REPO / ".venv" / "Scripts" / "python.exe")]
    for python in candidates:
        if not Path(python).exists():
            continue
        try:
            done = subprocess.run(
                [python, "-c", "import PySide6"],
                capture_output=True,
                timeout=120,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        if done.returncode == 0:
            return python
    return None


@pytest.fixture(scope="module")
def desktop():
    backend = UiaDesktop()
    backend.setup()
    if not backend._ready:
        pytest.skip(f"no UI Automation here: {backend._unavailable}")
    yield backend
    backend.close()


@pytest.fixture(scope="module")
def trial_window(desktop):
    """Start the trial app, yield its window handle, and close it afterwards."""
    if not TRIAL_APP.exists():
        pytest.skip(f"the trial app is not in this checkout: {TRIAL_APP}")
    python = _python_with_pyside()
    if python is None:
        pytest.skip(
            "no interpreter here can import PySide6, which the trial app needs; "
            'install it in the repository\'s .venv (`pip install -e "eval[dev]"`)'
        )

    app = subprocess.Popen([python, str(TRIAL_APP)])
    try:
        deadline = time.monotonic() + START_TIMEOUT_S
        handle = None
        while time.monotonic() < deadline:
            if app.poll() is not None:
                pytest.skip(f"the trial app exited at once with code {app.returncode}")
            for window in desktop.list_windows():
                if window["title"] == WINDOW_TITLE:
                    handle = window["handle"]
                    break
            if handle is not None:
                break
            time.sleep(0.25)
        if handle is None:
            pytest.fail(
                f"the trial app did not show a window titled {WINDOW_TITLE!r} within "
                f"{START_TIMEOUT_S:.0f} s"
            )
        yield handle
    finally:
        app.terminate()
        try:
            app.wait(timeout=10)
        except subprocess.TimeoutExpired:
            app.kill()


#: `eval/apps/trial/app.py` again: what it says when either field is empty. Used to reset the
#: status label between runs, so each of the ten runs proves its own login instead of reading
#: the message the run before it left there.
EMPTY_MESSAGE = "Username and password are required"

#: How long the application may take to react to a click. **A passed Click does not mean the
#: application has finished reacting**: `Invoke()` returns as soon as the provider accepts it,
#: and Qt updates the label on its own event loop afterwards. The first draft of this test read
#: the label immediately and saw it empty on the first run only -- runs 2 to 10 were reading
#: the message the previous run had left. That is a finding for #40, where a checkpoint has to
#: wait for the *assertion* to come true and not only for its element to exist.
REACTION_TIMEOUT_S = 5.0


def _descriptor(desktop: UiaDesktop, handle: int, automation_id: str):
    from ayna_agent.model import describe_tree

    nodes, infos = desktop.read_tree(handle)
    for descriptor, info in zip(describe_tree(nodes), infos, strict=True):
        if descriptor.automation_id == automation_id:
            return descriptor, info
    return None, None


def _status_text(desktop: UiaDesktop, handle: int) -> str | None:
    """What the app's status label says now."""
    descriptor, _info = _descriptor(
        desktop, handle, "QApplication.loginWindow.statusLabel"
    )
    return None if descriptor is None else descriptor.name


def _wait_for_status(desktop: UiaDesktop, handle: int, expected: str) -> str:
    """Poll the status label until it says `expected`, or give up and return what it says.

    Returning rather than asserting keeps the failure message in the test that asked, with the
    run number in it.
    """
    deadline = time.monotonic() + REACTION_TIMEOUT_S
    text = _status_text(desktop, handle) or ""
    while text != expected and time.monotonic() < deadline:
        time.sleep(0.1)
        text = _status_text(desktop, handle) or ""
    return text


def _field_value(desktop: UiaDesktop, handle: int, automation_id: str) -> str | None:
    """The text *in* a field, which for a Qt line edit is its ValuePattern, not its Name.

    Worth spelling out, because the descriptor's `name` for these inputs is `"Username"` /
    `"Password"` -- the accessible name Qt derives from the label, not what the user typed. A
    test that read `name` to check typing would pass while typing nothing.
    """
    from ayna_agent.playback.actions import uia_patterns

    _found, info = _descriptor(desktop, handle, automation_id)
    if info is None:
        return None
    pattern = uia_patterns(info.element, "Value")
    return None if pattern is None else pattern.CurrentValue


@pytest.mark.windows
def test_the_three_step_login_passes_ten_times_out_of_ten(desktop, trial_window):
    """#26's first acceptance criterion, end to end on the real application.

    Each run is checked twice: every step reports `passed`, **and** the app's own status label
    says the login succeeded. The second check is the one that matters -- three passed steps
    only prove that the agent thought it acted, while "Welcome, admin!" proves the application
    received a user name, a password and a click.
    """
    runs = 10
    read = lambda: desktop.read_tree(trial_window)
    outcomes: list[str] = []
    for attempt in range(1, runs + 1):
        # Clear both fields and submit, so the label holds the "required" message and this run
        # cannot read the one the previous run left behind.
        reset = run_steps(RESET_STEPS, TARGETS, read)
        assert [r.status for r in reset] == ["passed"] * 3, (
            f"the reset before run {attempt}/{runs} failed: "
            f"{[(r.status, r.message) for r in reset]}"
        )
        before = _wait_for_status(desktop, trial_window, EMPTY_MESSAGE)
        assert before == EMPTY_MESSAGE, (
            f"could not reset the status label before run {attempt}/{runs}: {before!r}"
        )

        results = run_steps(LOGIN_STEPS, TARGETS, read)
        statuses = [result.status for result in results]
        assert statuses == ["passed"] * 3, (
            f"run {attempt}/{runs} did not pass: "
            f"{[(r.status, r.message) for r in results]}"
        )
        assert all(result.matched == "primary" for result in results), (
            f"run {attempt}/{runs} fell back to the backup properties: "
            f"{[(r.step_index, r.matched) for r in results]}"
        )
        outcomes.append(_wait_for_status(desktop, trial_window, WELCOME))

    assert outcomes == [WELCOME] * runs, (
        f"the application did not confirm every login: {outcomes}"
    )


@pytest.mark.windows
def test_an_empty_value_clears_a_field_on_the_real_app(desktop, trial_window):
    """Step schema v0: Type replaces the text, and an empty value clears it."""
    field = "QApplication.loginWindow.usernameInput"

    def username() -> str | None:
        return _field_value(desktop, trial_window, field)

    typed = {
        "version": "0.1",
        "steps": [
            {"keyword": "Type", "target": "login.userNameInput", "value": "someone"}
        ],
    }
    cleared = {
        "version": "0.1",
        "steps": [{"keyword": "Type", "target": "login.userNameInput", "value": ""}],
    }
    read = lambda: desktop.read_tree(trial_window)

    assert [r.status for r in run_steps(typed, TARGETS, read)] == ["passed"]
    assert username() == "someone", "Type did not put the text in the field"
    assert [r.status for r in run_steps(cleared, TARGETS, read)] == ["passed"]
    assert username() == "", "an empty value must clear the field, not append to it"


@pytest.mark.windows
def test_a_renamed_object_falls_back_to_its_backup_properties(desktop, trial_window):
    """FR-29's precondition: the Find-by set stops matching and the Backup set carries it."""
    targets = {
        "login.loginButton": {
            "properties": {"automationId": "QApplication.loginWindow.signInButton"},
            "fallback": {"name": "Login", "controlType": "Button"},
        }
    }
    document = {
        "version": "0.1",
        "steps": [{"keyword": "Click", "target": "login.loginButton"}],
    }
    results = run_steps(document, targets, lambda: desktop.read_tree(trial_window))
    assert [r.status for r in results] == ["passed"]
    assert results[0].matched == "fallback"


@pytest.mark.windows
def test_an_ambiguous_object_fails_instead_of_clicking_something(desktop, trial_window):
    """`{name: "Username"}` matches the label and the box; neither may be acted on."""
    targets = {"login.userNameInput": {"properties": {"name": "Username"}}}
    document = {
        "version": "0.1",
        "steps": [
            {"keyword": "Click", "target": "login.userNameInput", "timeoutMs": 0}
        ],
    }
    results = run_steps(document, targets, lambda: desktop.read_tree(trial_window))
    assert results[0].status == "failed"
    assert "2 elements match" in results[0].message
