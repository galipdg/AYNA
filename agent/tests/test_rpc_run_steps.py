"""`runSteps` over JSON-RPC (#26).

A separate file from `test_rpc.py` on purpose: `rpc.py` and its tests are galip's
(`agent/AGENTS.md`), and this is the one method of it that #26 adds. Fold it into `test_rpc.py`
if you would rather have one file per module -- nothing here depends on living apart.

What is tested is the server's side only: the params it accepts and refuses, the shape it
answers, and which backend error becomes which JSON-RPC code. What the steps *do* is
`test_playback_runner.py` (with fakes) and `test_playback_trial_app.py` (on the real app).
"""

from __future__ import annotations

import asyncio
import json
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from ayna_agent.rpc import (
    INVALID_PARAMS,
    RPC_VERSION,
    BadStepDocument,
    Dispatcher,
    SnapshotTimeout,
    UiaUnavailable,
    UnavailableDesktop,
    WindowNotFound,
)

HANDLE = 657704

STEPS = {
    "version": "0.1",
    "steps": [
        {"keyword": "Type", "target": "login.userNameInput", "value": "admin"},
        {"keyword": "Click", "target": "login.loginButton"},
    ],
}
TARGETS = {
    "login.userNameInput": {
        "properties": {"automationId": "QApplication.loginWindow.usernameInput"}
    },
    "login.loginButton": {
        "properties": {"automationId": "QApplication.loginWindow.loginButton"},
        "fallback": {"name": "Login", "controlType": "Button"},
    },
}

RESULTS = [
    {"stepIndex": 0, "status": "passed", "durationMs": 7, "performedWith": "SetValue"},
    {"stepIndex": 1, "status": "passed", "durationMs": 12, "performedWith": "Invoke"},
]


class PlayingDesktop:
    """A desktop that records the `run_steps` call and answers with `RESULTS`."""

    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[tuple] = []
        self.threads: list[str] = []

    def list_windows(self):
        return []

    def snapshot(self, handle, timeout_ms):
        raise AssertionError("runSteps must not take the snapshot path")

    def run_steps(self, handle, steps, targets, default_timeout_ms=None, run_id=None):
        self.threads.append(threading.current_thread().name)
        self.calls.append((handle, steps, targets, default_timeout_ms, run_id))
        if self.error is not None:
            raise self.error
        return RESULTS


def call(desktop, params, *, method="runSteps"):
    """One request through a Dispatcher; returns the decoded reply."""
    message = {"jsonrpc": "2.0", "id": 1, "method": method}
    if params is not None:
        message["params"] = params

    async def run():
        with ThreadPoolExecutor(max_workers=1, thread_name_prefix="ayna-uia") as pool:
            return await Dispatcher(desktop, pool).handle(json.dumps(message))

    return json.loads(asyncio.run(run()))


def params(**overrides):
    base = {"handle": HANDLE, "steps": STEPS, "targets": TARGETS}
    base.update(overrides)
    return base


# --- the happy path ------------------------------------------------------------------------


def test_the_results_come_back_under_results():
    desktop = PlayingDesktop()
    reply = call(desktop, params())
    assert reply["result"] == {"results": RESULTS}
    assert desktop.calls == [(HANDLE, STEPS, TARGETS, None, None)]


def test_the_steps_run_on_the_single_uia_thread():
    """Every UI Automation call shares one apartment; playback is no exception (PR #135)."""
    desktop = PlayingDesktop()
    call(desktop, params())
    assert desktop.threads and all(
        name.startswith("ayna-uia") for name in desktop.threads
    )


def test_the_run_id_reaches_the_backend():
    """#54 names the run's screenshot directory after it; #44 sends one step per call, and
    without the id each call would open a folder of its own."""
    desktop = PlayingDesktop()
    reply = call(
        desktop,
        params(
            runId="3f6c2a9e-8b1d-4e7a-9c55-0d2f4b7a1e90",
            appVersionId="9a1d7c3e-2f4b-4c8a-b6e5-7d0f1a2b3c4d",
        ),
    )
    assert "result" in reply
    assert desktop.calls[0][0] == HANDLE
    assert desktop.calls[0][4] == "3f6c2a9e-8b1d-4e7a-9c55-0d2f4b7a1e90"


def test_without_a_run_id_the_backend_gets_none():
    desktop = PlayingDesktop()
    call(desktop, params())
    assert desktop.calls[0][4] is None


