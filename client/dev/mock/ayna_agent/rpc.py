"""Fake AYNA agent for client development on any OS: a subset of agent RPC 0.1
(docs/agent-rpc.md) on a stdlib-only WebSocket server.

The client starts it like the real one (`python -m ayna_agent.rpc --port 0`, token in
AYNA_AGENT_TOKEN); `npm run dev:mock` puts this folder's parent first on PYTHONPATH.
Answers `ping`, `listWindows` (windows from AYNA_MOCK_WINDOWS, a JSON file) and
`snapshot` (the document in AYNA_MOCK_SNAPSHOT for every listed window, with that
window's handle and a fresh id and time). With AYNA_MOCK_UIA=off both answer -32001, as on
a machine without UI Automation; with AYNA_MOCK_SNAPSHOT_TIMEOUT=on `snapshot` answers
-32002. Exits on stdin EOF, like the real agent.
"""

import base64
import hashlib
import json
import logging
import os
import socket
import struct
import sys
import threading
import uuid
from datetime import datetime

WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
TOKEN = os.environ.get("AYNA_AGENT_TOKEN", "")
UIA = os.environ.get("AYNA_MOCK_UIA", "on") != "off"
SNAPSHOT_TIMEOUT = os.environ.get("AYNA_MOCK_SNAPSHOT_TIMEOUT", "off") == "on"
WINDOWS_FILE = os.environ.get(
    "AYNA_MOCK_WINDOWS", os.path.join(os.path.dirname(__file__), "..", "windows.json")
)
SNAPSHOT_FILE = os.environ.get(
    "AYNA_MOCK_SNAPSHOT", os.path.join(os.path.dirname(__file__), "..", "snapshot.json")
)


# Same format as the real agent's log, so the client reads these lines as routine logging.
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("fake-agent").info


def no_uia(rid):
    message = "UI Automation is not available (fake agent)"
    return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32001, "message": message}}


def error(rid, code, message):
    return {"jsonrpc": "2.0", "id": rid, "error": {"code": code, "message": message}}


def load_json(path):
    with open(path, encoding="utf-8") as file:
        return json.load(file)  # read per call, so edits show on the Spy's next request


def snapshot(rid, params):
    handle = params.get("handle") if isinstance(params, dict) else None
    if not isinstance(handle, int) or isinstance(handle, bool) or handle < 1:
        return error(rid, -32602, "Invalid params: handle must be a positive int")
    if not UIA:
        return no_uia(rid)
    if not any(window["handle"] == handle for window in load_json(WINDOWS_FILE)):
        return error(rid, -32000, f"Window not found: {handle}")
    if SNAPSHOT_TIMEOUT:
        return error(rid, -32002, "Snapshot timeout: walk exceeded 5000 ms (fake agent)")
    document = load_json(SNAPSHOT_FILE)
    document["snapshotId"] = str(uuid.uuid4())
    document["capture"]["startedAt"] = datetime.now().astimezone().isoformat(timespec="seconds")
    document["window"]["handle"] = handle
    document["elements"][0]["element"]["nativeWindowHandle"] = handle
    return {"jsonrpc": "2.0", "id": rid, "result": document}


def handle_request(request):
    rid, method = request.get("id"), request.get("method")
    if method == "ping":
        result = {"agentVersion": "0.0.0-mock", "rpcVersion": "0.1"}
        return {"jsonrpc": "2.0", "id": rid, "result": result}
    if method == "listWindows":
        if not UIA:
            return no_uia(rid)
        return {"jsonrpc": "2.0", "id": rid, "result": {"windows": load_json(WINDOWS_FILE)}}
    if method == "snapshot":
        return snapshot(rid, request.get("params"))
    return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": "Method not found"}}


def recv_exact(conn, n):
    buffer = b""
    while len(buffer) < n:
        chunk = conn.recv(n - len(buffer))
        if not chunk:
            raise ConnectionError
        buffer += chunk
    return buffer


def send_frame(conn, opcode, payload=b""):
    head = bytes([0x80 | opcode])
    n = len(payload)
    if n < 126:
        head += bytes([n])
    elif n < 65536:
        head += bytes([126]) + struct.pack(">H", n)
    else:
        head += bytes([127]) + struct.pack(">Q", n)
    conn.sendall(head + payload)


def handshake(conn):
    data = b""
    while b"\r\n\r\n" not in data:
        chunk = conn.recv(4096)
        if not chunk:
            return False
        data += chunk
    lines = data.split(b"\r\n\r\n")[0].decode().split("\r\n")
    headers = {}
    for line in lines[1:]:
        if ":" in line:
            key, value = line.split(":", 1)
            headers[key.strip().lower()] = value.strip()
    if headers.get("authorization") != f"Bearer {TOKEN}":
        log("rejected a connection with a wrong token")
        conn.sendall(b"HTTP/1.1 401 Unauthorized\r\nContent-Length: 0\r\n\r\n")
        return False
    key = headers.get("sec-websocket-key", "") + WS_GUID
    accept = base64.b64encode(hashlib.sha1(key.encode()).digest()).decode()
    conn.sendall(
        (
            "HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
            f"Sec-WebSocket-Accept: {accept}\r\n\r\n"
        ).encode()
    )
    return True


def serve(conn):
    if not handshake(conn):
        return
    log("client connected")
    while True:
        b1, b2 = recv_exact(conn, 2)
        opcode, n = b1 & 0x0F, b2 & 0x7F
        if n == 126:
            n = struct.unpack(">H", recv_exact(conn, 2))[0]
        elif n == 127:
            n = struct.unpack(">Q", recv_exact(conn, 8))[0]
        mask = recv_exact(conn, 4) if b2 & 0x80 else b"\0\0\0\0"
        payload = bytes(c ^ mask[i % 4] for i, c in enumerate(recv_exact(conn, n)))
        if opcode == 0x8:  # close
            send_frame(conn, 0x8, payload[:2])
            return
        if opcode == 0x9:  # ping frame
            send_frame(conn, 0xA, payload)
        elif opcode == 0x1:
            request = json.loads(payload)
            if request.get("method") != "ping":
                log(f"<- {request.get('method')}")
            send_frame(conn, 0x1, json.dumps(handle_request(request)).encode())


def serve_safe(conn):
    try:
        serve(conn)
    except (ConnectionError, OSError):
        pass
    finally:
        conn.close()
        log("client disconnected")


def exit_on_stdin_eof():
    sys.stdin.buffer.read()
    log("stdin closed, exiting")
    os._exit(0)


def main():
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen()
    threading.Thread(target=exit_on_stdin_eof, daemon=True).start()
    print(json.dumps({"event": "listening", "port": server.getsockname()[1]}), flush=True)
    try:
        while True:
            conn, _ = server.accept()
            threading.Thread(target=serve_safe, args=(conn,), daemon=True).start()
    except KeyboardInterrupt:  # Ctrl+C in the terminal reaches the whole process group
        pass


if __name__ == "__main__":
    main()
