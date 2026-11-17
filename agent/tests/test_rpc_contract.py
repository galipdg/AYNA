"""The agent's replies against `schemas/agent-rpc.schema.json` (ADR contracts-v1-freeze, #52).

The client checks its requests against the same file
(`client/src/main/__tests__/agentContract.test.ts`); this is the agent's half. Every reply
goes through the real `Dispatcher`, so the envelope, `ping` and every error path are the
agent's own code. Method results come from fake backends shaped like the real ones, which
keeps the fakes the other tests use honest too.
"""

from __future__ import annotations

import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from ayna_agent.playback.runner import StepResult
from ayna_agent.rpc import (
    INTERNAL_ERROR,
    INVALID_PARAMS,
    INVALID_REQUEST,
    METHOD_NOT_FOUND,
    PARSE_ERROR,
    RPC_VERSION,
    SNAPSHOT_TIMEOUT,
    UIA_UNAVAILABLE,
    WINDOW_NOT_FOUND,
    Dispatcher,
    SnapshotTimeout,
    UnavailableDesktop,
    WindowNotFound,
)

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "schemas" / "agent-rpc.schema.json").read_text("utf-8"))
SNAPSHOT = json.loads(
    (ROOT / "schemas" / "examples" / "snapshot" / "trial-login.json").read_text("utf-8")
)

WINDOWS = [
    {
        "handle": 1001,
        "title": "Giriş",
        "className": "LoginWindow",
        "processId": 4242,
        "processName": "python.exe",
        "bounds": [100, 100, 500, 400],
    },
    # What `uia.py` sends when Windows will not say: an elevated process, a title it
    # cannot read. The schema allows null for each, and the client reads it (#52).
    # `bounds` is never null: `_frame_bounds` falls back to `GetWindowRect`.
    {
        "handle": 1002,
        "title": None,
        "className": None,
        "processId": None,
        "processName": None,
        "bounds": [0, 0, 800, 600],
    },
]
HIT = {
    "handle": SNAPSHOT["window"]["handle"],
    "bounds": SNAPSHOT["elements"][1]["element"]["bounds"],
    "snapshotId": SNAPSHOT["snapshotId"],
    "elementId": SNAPSHOT["elements"][1]["id"],
    "element": SNAPSHOT["elements"][1]["element"],
}
NO_WINDOW = dict.fromkeys(("handle", "bounds", "snapshotId", "elementId", "element"))
RESULTS = [
    {
        "stepIndex": 0,
        "status": "passed",
        "durationMs": 7,
        "performedWith": "SetValue",
        # #54: a step that ran carries its screenshot. The fake used to leave these out,
        # which is exactly why the 1.1 schema's `additionalProperties: false` could forbid
        # them while every real answer sent them (caught in #248's review).
        "screenshotPath": r"C:\Users\t\AppData\Local\Temp\ayna-screenshots\run-1\step-0000.png",
        "screenshotAt": "2026-11-15T14:03:11.250+03:00",
    },
    {
        "stepIndex": 1,
        "status": "failed",
        "durationMs": 10_000,
        "stepId": "c0ffee00-0000-4000-8000-000000000001",
        "message": "login.loginButton was not found within 10000 ms",
        "screenshotPath": "/tmp/ayna-screenshots/run-1/step-0001.png",
        "screenshotAt": "2026-11-15T14:03:21.402+03:00",
    },
    # A notRun step is never photographed, so it carries neither field (#54).
    {"stepIndex": 2, "status": "notRun", "durationMs": 0},
]
STEPS = {
    "version": "0.2",
    "steps": [{"keyword": "Click", "target": "login.loginButton"}],
}
TARGETS = {"login.loginButton": {"properties": {"automationId": "loginButton"}}}


def validator(definition: str) -> Draft202012Validator:
    """A validator for one `$defs` entry, with the file's other definitions in reach."""
    return Draft202012Validator(
        {"$ref": f"#/$defs/{definition}", "$defs": SCHEMA["$defs"]}
    )


def check(definition: str, instance: object) -> None:
    errors = sorted(validator(definition).iter_errors(instance), key=str)
    assert not errors, "\n".join(e.message for e in errors)


class ContractDesktop:
    """Answers every method the way the real backend shapes its answers."""

    def list_windows(self):
        return WINDOWS

    def snapshot(self, handle, timeout_ms):
        if handle != SNAPSHOT["window"]["handle"]:
            raise WindowNotFound(handle)
        if timeout_ms == 1:
            raise SnapshotTimeout("window still not read after 1 ms")
        return SNAPSHOT

    def element_from_point(self, x, y):
        return HIT if (x, y) == (10, 10) else NO_WINDOW

    def run_steps(self, handle, steps, targets, default_timeout_ms=None):
        return RESULTS


class BrokenDesktop(ContractDesktop):
    def list_windows(self):
        raise RuntimeError("COM blew up")


