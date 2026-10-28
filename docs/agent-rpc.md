# Agent JSON-RPC (v0.1 built; v0.2 proposed)

How the Electron client talks to the automation agent on the same machine. Part of the agent JSON-RPC contract (see `memory-bank/project/architecture.md`), frozen at G1 (week 7). Code: `agent/ayna_agent/rpc.py` (#16).

Everything up to [Trying it by hand](#trying-it-by-hand) is v0.1, as built. The last section, [Proposed (#149)](#proposed-149-step-results-and-healing-proposals-v02-draft), is a draft for v0.2 that is not implemented and may still change until its ADR is accepted.

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

Once it listens, the agent prints exactly one line on **stdout** and nothing else there:

```json
{"event": "listening", "port": 53124}
```

Logs go to stderr. To stop the agent, kill its process tree (`taskkill /F /T /PID <pid>` on Windows): a venv's `python.exe` is a launcher whose child is the real interpreter (`memory-bank/learnings.md`, 2026-10-25).

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
- Replies on one connection come in request order. UI Automation calls run one at a time on a single agent thread.
- In v0.1 only the client sends requests. v0.2 (proposed, #149) adds notifications that the agent sends during a run; see the last section.

## Methods

### `ping`

Checks that the agent is alive and which contract it speaks. No params.

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
| `bounds` | [left, top, right, bottom] | Screen pixels as UI Automation reports them. |

Without a UI Automation backend (not Windows, or before #12) the method answers `-32001`.

### `snapshot`

Captures one window's whole UIA subtree.

| Param | Type | Meaning |
|---|---|---|
| `handle` | positive integer | A `handle` from `listWindows`. |

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

## Errors

| Code | Name | When |
|---|---|---|
| -32700 | Parse error | The frame is not valid JSON. `id` is `null`. |
| -32600 | Invalid Request | Not one request object: a batch, a binary frame, `jsonrpc` not `"2.0"`, `method` not a string, `params` neither object nor array, or a bad `id` type (then `id` is `null`). |
| -32601 | Method not found | Unknown method name. |
| -32602 | Invalid params | Params given to a method that takes none, or a missing, extra or wrongly typed param. |
| -32603 | Internal error | The agent failed unexpectedly. The message names the exception and the traceback is in the agent's stderr. |
| -32000 | Window not found | No top-level window has that handle (any more). |
| -32001 | UI Automation unavailable | The agent cannot read UI Automation here: not Windows, or no backend yet. |

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

## Proposed (#149): step results and healing proposals (v0.2 draft)

> **Proposed, not implemented.** Decision: `memory-bank/decisions/2026-10-28-healing-proposal-transport.md`, status Proposed until Galip, Ömerfaruk and Hasan approve it. Playback (#40, #73) implements it. Until then `ping` answers `rpcVersion` `"0.1"`; with these messages it answers `"0.2"` (an addition).

When no element matches a step's target after the wait, the step ends as "repair proposed" with the top 3 candidate elements and the reasons for their scores (#73). This section says how that result reaches the client, which forwards it to the server unchanged. The CLI runner (#61) builds the same document without JSON-RPC and writes it to the same server endpoint.

### Notifications from the agent

- During a run the agent sends JSON-RPC **notifications**: objects with `jsonrpc`, `method` and `params` and no `id`. The client tells them apart from replies by the missing `id`.
- The client never answers a notification, not even with an error, and ignores a notification method it does not know, so that later minor versions can add some.
- All notifications of a run go to the connection that sent the run request, in the order the agent sends them.

### The run request (defined by #40)

Playback's request belongs to #40. For healing it must carry these params, which the agent copies into its results:

| Param | Type | Meaning |
|---|---|---|
| `runId` | UUID string | The Run the client created on the server before starting (#44, #51). |
| `appVersionId` | UUID string | The AppVersion under test. |
| `targets` (name for #40 to settle) | object | Per logical name, the element the object resolved to before: `serverElementId` (graph `Element.id`) and `properties`, with the keys of `agent/ayna_agent/heal/scorer.py`. Candidates are compared against it. |

Illustrative, with the request name used in the step schema ADR (`steps` shortened):

```json
→ {"jsonrpc": "2.0", "id": 7, "method": "runSteps", "params": {
    "runId": "3f6c2a9e-8b1d-4e7a-9c55-0d2f4b7a1e90",
    "appVersionId": "9a1d7c3e-2f4b-4c8a-b6e5-7d0f1a2b3c4d",
    "steps": {"version": "0.1", "steps": ["… four steps; the third is Click login.loginButton …"]},
    "targets": {
      "login.loginButton": {
        "serverElementId": "c2d4e6f8-0a1b-4c3d-8e5f-7a9b1c3d5e7f",
        "properties": {"automationId": "QApplication.loginWindow.loginButton", "name": "Giriş",
                       "controlType": "Button", "className": "QPushButton", "bounds": [600, 412, 720, 444],
                       "parentPath": "loginWindow/credentialsBox", "siblingIndex": 4, "windowTitle": "AYNA Trial"}
      }
    }
  }}
```

### `run.stepResult`

One notification per step of the run, in step order, when the step has finished or will not run.

| Field | Type | Meaning |
|---|---|---|
| `runId` | UUID string | From the run request. |
| `stepIndex` | integer ≥ 0 | The step's position in the run, from 0. With `runId`, the key of the result. |
| `stepId` | UUID string or null | The step's server id; `null` for a step that was never saved. |
| `status` | string | `passed`, `failed`, `repairProposed` or `notRun`. |
| `snapshot` | object | Only with `repairProposed`: the snapshot document (`schemas/snapshot.schema.json`, #12) of the window the candidates came from, captured when the wait ended. |
| `healingProposal` | object | Only with `repairProposed`: a document per `schemas/healing-proposal.schema.json` (below). |

#40 (duration, message), #54 (screenshot) and #63 (failure category) add their own fields to this message.

- `status` is `repairProposed` exactly when no element matched the target after the wait (TBD-5) and at least one candidate is left after playback's minimum score (#73). Then `snapshot` and `healingProposal` are both present, `healingProposal.snapshotId` is the snapshot's id, and the proposal's `runId`, `stepIndex` and `stepId` equal the result's.
- No element matched and no candidate is left: `failed`, without a proposal.
- After a `repairProposed` result the agent performs no further step of that test and never acts on a candidate. Each remaining step gets a `notRun` result, in order (TBD-6). Then the run ends as #40 defines.

A step that passed:

```json
← {"jsonrpc": "2.0", "method": "run.stepResult", "params": {
    "runId": "3f6c2a9e-8b1d-4e7a-9c55-0d2f4b7a1e90", "stepIndex": 1,
    "stepId": "4a8e2f10-6c3b-4d9e-a157-3e0b9c6d2f81", "status": "passed"}}
```

The login button was renamed (`loginButton` → `signInButton`, "Giriş" → "Oturum Aç"), so nothing matches it any more. Shortened: the snapshot, the target's and candidates' properties and candidates 2 and 3 are cut; the whole proposal is `schemas/examples/healing-proposal/login-button-renamed.json`.

```json
← {"jsonrpc": "2.0", "method": "run.stepResult", "params": {
    "runId": "3f6c2a9e-8b1d-4e7a-9c55-0d2f4b7a1e90", "stepIndex": 2,
    "stepId": "b7e4d1c2-5a3f-4e8b-9d61-2c0a7f3e5b14", "status": "repairProposed",
    "snapshot": {"…": "the snapshot document 5e8f0a1b-3c2d-4e6f-8a9b-1c0d2e3f4a5b (#12)"},
    "healingProposal": {
      "version": "0.1",
      "runId": "3f6c2a9e-8b1d-4e7a-9c55-0d2f4b7a1e90", "stepIndex": 2,
      "stepId": "b7e4d1c2-5a3f-4e8b-9d61-2c0a7f3e5b14",
      "logicalName": "login.loginButton",
      "appVersionId": "9a1d7c3e-2f4b-4c8a-b6e5-7d0f1a2b3c4d",
      "snapshotId": "5e8f0a1b-3c2d-4e6f-8a9b-1c0d2e3f4a5b",
      "target": {"serverElementId": "c2d4e6f8-0a1b-4c3d-8e5f-7a9b1c3d5e7f",
                 "properties": {"automationId": "QApplication.loginWindow.loginButton", "name": "Giriş", "…": "…"}},
      "scorer": {"id": "similo-v0",
                 "weights": {"automationId": "3/2", "name": "3/2", "controlType": "3/2", "nearestLabel": "3/2",
                             "className": "1/2", "parentPath": "1/2", "siblingIndex": "1/2", "location": "1/2",
                             "area": "1/2", "shape": "1/2", "windowTitle": "1/2"}},
      "candidatesScored": 4,
      "candidates": [
        {"rank": 1, "elementId": "e23",
         "element": {"automationId": "QApplication.loginWindow.signInButton", "name": "Oturum Aç", "…": "…"},
         "score": "151/192",
         "contributions": {"automationId": "9/64", "name": "1/48", "controlType": "3/16", "className": "1/16",
                           "parentPath": "1/16", "siblingIndex": "1/16", "location": "1/16", "area": "1/16",
                           "shape": "1/16", "windowTitle": "1/16"},
         "similarities": {"automationId": "3/4", "name": "1/9", "controlType": "1", "className": "1",
                          "parentPath": "1", "siblingIndex": "1", "location": "1", "area": "1", "shape": "1",
                          "windowTitle": "1"}},
        {"rank": 2, "elementId": "e25", "score": "3969/6400", "…": "…"},
        {"rank": 3, "elementId": "e24", "score": "19/32", "…": "…"}
      ]}}}
```

How to read it: the target has no `nearestLabel`, so that property is not compared, and the weights of the ten compared properties add up to 8. `name` contributes 3/2 × 1/9 / 8 = 1/48, and the contributions add up exactly to the score: 9/64 + 1/48 + 3/16 + 7 × 1/16 = 151/192 ≈ 0.786.

The remaining step:

```json
← {"jsonrpc": "2.0", "method": "run.stepResult", "params": {
    "runId": "3f6c2a9e-8b1d-4e7a-9c55-0d2f4b7a1e90", "stepIndex": 3,
    "stepId": "e1f3a5c7-9b2d-4f6e-8a0c-2d4f6b8e0a13", "status": "notRun"}}
```

### The healing proposal

Schema: `schemas/healing-proposal.schema.json` (version `0.1`, proposed). Examples, including a CLI run without a server: `schemas/examples/healing-proposal/`.

| Field | Type | Meaning |
|---|---|---|
| `version` | string | `"0.1"`. |
| `runId`, `stepIndex`, `stepId` | | As in the step result. |
| `logicalName` | string | The repository object that was not found. |
| `appVersionId` | UUID string or null | The AppVersion under test; approving a candidate makes the object resolve to it for this version. `null` only without a server. |
| `snapshotId` | string | Id of the snapshot sent with the result. |
| `target` | object | `serverElementId` (UUID or null) and `properties`: what the candidates were compared against, exactly as scored. |
| `scorer` | object | `id` (`"similo-v0"`) and `weights` per property. |
| `candidatesScored` | integer | How many candidates were ranked. |
| `candidates` | array of 1–3 | By score descending, then `elementId` ascending. Each has `rank` (1 = best), `elementId` (the element's id inside the snapshot, not a server id), `element` (its properties as scored), `score`, `contributions` and `similarities` (per compared property). |

**Numbers are exact fractions written as strings**, as Python's `str(Fraction)` writes them: `"0"`, `"1"` or `"p/q"` in lowest terms; never floats. Scores, contributions and similarities lie in [0, 1]; weights may be larger. For each candidate, `contributions[p] = weights[p] × similarities[p] / Σ weights` over the compared properties, and the contributions add up exactly to `score`; the compared properties are the same for every candidate. Convert to a double only to draw.

### What the client does with a result

1. Show it live.
2. Append its `params`, unchanged, to a durable outbox.
3. One forwarder writes the outbox in order to the server, with `params` as the body of `PUT /api/runs/{runId}/results/{stepIndex}` (proposed in the ADR; the REST contract is #51's and #74's). The ADR lists the retry rules for an unreachable server, a client closed mid-run and a rejected document.

The client does not need to read the proposal to forward it. There are no new error codes: notifications get no reply.
