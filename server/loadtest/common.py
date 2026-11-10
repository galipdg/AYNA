"""Shared HTTP client for the load test (#152): Python standard library only, so it runs on the closed network."""

from __future__ import annotations

import http.client
import json
import time
import urllib.parse
from dataclasses import dataclass


class ApiError(Exception):
    def __init__(self, method: str, path: str, status: int, body: str):
        super().__init__(f"{method} {path} -> {status}: {body[:300]}")
        self.status = status


@dataclass
class Response:
    status: int
    body: object
    seconds: float


class Client:
    """One keep-alive connection, as one AYNA client keeps; not thread-safe, so one per thread."""

    def __init__(self, base_url: str, token: str | None = None, timeout: float = 30.0):
        parsed = urllib.parse.urlsplit(base_url)
        if parsed.scheme != "http":
            raise ValueError(f"only http:// is supported, got {base_url}")
        self.host = parsed.hostname or "localhost"
        self.port = parsed.port or 80
        self.timeout = timeout
        self.token = token
        self.conn: http.client.HTTPConnection | None = None

    def _connection(self) -> http.client.HTTPConnection:
        if self.conn is None:
            self.conn = http.client.HTTPConnection(self.host, self.port, timeout=self.timeout)
        return self.conn

    def close(self) -> None:
        if self.conn is not None:
            self.conn.close()
            self.conn = None

    def request(self, method: str, path: str, body: object | None = None) -> Response:
        """Sends one request and returns status, parsed body and wall time; the time covers sending and reading."""
        headers = {"Accept": "application/json"}
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        for attempt in (1, 2):
            conn = self._connection()
            start = time.perf_counter()
            try:
                conn.request(method, path, body=data, headers=headers)
                raw = conn.getresponse()
                payload = raw.read()
            except (http.client.RemoteDisconnected, BrokenPipeError, ConnectionResetError):
                # The server closed an idle keep-alive connection; reconnect once, as a browser does.
                self.close()
                if attempt == 2:
                    raise
                continue
            seconds = time.perf_counter() - start
            text = payload.decode() if payload else ""
            try:
                parsed = json.loads(text) if text else None
            except json.JSONDecodeError:
                parsed = text
            return Response(raw.status, parsed, seconds)
        raise AssertionError("unreachable")

    def call(self, method: str, path: str, body: object | None = None) -> object:
        """Like `request`, but raises `ApiError` on anything but 2xx and returns only the body."""
        response = self.request(method, path, body)
        if not 200 <= response.status < 300:
            raise ApiError(method, path, response.status, json.dumps(response.body))
        return response.body


def login(base_url: str, username: str, password: str) -> Client:
    client = Client(base_url)
    answer = client.call("POST", "/api/auth/login", {"username": username, "password": password})
    client.token = answer["token"]
    return client


def wait_until_up(base_url: str, seconds: float = 180.0) -> None:
    """Waits for `/api/health` to say UP; the server starts after Neo4j and runs its migrations first."""
    deadline = time.monotonic() + seconds
    last = "no answer"
    while time.monotonic() < deadline:
        client = Client(base_url, timeout=5)
        try:
            response = client.request("GET", "/api/health")
            if response.status == 200 and isinstance(response.body, dict) and response.body.get("status") == "UP":
                return
            last = f"{response.status} {response.body}"
        except OSError as exc:
            last = str(exc)
        finally:
            client.close()
        time.sleep(2)
    raise SystemExit(f"server at {base_url} not UP after {seconds:.0f} s: {last}")
