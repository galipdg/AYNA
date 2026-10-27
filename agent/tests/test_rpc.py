"""Tests for the agent JSON-RPC server (#16). A fake desktop stands in for UI Automation,
so everything runs on any OS; the client side uses the websockets client."""

import asyncio
import json
import os
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from websockets.asyncio.client import connect
from websockets.exceptions import InvalidStatus

from ayna_agent import __version__
from ayna_agent.rpc import (
    HOST,
    INTERNAL_ERROR,
    INVALID_PARAMS,
    INVALID_REQUEST,
    METHOD_NOT_FOUND,
    PARSE_ERROR,
    RPC_VERSION,
    TOKEN_ENV,
    UIA_UNAVAILABLE,
    WINDOW_NOT_FOUND,
    Dispatcher,
    UnavailableDesktop,
    WindowNotFound,
    bound_port,
    main,
    serve_rpc,
)

TOKEN = "test-token-0123456789abcdef"
WINDOW = {
    "handle": 1001,
    "title": "Giriş",
    "className": "LoginWindow",
    "processId": 4242,
    "processName": "python.exe",
    "bounds": [100, 100, 500, 400],
}


class FakeDesktop:
    def __init__(self):
        self.threads = []

    def list_windows(self):
        self.threads.append(threading.current_thread().name)
        return [WINDOW]

    def snapshot(self, handle):
        self.threads.append(threading.current_thread().name)
        if handle != WINDOW["handle"]:
            raise WindowNotFound(handle)
        return {"snapshotId": "fake", "window": WINDOW, "elements": []}


class BrokenDesktop(FakeDesktop):
    def list_windows(self):
        raise RuntimeError("COM blew up")


def worker():
    return ThreadPoolExecutor(max_workers=1, thread_name_prefix="ayna-uia")


def call(desktop, request):
    """Run one request through a Dispatcher; returns the decoded reply or None."""
    text = request if isinstance(request, str) else json.dumps(request)

    async def run():
        with worker() as executor:
            return await Dispatcher(desktop, executor).handle(text)

    reply = asyncio.run(run())
    return None if reply is None else json.loads(reply)


def request(method, params=None, id=1):
    message = {"jsonrpc": "2.0", "method": method, "id": id}
    if params is not None:
        message["params"] = params
    return message


# --- methods -------------------------------------------------------------------------


def test_ping_reports_versions():
    assert call(FakeDesktop(), request("ping")) == {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {"agentVersion": __version__, "rpcVersion": RPC_VERSION},
    }


def test_list_windows_returns_backend_windows():
    reply = call(FakeDesktop(), request("listWindows", id="w-1"))
    assert reply == {"jsonrpc": "2.0", "id": "w-1", "result": {"windows": [WINDOW]}}


def test_snapshot_returns_backend_snapshot():
    reply = call(FakeDesktop(), request("snapshot", {"handle": 1001}))
    assert reply["result"]["window"] == WINDOW


def test_snapshot_of_unknown_window():
    reply = call(FakeDesktop(), request("snapshot", {"handle": 999}))
    assert reply["error"]["code"] == WINDOW_NOT_FOUND
    assert reply["id"] == 1


@pytest.mark.parametrize("method", ["listWindows", "snapshot"])
def test_without_uia_backend(method):
    params = {"handle": 1001} if method == "snapshot" else None
    reply = call(UnavailableDesktop("not Windows"), request(method, params))
    assert reply["error"]["code"] == UIA_UNAVAILABLE
    assert "not Windows" in reply["error"]["message"]


def test_backend_crash_is_an_internal_error():
    reply = call(BrokenDesktop(), request("listWindows"))
    assert reply["error"]["code"] == INTERNAL_ERROR
    assert "COM blew up" in reply["error"]["message"]


def test_backend_calls_share_one_worker_thread():
    desktop = FakeDesktop()

    async def run():
        with worker() as executor:
            dispatcher = Dispatcher(desktop, executor)
            await asyncio.gather(
                *(
                    dispatcher.handle(json.dumps(request("listWindows")))
                    for _ in range(5)
                )
            )

    asyncio.run(run())
    assert len(set(desktop.threads)) == 1
    assert desktop.threads[0].startswith("ayna-uia")


