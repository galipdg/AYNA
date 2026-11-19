"""`elementFromPoint` over JSON-RPC (#22).

A separate file for the same reason as `test_rpc_run_steps.py`: `rpc.py` and its tests are
galip's (`agent/AGENTS.md`), and this is the one method of it that #22 adds. Fold it into
`test_rpc.py` if you would rather have one file per module.

What is tested here is the server's side only -- the params it accepts and refuses, the shape
it passes through, and which backend error becomes which JSON-RPC code. What the method
*finds* is `test_uia_element_from_point.py`.
"""

from __future__ import annotations

import asyncio
import json
import threading
from concurrent.futures import ThreadPoolExecutor

from ayna_agent.rpc import (
    INVALID_PARAMS,
    UIA_UNAVAILABLE,
    Dispatcher,
    UiaUnavailable,
    UnavailableDesktop,
)

ANSWER = {
    "handle": 657704,
    "bounds": [560, 210, 1010, 415],
    "snapshotId": "5e8f0a1b-3c2d-4e6f-8a9b-1c0d2e3f4a5b",
    "elementId": "e8",
    "element": {"automationId": "QApplication.loginWindow.usernameInput"},
}


class PointingDesktop:
    """A desktop that records the `element_from_point` call and answers with `ANSWER`."""

    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[tuple[int, int]] = []
        self.threads: list[str] = []

    def list_windows(self):
        return []

    def snapshot(self, handle, timeout_ms):
        raise AssertionError("elementFromPoint must not take the snapshot path")

    def run_steps(self, handle, steps, targets, default_timeout_ms=None, run_id=None):
        raise AssertionError("elementFromPoint must not take the playback path")

    def element_from_point(self, x, y):
        self.threads.append(threading.current_thread().name)
        self.calls.append((x, y))
        if self.error is not None:
            raise self.error
        return ANSWER


def call(desktop, params, *, method="elementFromPoint"):
    """One request through a Dispatcher; returns the decoded reply."""
    message = {"jsonrpc": "2.0", "id": 1, "method": method}
    if params is not None:
        message["params"] = params

    async def run():
        with ThreadPoolExecutor(max_workers=1, thread_name_prefix="ayna-uia") as pool:
            return await Dispatcher(desktop, pool).handle(json.dumps(message))

    return json.loads(asyncio.run(run()))


# --- the happy path ------------------------------------------------------------------------


def test_the_answer_is_passed_through_unchanged():
    desktop = PointingDesktop()
    reply = call(desktop, {"x": 785, "y": 312})
    assert reply["result"] == ANSWER
    assert desktop.calls == [(785, 312)]


def test_the_hit_test_runs_on_the_single_uia_thread():
    """A hit test is a UI Automation call, so it belongs in the same apartment (PR #135)."""
    desktop = PointingDesktop()
    call(desktop, {"x": 1, "y": 2})
    assert desktop.threads and all(
        name.startswith("ayna-uia") for name in desktop.threads
    )


def test_a_negative_point_is_valid():
    """Virtual-desktop coordinates are signed: a maximised window at 150 % reports a negative
    origin (`learnings.md` 2026-11-07), so a point inside it can be negative too."""
    desktop = PointingDesktop()
    reply = call(desktop, {"x": -11, "y": -11})
    assert "result" in reply
    assert desktop.calls == [(-11, -11)]


def test_the_origin_is_valid():
    desktop = PointingDesktop()
    assert "result" in call(desktop, {"x": 0, "y": 0})
    assert desktop.calls == [(0, 0)]


# --- params the server refuses -------------------------------------------------------------


def test_a_missing_coordinate_is_invalid_params():
    reply = call(PointingDesktop(), {"x": 10})
    assert reply["error"]["code"] == INVALID_PARAMS
    assert "y" in reply["error"]["message"] or "x" in reply["error"]["message"]


def test_no_params_at_all_is_invalid_params():
    assert call(PointingDesktop(), None)["error"]["code"] == INVALID_PARAMS


def test_an_unknown_param_is_refused_rather_than_ignored():
    """A typo must not be silently dropped; a new optional param is a minor version bump."""
    reply = call(PointingDesktop(), {"x": 1, "y": 2, "handle": 3})
    assert reply["error"]["code"] == INVALID_PARAMS
    assert "handle" in reply["error"]["message"]


def test_a_coordinate_that_is_not_an_int_is_invalid_params():
    for value in ("10", 10.5, None, [10], {"v": 10}):
        reply = call(PointingDesktop(), {"x": value, "y": 0})
        assert reply["error"]["code"] == INVALID_PARAMS, value


def test_a_boolean_is_not_a_coordinate():
    """`True` is an `int` in Python. A client sending one has a bug, not a point."""
    reply = call(PointingDesktop(), {"x": True, "y": 0})
    assert reply["error"]["code"] == INVALID_PARAMS


def test_params_as_an_array_is_invalid_params():
    assert call(PointingDesktop(), [785, 312])["error"]["code"] == INVALID_PARAMS


# --- errors from the backend ---------------------------------------------------------------


def test_a_host_without_ui_automation_answers_minus_32001():
    reply = call(UnavailableDesktop("UI Automation needs Windows"), {"x": 1, "y": 2})
    assert reply["error"]["code"] == UIA_UNAVAILABLE
    assert "Windows" in reply["error"]["message"]


def test_the_backend_reason_reaches_the_client():
    desktop = PointingDesktop(UiaUnavailable("COM did not start"))
    reply = call(desktop, {"x": 1, "y": 2})
    assert reply["error"]["code"] == UIA_UNAVAILABLE
    assert "COM did not start" in reply["error"]["message"]