@pytest.mark.parametrize("run_id", [42, ["a"], {"id": "a"}, True])
def test_a_run_id_that_is_not_a_string_is_refused(run_id):
    desktop = PlayingDesktop()
    reply = call(desktop, params(runId=run_id))
    assert reply["error"]["code"] == INVALID_PARAMS
    assert "runId" in reply["error"]["message"]
    assert desktop.calls == []


def test_a_default_timeout_is_passed_through():
    desktop = PlayingDesktop()
    call(desktop, params(defaultTimeoutMs=2_000))
    assert desktop.calls[0][3] == 2_000


def test_ping_answers_the_contract_version_it_fills():
    """1.0 is v0.1 plus `runSteps` and `elementFromPoint` (ADR contracts-v1-freeze); 1.1 a
    failed step's `category`, filled by #63; 1.2 the step screenshot, filled by #54."""
    reply = call(PlayingDesktop(), None, method="ping")
    assert reply["result"]["rpcVersion"] == RPC_VERSION == "1.2"


# --- params the server refuses -------------------------------------------------------------


@pytest.mark.parametrize(
    "bad",
    [
        None,
        [],
        {},
        {"handle": HANDLE},
        {"handle": HANDLE, "steps": STEPS},
        {"steps": STEPS, "targets": TARGETS},
    ],
    ids=[
        "no params",
        "an array",
        "empty",
        "no steps or targets",
        "no targets",
        "no handle",
    ],
)
def test_the_three_required_params_are_required(bad):
    reply = call(PlayingDesktop(), bad)
    assert reply["error"]["code"] == INVALID_PARAMS


def test_an_unknown_param_is_refused_so_a_typo_is_not_dropped():
    reply = call(PlayingDesktop(), params(timeoutMs=1_000))
    assert reply["error"]["code"] == INVALID_PARAMS
    assert "timeoutMs" in reply["error"]["message"]


@pytest.mark.parametrize("handle", [0, -1, "657704", 1.5, True, None])
def test_the_handle_must_be_a_positive_int(handle):
    reply = call(PlayingDesktop(), params(handle=handle))
    assert reply["error"]["code"] == INVALID_PARAMS
    assert "handle" in reply["error"]["message"]


@pytest.mark.parametrize("steps", [[], "0.1", 3, None])
def test_the_steps_must_be_a_document_object(steps):
    reply = call(PlayingDesktop(), params(steps=steps))
    assert reply["error"]["code"] == INVALID_PARAMS
    assert "steps" in reply["error"]["message"]


@pytest.mark.parametrize(
    "targets", [[], "none", {"login.loginButton": "automationId=x"}, {"a": None}]
)
def test_the_targets_must_map_a_name_to_its_property_sets(targets):
    reply = call(PlayingDesktop(), params(targets=targets))
    assert reply["error"]["code"] == INVALID_PARAMS
    assert "targets" in reply["error"]["message"]


def test_no_targets_at_all_is_allowed_and_fails_per_step():
    """An empty map is a legal request; every step then fails by name, which is #26's message."""
    desktop = PlayingDesktop()
    reply = call(desktop, params(targets={}))
    assert "result" in reply
    assert desktop.calls[0][2] == {}


@pytest.mark.parametrize("timeout", [0, -1, "1000", 600_001, True])
def test_a_default_timeout_outside_the_contract_is_refused(timeout):
    reply = call(PlayingDesktop(), params(defaultTimeoutMs=timeout))
    assert reply["error"]["code"] == INVALID_PARAMS
    assert "defaultTimeoutMs" in reply["error"]["message"]


# --- backend errors become the documented codes --------------------------------------------


@pytest.mark.parametrize(
    ("error", "code", "text"),
    [
        (WindowNotFound(12), -32000, "Window not found"),
        (UiaUnavailable("not Windows"), -32001, "UI Automation unavailable"),
        (SnapshotTimeout("walk stopped"), -32002, "Snapshot timeout"),
        (BadStepDocument("version '0.9'"), INVALID_PARAMS, "Invalid params"),
    ],
    ids=["window gone", "no backend", "window too slow", "unreadable document"],
)
def test_a_backend_error_becomes_its_documented_code(error, code, text):
    reply = call(PlayingDesktop(error=error), params())
    assert reply["error"]["code"] == code
    assert text in reply["error"]["message"]


def test_a_host_without_a_backend_answers_uia_unavailable():
    """`UnavailableDesktop` has to answer every method, `runSteps` included (#12)."""
    reply = call(UnavailableDesktop("UI Automation needs Windows"), params())
    assert reply["error"]["code"] == -32001
    assert "needs Windows" in reply["error"]["message"]
