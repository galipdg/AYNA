"""#264 on a real Qt button: two Clicks on the same button both take effect.

Qt performs UIA `Invoke` on a button with `animateClick()`, which releases the button 100 ms
later and only restarts that timer when called again before then, so a second `Invoke` inside
the window is lost while still returning without error. The sample app's wizard shows it
plainly: two Clicks on Next must turn two pages.

Like `test_playback_trial_app.py`, this needs Windows, UI Automation and an interpreter that can
import PySide6 (the repository's `.venv`); it skips with the reason when any is missing.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import pytest

from ayna_agent.playback.actions import InvokeSpacing
from ayna_agent.playback.runner import run_steps
from ayna_agent.recognition.uia import UiaDesktop

REPO = Path(__file__).resolve().parents[2]
SAMPLE_APP = REPO / "eval" / "apps" / "sample" / "sample_app.py"
WINDOW_TITLE = "AYNA Örnek 1.0 - Yeni kayıt sihirbazı"
START_TIMEOUT_S = 60.0


def _target(logical: str, control_type: str) -> dict:
    return {
        "properties": {"automationId": f"QApplication.{logical}"},
        "fallback": {"controlType": control_type},
    }


TARGETS = {
    "wizard.nameInput": _target("wizard.nameInput", "Edit"),
    "wizard.nextButton": _target("wizard.nextButton", "Button"),
    "wizard.stepLabel": _target("wizard.stepLabel", "Text"),
}

#: Two Clicks on Next with nothing in between, then the page the wizard is on. The Verify waits
#: up to its timeout, so a page that turns late still passes and a lost click fails.
TWO_PAGES = {
    "version": "0.2",
    "steps": [
        {"keyword": "Type", "target": "wizard.nameInput", "value": "Ayşe Çelik"},
        {"keyword": "Click", "target": "wizard.nextButton"},
        {"keyword": "Click", "target": "wizard.nextButton"},
        {
            "keyword": "Verify",
            "target": "wizard.stepLabel",
            "checkpoint": {
                "property": "name",
                "operator": "equals",
                "expected": "Adım 3 / 3",
            },
            "timeoutMs": 2000,
        },
    ],
}


class NoSpacing(InvokeSpacing):
    """The runner as it was before #264: never waits."""

    def wait(self, name, now, sleep) -> float:
        return 0.0


def _python_with_pyside() -> str | None:
    for python in (sys.executable, str(REPO / ".venv" / "Scripts" / "python.exe")):
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


@pytest.fixture
def wizard(desktop):
    """A fresh wizard on page 1 for each test, closed afterwards."""
    if not SAMPLE_APP.exists():
        pytest.skip(f"the sample app is not in this checkout: {SAMPLE_APP}")
    python = _python_with_pyside()
    if python is None:
        pytest.skip(
            "no interpreter here can import PySide6, which the sample app needs"
        )
    app = subprocess.Popen([python, str(SAMPLE_APP), "--screen", "wizard"])
    try:
        deadline = time.monotonic() + START_TIMEOUT_S
        handle = None
        while handle is None and time.monotonic() < deadline:
            if app.poll() is not None:
                pytest.skip(f"the sample app exited at once with code {app.returncode}")
            handle = next(
                (
                    w["handle"]
                    for w in desktop.list_windows()
                    if w["title"] == WINDOW_TITLE
                ),
                None,
            )
            if handle is None:
                time.sleep(0.25)
        if handle is None:
            pytest.fail(
                f"no window titled {WINDOW_TITLE!r} within {START_TIMEOUT_S:.0f} s"
            )
        yield lambda: desktop.read_tree(handle)
    finally:
        app.terminate()
        try:
            app.wait(timeout=10)
        except subprocess.TimeoutExpired:
            app.kill()


@pytest.mark.windows
def test_two_clicks_on_next_turn_two_pages(wizard):
    results = run_steps(TWO_PAGES, TARGETS, wizard, spacing=InvokeSpacing())
    assert [r.status for r in results] == ["passed"] * 4, [r.message for r in results]


@pytest.mark.windows
def test_without_the_gap_the_second_click_is_lost(wizard):
    """The control: shows the test above can fail, i.e. the bug is real on this machine."""
    results = run_steps(TWO_PAGES, TARGETS, wizard, spacing=NoSpacing())
    if results[3].status == "passed":
        pytest.skip("the two clicks were more than 100 ms apart here; nothing to show")
    assert [r.status for r in results[:3]] == ["passed"] * 3, (
        "both Clicks report passed"
    )
    assert "Adım 2 / 3" in (results[3].message or "")
