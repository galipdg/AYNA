"""Localhost JSON-RPC 2.0 server over WebSocket, the client's way into the agent (#16).

The client starts the agent with the session token in an environment variable, never
on the command line (other processes can read command lines):

    AYNA_AGENT_TOKEN=<token> python -m ayna_agent.rpc --port 0

The server binds 127.0.0.1 only, refuses every opening handshake without
`Authorization: Bearer <token>`, and prints one JSON line on stdout once it listens:
{"event": "listening", "port": 53124}. Methods, errors and examples: docs/agent-rpc.md.
"""

from __future__ import annotations

import argparse
import asyncio
import hmac
import json
import logging
import os
import sys
from collections.abc import AsyncIterator, Awaitable, Callable
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from http import HTTPStatus
from typing import Any, Protocol

from websockets.asyncio.server import Server, ServerConnection, serve
from websockets.exceptions import ConnectionClosed
from websockets.http11 import Request, Response

from ayna_agent import __version__

HOST = "127.0.0.1"
RPC_VERSION = "0.1"
TOKEN_ENV = "AYNA_AGENT_TOKEN"
MIN_TOKEN_LENGTH = 16

# JSON-RPC 2.0 error codes; -32000 to -32099 are ours (docs/agent-rpc.md).
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603
WINDOW_NOT_FOUND = -32000
UIA_UNAVAILABLE = -32001

log = logging.getLogger(__name__)


class WindowNotFound(Exception):
    """No top-level window has the requested handle (it may have closed)."""


class UiaUnavailable(Exception):
    """UI Automation cannot run here: not Windows, or no backend yet."""


class Desktop(Protocol):
    """What the server needs from the recognition layer.

    Calls block. The server runs them all on one dedicated worker thread, so a backend
    can initialise COM there once and never sees two calls at the same time.
    """

    def list_windows(self) -> list[dict[str, Any]]: ...

    def snapshot(self, handle: int) -> dict[str, Any]: ...


class UnavailableDesktop:
    """Stand-in until recognition/ provides a UI Automation backend (#12)."""

    def __init__(self, reason: str) -> None:
        self.reason = reason

    def list_windows(self) -> list[dict[str, Any]]:
        raise UiaUnavailable(self.reason)

    def snapshot(self, handle: int) -> dict[str, Any]:
        raise UiaUnavailable(self.reason)


class RpcError(Exception):
    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


Params = dict[str, Any] | list[Any]


class Dispatcher:
    """Turns one request text into one response text, or None for a notification."""

    def __init__(self, desktop: Desktop, executor: ThreadPoolExecutor) -> None:
        self._desktop = desktop
        self._executor = executor
        self._methods: dict[str, Callable[[Params], Awaitable[Any]]] = {
            "ping": self._ping,
            "listWindows": self._list_windows,
            "snapshot": self._snapshot,
        }

    async def handle(self, text: str) -> str | None:
        try:
            request = json.loads(text)
        except (ValueError, RecursionError) as exc:
            return _error(None, PARSE_ERROR, f"Parse error: {exc}")
        if not isinstance(request, dict):
            return _error(
                None, INVALID_REQUEST, "Invalid Request: one object, no batches"
            )
        request_id = request.get("id")
        if not _valid_id(request_id):
            return _error(None, INVALID_REQUEST, "Invalid Request: bad id type")
        try:
            name, params = _parse(request)
        except RpcError as exc:
            # Answered even without an id: only a valid request can be a notification.
            return _error(request_id, exc.code, exc.message)

        notification = "id" not in request
        try:
            method = self._methods.get(name)
            if method is None:
                raise RpcError(METHOD_NOT_FOUND, f"Method not found: {name}")
            result = await method(params)
            if notification:
                return None
            return _encode({"jsonrpc": "2.0", "id": request_id, "result": result})
        except RpcError as exc:
            return None if notification else _error(request_id, exc.code, exc.message)
        except Exception as exc:
            log.exception("%s failed", name)
            if notification:
                return None
            return _error(request_id, INTERNAL_ERROR, f"Internal error: {exc!r}")

    async def _ping(self, params: Params) -> dict[str, Any]:
        _expect_no_params(params)
        return {"agentVersion": __version__, "rpcVersion": RPC_VERSION}

    async def _list_windows(self, params: Params) -> dict[str, Any]:
        _expect_no_params(params)
        return {"windows": await self._run(self._desktop.list_windows)}

    async def _snapshot(self, params: Params) -> dict[str, Any]:
        if not isinstance(params, dict) or set(params) != {"handle"}:
            raise RpcError(INVALID_PARAMS, 'Invalid params: expected {"handle": <int>}')
        handle = params["handle"]
        if not isinstance(handle, int) or isinstance(handle, bool) or handle <= 0:
            raise RpcError(
                INVALID_PARAMS, "Invalid params: handle must be a positive int"
            )
        return await self._run(self._desktop.snapshot, handle)

    async def _run(self, call: Callable[..., Any], *args: Any) -> Any:
        loop = asyncio.get_running_loop()
        try:
            return await loop.run_in_executor(self._executor, call, *args)
        except WindowNotFound as exc:
            raise RpcError(WINDOW_NOT_FOUND, f"Window not found: {exc}") from exc
        except UiaUnavailable as exc:
            raise RpcError(
                UIA_UNAVAILABLE, f"UI Automation unavailable: {exc}"
            ) from exc