def test_empty_params_are_accepted():
    assert "result" in call(FakeDesktop(), request("ping", {}))
    assert "result" in call(FakeDesktop(), request("listWindows", []))


# --- protocol errors -----------------------------------------------------------------

INVALID = {
    "not json": ("{", PARSE_ERROR, None),
    "batch": ([request("ping")], INVALID_REQUEST, None),
    "scalar": (42, INVALID_REQUEST, None),
    "no jsonrpc": ({"method": "ping", "id": 7}, INVALID_REQUEST, 7),
    "jsonrpc 1.0": ({"jsonrpc": "1.0", "method": "ping", "id": 7}, INVALID_REQUEST, 7),
    "no method": ({"jsonrpc": "2.0", "id": 7}, INVALID_REQUEST, 7),
    "method not a string": (
        {"jsonrpc": "2.0", "method": 1, "id": 7},
        INVALID_REQUEST,
        7,
    ),
    "params a string": (request("ping", "x", id=7), INVALID_REQUEST, 7),
    "params null": ({**request("ping", id=7), "params": None}, INVALID_REQUEST, 7),
    "id boolean": (request("ping", id=True), INVALID_REQUEST, None),
    "id float": (request("ping", id=1.5), INVALID_REQUEST, None),
    "id object": (request("ping", id={"a": 1}), INVALID_REQUEST, None),
    "unknown method": (request("deleteEverything", id=7), METHOD_NOT_FOUND, 7),
    "ping with params": (request("ping", {"x": 1}, id=7), INVALID_PARAMS, 7),
    "listWindows with params": (request("listWindows", [1], id=7), INVALID_PARAMS, 7),
    "snapshot no params": (request("snapshot", id=7), INVALID_PARAMS, 7),
    "snapshot positional": (request("snapshot", [1001], id=7), INVALID_PARAMS, 7),
    "snapshot extra key": (
        request("snapshot", {"handle": 1001, "deep": True}, id=7),
        INVALID_PARAMS,
        7,
    ),
    "handle string": (request("snapshot", {"handle": "1001"}, id=7), INVALID_PARAMS, 7),
    "handle boolean": (request("snapshot", {"handle": True}, id=7), INVALID_PARAMS, 7),
    "handle zero": (request("snapshot", {"handle": 0}, id=7), INVALID_PARAMS, 7),
    "handle negative": (request("snapshot", {"handle": -5}, id=7), INVALID_PARAMS, 7),
}


@pytest.mark.parametrize("case", INVALID, ids=list(INVALID))
def test_invalid_requests_are_answered_with_an_error(case):
    message, code, request_id = INVALID[case]
    reply = call(FakeDesktop(), message)
    assert reply["jsonrpc"] == "2.0"
    assert reply["error"]["code"] == code
    assert reply["id"] == request_id
    assert "result" not in reply


def test_deeply_nested_json_gets_an_error_reply():
    # Python 3.11 raises RecursionError here (parse error); newer versions parse it.
    reply = call(FakeDesktop(), "[" * 100_000 + "]" * 100_000)
    assert reply["error"]["code"] in (PARSE_ERROR, INVALID_REQUEST)


def test_notifications_get_no_reply():
    desktop = FakeDesktop()
    assert call(desktop, {"jsonrpc": "2.0", "method": "listWindows"}) is None
    assert desktop.threads, "the notification still ran"
    assert call(desktop, {"jsonrpc": "2.0", "method": "nope"}) is None


def test_invalid_request_without_id_is_still_answered():
    reply = call(FakeDesktop(), {"jsonrpc": "2.0", "method": 1})
    assert reply["error"]["code"] == INVALID_REQUEST
    assert reply["id"] is None


# --- over a real WebSocket on 127.0.0.1 ----------------------------------------------


def run_with_server(desktop, client):
    """Start the server on a free port, run `client(uri)`, stop the server."""

    async def run():
        async with serve_rpc(desktop, TOKEN) as server:
            return await client(f"ws://{HOST}:{bound_port(server)}", server)

    return asyncio.run(run())


def auth(token=TOKEN):
    return {"Authorization": f"Bearer {token}"}


