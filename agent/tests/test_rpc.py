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
    SNAPSHOT_TIMEOUT,
    TOKEN_ENV,
    UIA_UNAVAILABLE,
    WINDOW_NOT_FOUND,
    Dispatcher,
    SnapshotTimeout,
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
        self.calls = []

    def list_windows(self):
        self.threads.append(threading.current_thread().name)
        self.calls.append(("listWindows",))
        return [WINDOW]

    def snapshot(self, handle, timeout_ms):
        self.threads.append(threading.current_thread().name)
        self.calls.append(("snapshot", handle, timeout_ms))
        if handle != WINDOW["handle"]:
            raise WindowNotFound(handle)
        return {"snapshotId": "fake", "window": WINDOW, "elements": []}


class BrokenDesktop(FakeDesktop):
    def list_windows(self):
        raise RuntimeError("COM blew up")


class SlowDesktop(FakeDesktop):
    """snapshot blocks until the test releases it."""

    def __init__(self):
        super().__init__()
        self.release = threading.Event()

    def snapshot(self, handle, timeout_ms):
        self.release.wait(timeout=10)
        return super().snapshot(handle, timeout_ms)


class TimedOutDesktop(FakeDesktop):
    def snapshot(self, handle, timeout_ms):
        raise SnapshotTimeout(f"walk stopped after {timeout_ms} ms")


class LifecycleDesktop(FakeDesktop):
    def __init__(self):
        super().__init__()
        self.events = []

    def setup(self):
        self.events.append(("setup", threading.current_thread().name))

    def close(self):
        self.events.append(("close", threading.current_thread().name))

    def list_windows(self):
        self.events.append(("listWindows", threading.current_thread().name))
        return super().list_windows()


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
    desktop = FakeDesktop()
    reply = call(desktop, request("snapshot", {"handle": 1001}))
    assert reply["result"]["window"] == WINDOW
    assert desktop.calls == [("snapshot", 1001, None)]


def test_snapshot_passes_its_time_budget_on():
    desktop = FakeDesktop()
    reply = call(desktop, request("snapshot", {"handle": 1001, "timeoutMs": 2000}))
    assert "result" in reply
    assert desktop.calls == [("snapshot", 1001, 2000)]


def test_snapshot_over_budget():
    reply = call(
        TimedOutDesktop(), request("snapshot", {"handle": 1001, "timeoutMs": 5})
    )
    assert reply["error"]["code"] == SNAPSHOT_TIMEOUT
    assert "after 5 ms" in reply["error"]["message"]


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
    **{
        f"timeoutMs {value!r}": (
            request("snapshot", {"handle": 1001, "timeoutMs": value}, id=7),
            INVALID_PARAMS,
            7,
        )
        for value in (0, -1, 600_001, 1.5, "2000", True, None)
    },
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


def test_ping_answers_while_a_snapshot_runs():
    desktop = SlowDesktop()

    async def client(uri, server):
        async with connect(uri, additional_headers=auth()) as websocket:
            try:
                await websocket.send(json.dumps(request("snapshot", {"handle": 1001})))
                await websocket.send(json.dumps(request("ping", id=2)))
                first = json.loads(await asyncio.wait_for(websocket.recv(), 5))
            finally:
                desktop.release.set()
            second = json.loads(await asyncio.wait_for(websocket.recv(), 5))
            return first, second

    first, second = run_with_server(desktop, client)
    assert first["id"] == 2 and "result" in first
    assert second["id"] == 1 and second["result"]["window"] == WINDOW


def test_uia_calls_run_in_arrival_order():
    desktop = FakeDesktop()
    messages = [
        request("snapshot", {"handle": 1001}, id=1),
        request("listWindows", id=2),
        request("snapshot", {"handle": 5, "timeoutMs": 10}, id=3),
        request("listWindows", id=4),
    ]

    async def client(uri, server):
        async with connect(uri, additional_headers=auth()) as websocket:
            for message in messages:
                await websocket.send(json.dumps(message))
            replies = [json.loads(await websocket.recv()) for _ in messages]
        return sorted(reply["id"] for reply in replies)

    assert run_with_server(desktop, client) == [1, 2, 3, 4]
    assert desktop.calls == [
        ("snapshot", 1001, None),
        ("listWindows",),
        ("snapshot", 5, 10),
        ("listWindows",),
    ]


def test_backend_setup_and_close_run_once_on_the_worker_thread():
    desktop = LifecycleDesktop()

    async def client(uri, server):
        async with connect(uri, additional_headers=auth()) as websocket:
            await roundtrip(websocket, request("listWindows"))
            await roundtrip(websocket, request("listWindows", id=2))

    run_with_server(desktop, client)
    assert [name for name, _ in desktop.events] == [
        "setup",
        "listWindows",
        "listWindows",
        "close",
    ]
    assert len({thread for _, thread in desktop.events}) == 1


def test_failed_backend_setup_stops_the_server():
    class NoCom(FakeDesktop):
        def setup(self):
            raise OSError("CoInitializeEx failed")

    async def run():
        async with serve_rpc(NoCom(), TOKEN):
            pass

    with pytest.raises(OSError):
        asyncio.run(run())


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


def start_agent():
    """The agent as the client starts it: token in the env, stdin a pipe."""
    return subprocess.Popen(
        [sys.executable, "-m", "ayna_agent.rpc", "--port", "0"],
        env={**os.environ, TOKEN_ENV: TOKEN},
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )


def test_cli_announces_its_port_and_answers():
    process = start_agent()
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
        # The CLI wires in the real recognition backend (#12). On a Windows desktop it
        # answers with the window list; anywhere else it answers -32001 per call, which is
        # what `docs/agent-rpc.md` promises and why the server still starts there.
        if "error" in windows:
            assert windows["error"]["code"] == UIA_UNAVAILABLE
        else:
            assert isinstance(windows["result"]["windows"], list)
    finally:
        process.kill()
        process.wait(timeout=10)


def test_cli_exits_when_its_stdin_closes():
    process = start_agent()
    try:
        assert json.loads(process.stdout.readline())["event"] == "listening"
        process.stdin.close()
        assert process.wait(timeout=10) == 0
    finally:
        process.kill()
        process.wait(timeout=10)
