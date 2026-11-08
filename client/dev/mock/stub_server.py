"""Stub AYNA server for client development: GET /api/health, GET and POST /api/apps,
in memory, no login. Usage: python stub_server.py [port] (default 8099).

Prints {"event": "listening", "port": n} on stdout once it accepts connections and
exits on stdin EOF, so `npm run dev:mock` can wait for it and never leaves it behind.
"""

import json
import os
import sys
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

APPS = [{"id": str(uuid.uuid4()), "name": "Spy Trial", "technology": "Qt", "description": None}]


class Handler(BaseHTTPRequestHandler):
    def send_json(self, code, body):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/api/health":
            return self.send_json(200, {"status": "UP", "db": "UP"})
        if self.path == "/api/apps":
            return self.send_json(200, APPS)
        self.send_json(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/api/apps":
            return self.send_json(404, {"error": "not found"})
        length = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(length) or b"{}")
        app = {
            "id": str(uuid.uuid4()),
            "name": body.get("name", "?"),
            "technology": body.get("technology", "Qt"),
            "description": body.get("description"),
        }
        APPS.append(app)
        self.send_json(201, app)

    def log_message(self, format, *args):
        sys.stderr.write(f"[stub-server] {format % args}\n")


def exit_on_stdin_eof():
    sys.stdin.buffer.read()
    os._exit(0)


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8099
    try:
        server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    except OSError as error:
        sys.stderr.write(f"[stub-server] cannot listen on 127.0.0.1:{port}: {error}\n")
        sys.exit(1)
    threading.Thread(target=exit_on_stdin_eof, daemon=True).start()
    print(json.dumps({"event": "listening", "port": port}), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:  # Ctrl+C in the terminal reaches the whole process group
        pass


if __name__ == "__main__":
    main()