def _valid_id(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    return value is None or isinstance(value, str | int)


def _parse(request: dict[str, Any]) -> tuple[str, Params]:
    if request.get("jsonrpc") != "2.0":
        raise RpcError(INVALID_REQUEST, 'Invalid Request: jsonrpc must be "2.0"')
    name = request.get("method")
    if not isinstance(name, str):
        raise RpcError(INVALID_REQUEST, "Invalid Request: method must be a string")
    params = request.get("params", {})
    if not isinstance(params, dict | list):
        raise RpcError(
            INVALID_REQUEST, "Invalid Request: params must be object or array"
        )
    return name, params


def _expect_no_params(params: Params) -> None:
    if params:
        raise RpcError(INVALID_PARAMS, "Invalid params: this method takes none")


def _encode(message: dict[str, Any]) -> str:
    return json.dumps(message, ensure_ascii=False, separators=(",", ":"))


def _error(request_id: Any, code: int, message: str) -> str:
    error = {"code": code, "message": message}
    return _encode({"jsonrpc": "2.0", "id": request_id, "error": error})


def require_token(
    token: str,
) -> Callable[[ServerConnection, Request], Response | None]:
    """Handshake check: exactly one `Authorization: Bearer <token>`, constant-time compare.

    Browsers cannot set this header on a WebSocket, so a web page on the same machine
    cannot open a session even if it finds the port.
    """
    expected = f"Bearer {token}".encode()

    def process_request(
        connection: ServerConnection, request: Request
    ) -> Response | None:
        values = request.headers.get_all("Authorization")
        if len(values) == 1 and hmac.compare_digest(values[0].encode(), expected):
            return None
        log.warning("refused a handshake without a valid token")
        return connection.respond(HTTPStatus.UNAUTHORIZED, "Missing or wrong token\n")

    return process_request


@asynccontextmanager
async def serve_rpc(
    desktop: Desktop, token: str, port: int = 0
) -> AsyncIterator[Server]:
    """Listen on 127.0.0.1:`port` (0 = any free port) until the context exits."""
    if len(token) < MIN_TOKEN_LENGTH:
        raise ValueError(
            f"the session token needs at least {MIN_TOKEN_LENGTH} characters"
        )
    with ThreadPoolExecutor(max_workers=1, thread_name_prefix="ayna-uia") as executor:
        dispatcher = Dispatcher(desktop, executor)

        # Requests on one connection are answered in order; UIA work is serial anyway.
        async def handler(connection: ServerConnection) -> None:
            try:
                async for message in connection:
                    if isinstance(message, bytes):
                        reply = _error(
                            None, INVALID_REQUEST, "Invalid Request: use text frames"
                        )
                    else:
                        reply = await dispatcher.handle(message)
                    if reply is not None:
                        await connection.send(reply)
            except ConnectionClosed:
                log.info("client went away without closing the connection")

        # No compression: it only costs CPU on a loopback connection.
        async with serve(
            handler, HOST, port, process_request=require_token(token), compression=None
        ) as server:
            yield server


def bound_port(server: Server) -> int:
    return server.sockets[0].getsockname()[1]


async def _serve_forever(desktop: Desktop, token: str, port: int) -> None:
    async with serve_rpc(desktop, token, port) as server:
        print(
            json.dumps({"event": "listening", "port": bound_port(server)}), flush=True
        )
        await server.serve_forever()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m ayna_agent.rpc", description=__doc__.splitlines()[0]
    )
    parser.add_argument(
        "--port", type=int, default=0, help="TCP port on 127.0.0.1; 0 = any free port"
    )
    args = parser.parse_args(argv)
    if not 0 <= args.port <= 65535:
        parser.error("--port must be between 0 and 65535")
    # Popped so that apps the agent starts later do not inherit the token.
    token = os.environ.pop(TOKEN_ENV, "")
    if len(token) < MIN_TOKEN_LENGTH:
        parser.error(
            f"set {TOKEN_ENV} to the session token ({MIN_TOKEN_LENGTH}+ characters)"
        )

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    # Swapped for the recognition/ backend once it exists (#12, hasan).
    desktop = UnavailableDesktop("no UI Automation backend yet (#12)")
    try:
        asyncio.run(_serve_forever(desktop, token, args.port))
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
