"""#265 on a real Qt table: after SelectRow, the application acts on that row.

The sample app's Open button opens `currentRow()`, the common Qt idiom. `SelectionItem.Select`
alone changes the selection but not the current row, so Open used to show row 1 whatever row
SelectRow had selected. Like `test_playback_trial_app.py`, this needs Windows, UI Automation
and an interpreter that can import PySide6 (the repository's `.venv`); it skips otherwise.

It presses real keys (`rows.make_current`), so keep the desktop to yourself while it runs.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import pytest

from ayna_agent.playback.runner import run_steps
from ayna_agent.recognition.uia import UiaDesktop

REPO = Path(__file__).resolve().parents[2]
SAMPLE_APP = REPO / "eval" / "apps" / "sample" / "sample_app.py"
MAIN_TITLE = "AYNA Örnek 1.0 - Müşteriler"
DETAIL_TITLE = "AYNA Örnek 1.0 - Müşteri detayı"
START_TIMEOUT_S = 60.0


def _target(logical: str, control_type: str) -> dict:
    return {
        "properties": {
            "automationId": f"QApplication.{logical}",
            "controlType": control_type,
        }
    }


MAIN_TARGETS = {
    "main.searchButton": _target("main.searchButton", "Button"),
    "main.openButton": _target("main.openButton", "Button"),
    "main.customerGrid": _target("main.customerGrid", "Table"),
}
DETAIL_TARGETS = {"detail.nameInput": _target("detail.nameInput", "Edit")}


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


def _window(desktop: UiaDesktop, title: str, timeout_s: float) -> int | None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        for window in desktop.list_windows():
            if window["title"] == title:
                return window["handle"]
        time.sleep(0.25)
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
def main_window(desktop):
    if not SAMPLE_APP.exists():
        pytest.skip(f"the sample app is not in this checkout: {SAMPLE_APP}")
    python = _python_with_pyside()
    if python is None:
        pytest.skip(
            "no interpreter here can import PySide6, which the sample app needs"
        )
    app = subprocess.Popen([python, str(SAMPLE_APP), "--screen", "main"])
    try:
        handle = _window(desktop, MAIN_TITLE, START_TIMEOUT_S)
        if handle is None:
            pytest.fail(
                f"no window titled {MAIN_TITLE!r} within {START_TIMEOUT_S:.0f} s"
            )
        yield handle
    finally:
        app.terminate()
        try:
            app.wait(timeout=10)
        except subprocess.TimeoutExpired:
            app.kill()


@pytest.mark.windows
@pytest.mark.parametrize(
    ("row", "opened"),
    [
        ({"value": "Demir", "column": "Soyad"}, "Mehmet Demir"),
        ({"index": 5}, "Elif Şahin"),
    ],
)
def test_open_acts_on_the_row_select_row_chose(desktop, main_window, row, opened):
    steps = {
        "version": "0.2",
        "steps": [
            {"keyword": "Click", "target": "main.searchButton"},
            {"keyword": "Wait", "target": "main.openButton"},
            {"keyword": "SelectRow", "target": "main.customerGrid", "row": row},
            {"keyword": "Click", "target": "main.openButton"},
        ],
    }
    results = run_steps(steps, MAIN_TARGETS, lambda: desktop.read_tree(main_window))
    assert [r.status for r in results] == ["passed"] * 4, [r.message for r in results]
    assert results[2].message is None, results[2].message

    detail = _window(desktop, DETAIL_TITLE, 10.0)
    assert detail is not None, "Open showed no detail window"
    check = {
        "version": "0.2",
        "steps": [
            {
                "keyword": "Verify",
                "target": "detail.nameInput",
                "checkpoint": {
                    "property": "value",
                    "operator": "equals",
                    "expected": opened,
                },
                "timeoutMs": 3000,
            }
        ],
    }
    verified = run_steps(check, DETAIL_TARGETS, lambda: desktop.read_tree(detail))
    assert verified[0].status == "passed", verified[0].message