async def roundtrip(websocket, message):
    await websocket.send(json.dumps(message))
    return json.loads(await websocket.recv())


def test_binds_to_loopback_only():
    async def client(uri, server):
        return [sock.getsockname()[0] for sock in server.sockets]

    assert run_with_server(FakeDesktop(), client) == ["127.0.0.1"]


def test_methods_work_from_a_websocket_client():
    async def client(uri, server):
        async with connect(uri, additional_headers=auth()) as websocket:
            return [
                await roundtrip(websocket, request("ping", id=1)),
                await roundtrip(websocket, request("listWindows", id=2)),
                await roundtrip(websocket, request("snapshot", {"handle": 1001}, id=3)),
                await roundtrip(websocket, request("snapshot", {"handle": 5}, id=4)),
            ]

    ping, windows, snapshot, missing = run_with_server(FakeDesktop(), client)
    assert ping["result"]["rpcVersion"] == RPC_VERSION
    assert windows["result"]["windows"] == [WINDOW]
    assert snapshot["id"] == 3 and snapshot["result"]["window"]["handle"] == 1001
    assert missing["error"]["code"] == WINDOW_NOT_FOUND


@pytest.mark.parametrize(
    "headers",
    [
        {},
        auth("wrong-token-0123456789abcdef"),
        auth(TOKEN + "x"),
        {"Authorization": TOKEN},
        {"Authorization": f"bearer {TOKEN}"},
        {"Authorization": f"Basic {TOKEN}"},
        [("Authorization", f"Bearer {TOKEN}"), ("Authorization", f"Bearer {TOKEN}")],
    ],
    ids=["none", "wrong", "longer", "no scheme", "lowercase", "basic", "twice"],
)
def test_handshake_without_the_token_is_refused(headers):
    async def client(uri, server):
        with pytest.raises(InvalidStatus) as refused:
            async with connect(uri, additional_headers=headers):
                pass
        return refused.value.response.status_code

    assert run_with_server(FakeDesktop(), client) == 401


def test_token_in_the_query_string_is_refused():
    async def client(uri, server):
        with pytest.raises(InvalidStatus) as refused:
            async with connect(f"{uri}/?token={TOKEN}"):
                pass
        return refused.value.response.status_code

    assert run_with_server(FakeDesktop(), client) == 401


def test_binary_frames_are_refused():
    async def client(uri, server):
        async with connect(uri, additional_headers=auth()) as websocket:
            await websocket.send(json.dumps(request("ping")).encode())
            return json.loads(await websocket.recv())

    assert run_with_server(FakeDesktop(), client)["error"]["code"] == INVALID_REQUEST


def test_short_token_is_rejected():
    async def run():
        async with serve_rpc(FakeDesktop(), "short"):
            pass

    with pytest.raises(ValueError):
        asyncio.run(run())


# --- command line --------------------------------------------------------------------


def test_main_needs_a_token(monkeypatch):
    monkeypatch.delenv(TOKEN_ENV, raising=False)
    with pytest.raises(SystemExit) as stopped:
        main([])
    assert stopped.value.code == 2


def test_main_rejects_a_bad_port(monkeypatch):
    monkeypatch.setenv(TOKEN_ENV, TOKEN)
    with pytest.raises(SystemExit) as stopped:
        main(["--port", "70000"])
    assert stopped.value.code == 2


def test_cli_announces_its_port_and_answers():
    env = {**os.environ, TOKEN_ENV: TOKEN}
    process = subprocess.Popen(
        [sys.executable, "-m", "ayna_agent.rpc", "--port", "0"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    try:
        ready = json.loads(process.stdout.readline())
        assert ready["event"] == "listening"

        async def client():
            uri = f"ws://{HOST}:{ready['port']}"
            async with connect(uri, additional_headers=auth()) as websocket:
                return [
                    await roundtrip(websocket, request("ping")),
                    await roundtrip(websocket, request("listWindows", id=2)),
                ]

        ping, windows = asyncio.run(asyncio.wait_for(client(), timeout=10))
        assert ping["result"]["agentVersion"] == __version__
        # No UIA backend is wired in yet (#12).
        assert windows["error"]["code"] == UIA_UNAVAILABLE
    finally:
        process.kill()
        process.wait(timeout=10)