def reply(desktop, message):
    """One message through the real Dispatcher; the decoded reply."""
    text = message if isinstance(message, str) else json.dumps(message)

    async def run():
        with ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="ayna-uia"
        ) as executor:
            return await Dispatcher(desktop, executor).handle(text)

    return json.loads(asyncio.run(run()))


def request(method, params=None):
    message = {"jsonrpc": "2.0", "id": 7, "method": method}
    if params is not None:
        message["params"] = params
    return message


# --- versions --------------------------------------------------------------------------


def test_rpc_version_is_within_the_schemas_version():
    """`ping` never claims more than the schema describes, nor another major version.

    The schema may be a minor version ahead while what it adds is not built yet: 1.1's
    `category` (#240) lands before playback fills it (#63), and only then does the agent
    answer 1.1."""
    agent_major, agent_minor = map(int, RPC_VERSION.split("."))
    schema_major, schema_minor = map(
        int, SCHEMA["$defs"]["version"]["const"].split(".")
    )
    assert agent_major == schema_major
    assert agent_minor <= schema_minor


# --- results ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("method", "params", "definition"),
    [
        ("ping", None, "pingResult"),
        ("listWindows", None, "listWindowsResult"),
        ("snapshot", {"handle": SNAPSHOT["window"]["handle"]}, "snapshotResult"),
        ("elementFromPoint", {"x": 10, "y": 10}, "elementFromPointResult"),
        ("elementFromPoint", {"x": -1920, "y": 5}, "elementFromPointResult"),
        (
            "runSteps",
            {"handle": 1001, "steps": STEPS, "targets": TARGETS},
            "runStepsResult",
        ),
    ],
    ids=["ping", "listWindows", "snapshot", "hit", "no-window", "runSteps"],
)
def test_every_result_is_in_the_contract(method, params, definition):
    answer = reply(ContractDesktop(), request(method, params))
    check("success", answer)
    check(definition, answer["result"])


# --- errors -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("desktop", "message", "code"),
    [
        (ContractDesktop(), "{not json", PARSE_ERROR),
        (ContractDesktop(), {"jsonrpc": "2.0", "id": 7}, INVALID_REQUEST),
        (ContractDesktop(), request("noSuchMethod"), METHOD_NOT_FOUND),
        (ContractDesktop(), request("snapshot", {"handle": "1001"}), INVALID_PARAMS),
        (BrokenDesktop(), request("listWindows"), INTERNAL_ERROR),
        (ContractDesktop(), request("snapshot", {"handle": 999}), WINDOW_NOT_FOUND),
        (UnavailableDesktop("not Windows"), request("listWindows"), UIA_UNAVAILABLE),
        (
            ContractDesktop(),
            request(
                "snapshot", {"handle": SNAPSHOT["window"]["handle"], "timeoutMs": 1}
            ),
            SNAPSHOT_TIMEOUT,
        ),
    ],
    ids=[
        "parse",
        "invalid-request",
        "method",
        "params",
        "internal",
        "window",
        "uia",
        "timeout",
    ],
)
def test_every_error_is_in_the_contract(desktop, message, code):
    answer = reply(desktop, message)
    check("failure", answer)
    assert answer["error"]["code"] == code


# --- the real StepResult, not a fake of it ------------------------------------------------


@pytest.mark.parametrize(
    "result",
    [
        StepResult(step_index=0, status="passed", duration_ms=7),
        StepResult(
            step_index=1,
            status="passed",
            duration_ms=31,
            step_id="c0ffee00-0000-4000-8000-000000000001",
            matched="fallback",
            performed_with="Invoke",
            screenshot_path=r"C:\Temp\ayna-screenshots\run-1\step-0001.png",
            screenshot_at="2026-11-15T14:03:11.250+03:00",
        ),
        StepResult(
            step_index=2,
            status="failed",
            duration_ms=10_000,
            message="login.loginButton was not found within 10000 ms",
            matched="primary",
            screenshot_path="/tmp/ayna-screenshots/run-1/step-0002.png",
            screenshot_at="2026-11-15T14:03:21.402+03:00",
        ),
        StepResult(
            step_index=3,
            status="notRun",
            duration_ms=0,
            message="not run: an earlier step failed",
        ),
    ],
    ids=["bare", "passed-with-screenshot", "failed-with-screenshot", "notRun"],
)
def test_what_the_runner_really_writes_is_in_the_contract(result):
    """The fake above shapes its answers by hand; this one asks `StepResult` itself.

    The gap this closes is a real one. The 1.1 schema set `additionalProperties: false` on
    `stepResult` while #54 was adding `screenshotPath` and `screenshotAt`, so **every** real
    `runSteps` answer was outside the contract — and nothing failed, because the only
    step results any test validated were hand-written dicts that happened not to carry the
    new fields (found by omer reviewing #248, not by CI). A field added to `StepResult`
    without the schema now fails here instead.
    """
    check("stepResult", result.to_json())
