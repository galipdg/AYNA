# Agent JSON-RPC (v0.1)

How the Electron client talks to the automation agent on the same machine. Part of the agent JSON-RPC contract (see `memory-bank/project/architecture.md`), frozen at G1 (week 7). Code: `agent/ayna_agent/rpc.py` (#16).

- [JSON-RPC 2.0](https://www.jsonrpc.org/specification) over one WebSocket on `127.0.0.1`.
- Only the client's main process connects. The renderer goes through the preload API, as for everything else.
- `rpcVersion` (returned by `ping`) changes when this contract changes: minor for additions, major for anything that breaks an existing client.

## Starting the agent

The client spawns the agent once per session and makes a fresh random token for it, for example 32 random bytes as hex. The token goes in an environment variable. It must not go on the command line, because other processes can read command lines.

```
AYNA_AGENT_TOKEN=<token> python -m ayna_agent.rpc --port 0
```

| Input | Meaning |
|---|---|
| `AYNA_AGENT_TOKEN` | Session token, at least 16 characters. Without it the agent exits with code 2. The agent removes it from its own environment, so the apps it starts do not inherit it. |
| `--port <n>` | TCP port on `127.0.0.1`. `0` (default) lets the OS pick a free one, which avoids a race between choosing a port and binding it. |
| stdin | A pipe the client keeps open and never writes to. The agent exits (code 0) when it reaches EOF, which the OS causes when the client quits **or crashes**, so the agent never outlives its client with UIA access. A terminal on stdin is not watched (stop with Ctrl+C). An empty stdin such as `/dev/null` or `NUL` makes the agent exit at once. |

Once it listens, the agent prints exactly one line on **stdout** and nothing else there:

```json
{"event": "listening", "port": 53124}
```

Logs go to stderr. To stop the agent, close its stdin. If it has not exited after a grace period, kill its process tree with the PID of the process **you spawned** (`taskkill /F /T /PID <pid>` on Windows). A venv's `python.exe` is a launcher whose child is the real interpreter (`memory-bank/learnings.md`, 2026-10-25), so only the launcher's PID reaches both.

The agent process is per-monitor DPI aware (v2), so every coordinate it reports is in physical pixels. The recognition backend sets this at startup (#12).

## Connecting

Connect to `ws://127.0.0.1:<port>`. Use the literal address, not `localhost`, which may resolve to `::1`. The opening handshake must carry exactly one header:

```
Authorization: Bearer <token>
```

A handshake that is missing it, has a wrong token, uses another scheme or repeats the header is refused with **HTTP 401** before any message is exchanged. A token in the URL is ignored. Browsers cannot set this header on a WebSocket, so a web page on the same machine cannot open a session even if it finds the port. Use a Node client that can set handshake headers, for example the `ws` package: `new WebSocket(url, { headers: { Authorization: "Bearer " + token } })`.

## Messages

- One request object per **text** frame, UTF-8 JSON. Batches (arrays) and binary frames are refused with `-32600`.
- `params` is by name (an object). It may be left out for methods without parameters.
- `id` is a string, an integer or `null`. A request without `id` is a notification: it runs, and no reply is sent.
- Each request starts as soon as it arrives, and replies come **in any order**: match them by `id`. UI Automation calls (`listWindows`, `snapshot`) still run one at a time, in the order they arrived, on a single agent thread. So `ping` answers at once even while a long snapshot runs.
- Liveness: the library answers WebSocket ping frames at any time, and the `ping` method works too.

## Methods

### `ping`

Checks that the agent answers and which contract it speaks. It does not wait for running UIA calls. No params.

```json
→ {"jsonrpc": "2.0", "id": 1, "method": "ping"}
← {"jsonrpc": "2.0", "id": 1, "result": {"agentVersion": "0.0.0", "rpcVersion": "0.1"}}
```

### `listWindows`

The visible top-level windows on the desktop, for the Spy's window picker. No params.

```json
→ {"jsonrpc": "2.0", "id": 2, "method": "listWindows"}
← {"jsonrpc": "2.0", "id": 2, "result": {"windows": [
    {"handle": 395942, "title": "AYNA Trial", "className": "LoginWindow",
     "processId": 7316, "processName": "python.exe", "bounds": [320, 180, 960, 660]}
  ]}}
```

| Field | Type | Meaning |
|---|---|---|
| `handle` | integer | Native window handle (HWND). Valid only while the window exists; pass it to `snapshot`. |
| `title` | string | The window's UIA Name. Qt apps that set an `accessibleName` show that instead of the title (`memory-bank/learnings.md`). |
| `className` | string | UIA ClassName. For Qt it is the Python/C++ class name, the most stable handle for a window. |
| `processId` | integer | Owning process. |
| `processName` | string or null | Exe file name without path; `null` when it cannot be read (e.g. an elevated process). |
| `bounds` | [left, top, right, bottom] | Physical pixels in virtual-screen coordinates. Values are negative on a monitor left of or above the primary one. |

Without a UI Automation backend (not Windows, or before #12) the method answers `-32001`.

### `snapshot`

Captures one window's UIA subtree.

| Param | Type | Meaning |
|---|---|---|
| `handle` | positive integer, required | A `handle` from `listWindows`. |
| `timeoutMs` | integer 1–600000, optional | Time budget for the walk. If left out, the agent's default applies (set with #12). When the budget runs out, the agent stops the walk and answers `-32002`. v0.1 returns no partial document. |

Unknown params are refused with `-32602`. New optional ones (e.g. a depth or element limit from #12) are a minor `rpcVersion` bump.

The result is one snapshot document as defined by `schemas/snapshot.schema.json` (#12). A success example will be added here together with that schema. Until then:

```json
→ {"jsonrpc": "2.0", "id": 3, "method": "snapshot", "params": {"handle": 395942}}
← {"jsonrpc": "2.0", "id": 3, "error": {"code": -32001, "message": "UI Automation unavailable: no UI Automation backend yet (#12)"}}
```

A window that has closed since `listWindows`:

```json
→ {"jsonrpc": "2.0", "id": 4, "method": "snapshot", "params": {"handle": 12}}
← {"jsonrpc": "2.0", "id": 4, "error": {"code": -32000, "message": "Window not found: 12"}}
```

A walk that did not finish within its budget (the message text comes from the backend):

```json
→ {"jsonrpc": "2.0", "id": 6, "method": "snapshot", "params": {"handle": 395942, "timeoutMs": 2000}}
← {"jsonrpc": "2.0", "id": 6, "error": {"code": -32002, "message": "Snapshot timeout: walk stopped after 2000 ms"}}
```

## Errors

| Code | Name | When |
|---|---|---|
| -32700 | Parse error | The frame is not valid JSON. `id` is `null`. |
| -32600 | Invalid Request | Not one request object: a batch, a binary frame, `jsonrpc` not `"2.0"`, `method` not a string, `params` neither object nor array, or a bad `id` type (then `id` is `null`). |
| -32601 | Method not found | Unknown method name. |
| -32602 | Invalid params | Params given to a method that takes none, or a missing, unknown or wrongly typed param. |
| -32603 | Internal error | The agent failed unexpectedly. The message names the exception and the traceback is in the agent's stderr. |
| -32000 | Window not found | No top-level window has that handle (any more). |
| -32001 | UI Automation unavailable | The agent cannot read UI Automation here: not Windows, or no backend yet. |
| -32002 | Snapshot timeout | The snapshot walk used up its `timeoutMs` budget (or the default) before it finished. Retry with a bigger budget, or report it. |

Errors from a request without `id` are not sent, except Invalid Request: only a valid request can be a notification.

```json
→ {"jsonrpc": "2.0", "id": 5, "method": "snapshot", "params": {"handle": "395942"}}
← {"jsonrpc": "2.0", "id": 5, "error": {"code": -32602, "message": "Invalid params: handle must be a positive int"}}
```

## Trying it by hand

From `agent/`, with the dev install (`pip install -e ".[dev]"`):

```
AYNA_AGENT_TOKEN=0123456789abcdef0123 python -m ayna_agent.rpc
```

In a second shell (bash or zsh; replace the port with the one printed):

```
python -c "
import asyncio, json
from websockets.asyncio.client import connect
async def main():
    async with connect('ws://127.0.0.1:53124', additional_headers={'Authorization': 'Bearer 0123456789abcdef0123'}) as ws:
        await ws.send(json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'ping'}))
        print(await ws.recv())
asyncio.run(main())
"
```

On Windows `cmd.exe`, set the variable first with `set AYNA_AGENT_TOKEN=...`.
