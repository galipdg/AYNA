"""Shared fixtures: a fake Ollama server on 127.0.0.1, so no model is needed in CI."""

import json
import socketserver
import threading
import time
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

DATA = Path(__file__).resolve().parent / "data"

# (path, request body or None) -> (HTTP status, JSON body, delay in seconds, extra headers)
Responder = Callable[[str, dict | None], tuple[int, object, float, dict]]


class FakeOllama:
    def __init__(self) -> None:
        self.url = ""
        self.requests: list[tuple[str, dict | None]] = []
        self.respond: Responder = lambda path, body: (200, {}, 0.0, {})


class LocalServer(ThreadingHTTPServer):
    def server_bind(self):
        # HTTPServer.server_bind does a reverse DNS lookup (getfqdn), which
        # can take half a minute on a machine without a resolver.
        socketserver.TCPServer.server_bind(self)
        self.server_name, self.server_port = self.server_address[:2]


@pytest.fixture
def fake_ollama():
    state = FakeOllama()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self._answer(None)

        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            self._answer(json.loads(self.rfile.read(length)))

        def _answer(self, body):
            state.requests.append((self.path, body))
            status, payload, delay, headers = state.respond(self.path, body)
            time.sleep(delay)
            data = json.dumps(payload).encode("utf-8")
            try:
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                for name, value in headers.items():
                    self.send_header(name, value)
                self.end_headers()
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError):
                pass  # the client gave up (timeout tests)

        def log_message(self, *args):
            pass

    server = LocalServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, args=(0.05,), daemon=True)
    thread.start()
    state.url = f"http://127.0.0.1:{server.server_address[1]}"
    yield state
    server.shutdown()
    server.server_close()


@pytest.fixture
def spike_objects() -> dict[str, str]:
    """The fake customer-records repository of the #7 spike (17 objects)."""
    return json.loads((DATA / "spike-objects.json").read_text(encoding="utf-8"))
