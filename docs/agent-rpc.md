# Agent JSON-RPC (1.0; healing draft proposed)

How the Electron client talks to the automation agent on the same machine. Part of the agent JSON-RPC contract (see `memory-bank/project/architecture.md`), frozen at G1 (week 7). Code: `agent/ayna_agent/rpc.py` (#16).

Everything up to [Trying it by hand](#trying-it-by-hand) is **1.0**, as built: v0.1 plus `runSteps` (#26) and `elementFromPoint` (#22), frozen at G1 (#52, ADR `2026-11-08-contracts-v1-freeze`). `schemas/agent-rpc.schema.json` fixes the message shapes and is checked by both sides (`client/src/main/__tests__/agentContract.test.ts`, `agent/tests/test_rpc_contract.py`). The last section, [Proposed (#149)](#proposed-149-step-results-and-healing-proposals-draft), is a draft for a later 1.x that is not implemented. Its transport ADR is accepted; the parts that come from the proposal schema 0.2 ADR may still change until that one is accepted.

> **Version numbers, settled 2026-11-15 (galip).** The freeze made everything built before it **1.0**, `runSteps` and `elementFromPoint` included, so they do not need a 1.1 of their own; `ping` answers `"1.0"`. **1.1** is a failed step's `category` (FR-35, #63; proposed in PR #240 with ADR `2026-11-15-failure-category`): the agent answers `"1.1"` in the change that fills it. The healing draft below takes the next minor number when it is built. A line further down that still says `"0.1"` predates this note.

- [JSON-RPC 2.0](https://www.jsonrpc.org/specification) over one WebSocket on `127.0.0.1`.
- Only the client's main process connects. The renderer goes through the preload API, as for everything else.
- `rpcVersion` (returned by `ping`) changes when this contract changes: minor for additions, major for anything that breaks an existing client. It is `RPC_VERSION` in `rpc.py` and follows `$defs/version` in `schemas/agent-rpc.schema.json`: the same major version, and never a minor version the schema does not have yet. The schema may be ahead while a field it adds is not built (a test checks both). A 1.x client accepts any 1.y agent.

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
- In 1.0 only the client sends requests. The healing draft (proposed, #149) adds notifications that the agent sends during a run; see the last section.

## Methods

### `ping`

Checks that the agent answers and which contract it speaks. It does not wait for running UIA calls. No params.

```json
→ {"jsonrpc": "2.0", "id": 1, "method": "ping"}
← {"jsonrpc": "2.0", "id": 1, "result": {"agentVersion": "0.0.0", "rpcVersion": "1.0"}}
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
| `title` | string or null | The window's UIA Name; `null` when it cannot be read. Qt apps that set an `accessibleName` show that instead of the title (`memory-bank/learnings.md`). |
| `className` | string or null | UIA ClassName; `null` when it cannot be read. For Qt it is the Python/C++ class name, the most stable handle for a window. |
| `processId` | integer or null | Owning process; `null` when Windows will not say. Intended: the schema allows it and the client reads it (#52). |
| `processName` | string or null | Exe file name without path; `null` when it cannot be read (e.g. an elevated process). |
| `bounds` | [left, top, right, bottom] | Physical pixels in virtual-screen coordinates. Values are negative on a monitor left of or above the primary one. The rectangle the window **appears** to occupy (DWM extended frame bounds), not `GetWindowRect`: since Windows 10 a resizable window carries an *invisible* resize border outside its visible frame, and including it makes a highlight land outside the window (measured 8 px at 150 % scaling, #184). This is deliberately **not** the same rectangle as `snapshot`'s `window.bounds`, which is the window element's UI Automation rectangle and excludes the title bar. |

Without a UI Automation backend (not Windows, or before #12) the method answers `-32001`.

### `snapshot`

Captures one window's UIA subtree.

| Param | Type | Meaning |
|---|---|---|
| `handle` | positive integer, required | A `handle` from `listWindows`. |
| `timeoutMs` | integer 1–600000, optional | Time budget for the walk. If left out, the agent's default of **5 000 ms** applies (#12, measured in #161). When the budget runs out, the agent stops the walk and answers `-32002`. The agent never returns a partial document. |

Unknown params are refused with `-32602`. New optional ones are a minor `rpcVersion` bump. There is deliberately no depth or element limit: an incomplete walk has exactly one outcome, `-32002`, because a partial tree is the one input healing must never rank candidates from (RS 0.6 FR-29/FR-35, "search incomplete"; ADR snapshot schema v0).

The result is one snapshot document as defined by `schemas/snapshot.schema.json` (#12): the window it came from, what the walk cost, and every element as a flat pre-order list of `{id, parentId, element}`, a parent always before its children, so one pass builds the tree. `element` is the descriptor of `schemas/element.schema.json`. Element ids are opaque and scoped to the document; a healing proposal's `candidates[].elementId` resolves against them, and its `snapshotAt` is `capture.startedAt`.

Shortened — the trial app's login window has 14 elements; the whole document is
[`schemas/examples/snapshot/trial-login.json`](../schemas/examples/snapshot/trial-login.json):

```json
→ {"jsonrpc": "2.0", "id": 3, "method": "snapshot", "params": {"handle": 657704}}
← {"jsonrpc": "2.0", "id": 3, "result": {
    "version": "0.1",
    "snapshotId": "5e8f0a1b-3c2d-4e6f-8a9b-1c0d2e3f4a5b",
    "capture": {"startedAt": "2026-10-31T17:42:19+03:00", "durationMs": 312, "budgetMs": 5000,
                "elementCount": 14, "readErrors": 0, "agentVersion": "0.0.0",
                "featureVersion": "features-v0"},
    "app": {"exeName": "python.exe", "fileVersion": "3.13.150.1013"},
    "window": {"handle": 657704, "title": "AYNA Trial - Login", "className": "LoginWindow",
               "bounds": [560, 210, 1010, 415], "dpi": 120},
    "elements": [
      {"id": "e0", "parentId": null,
       "element": {"automationId": "QApplication.loginWindow", "name": "AYNA Trial - Login",
                   "controlType": "Window", "className": "LoginWindow", "frameworkId": "Qt",
                   "bounds": [560, 210, 1010, 415], "dpi": 120, "siblingIndex": 0,
                   "windowTitle": "AYNA Trial - Login", "enabled": true, "offscreen": false,
                   "nativeWindowHandle": 657704}},
      {"id": "e8", "parentId": "e0",
       "element": {"automationId": "QApplication.loginWindow.usernameInput", "name": "Username",
                   "controlType": "Edit", "className": "QLineEdit", "frameworkId": "Qt",
                   "bounds": [648, 223, 995, 255],
                   "dpi": 120, "parentPath": "Window", "siblingIndex": 2,
                   "nearestLabel": "Username", "nearestLabelSource": "geometric",
                   "windowTitle": "AYNA Trial - Login", "enabled": true, "offscreen": false}},
      {"…": "eleven more, e1–e7 and e9–e13"}
    ]}}
```

The agent writes the document in a canonical form — fixed key order, two-space indent, LF, UTF-8
unescaped — so that reading a saved snapshot and writing it again gives the same file back
(`agent/ayna_agent/recognition/snapshot.py`).

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

### `elementFromPoint`

The element at a point, for the Spy's pick hotkey (#22).

| Param | Type | Meaning |
|---|---|---|
| `x`, `y` | integer, required, **signed** | A point in physical pixels, in virtual-desktop coordinates. Negative values are valid: a maximised window on a scaled display starts at a negative origin. The agent is per-monitor-v2 DPI aware, so it converts nothing — send the point the OS gave you. |

Unknown params are refused with `-32602`.

**The answer names the element in the snapshot the client already has.** It does not describe
the hit element on its own, because the properties that identify an element are derived from
its surroundings: `nearestLabel` from its siblings and its parent's siblings, `parentPath` from
its ancestors. Reading those for one element costs a property read per sibling — unbounded in a
list — and an element whose siblings were *not* read would come back with `nearestLabel` absent,
which cannot be told apart from "this element has no label". So one element would have two
different descriptors depending on whether a snapshot happened to be open. Instead the agent
keeps the snapshot it took last and answers out of it, which is also what the Spy wants: select
the tree node it is already showing.

| Field | Type | Meaning |
|---|---|---|
| `handle` | integer or null | The top-level window under the point, the same kind of handle `listWindows` reports. Null when there is no window there. |
| `bounds` | `[left, top, right, bottom]` or null | The hit element's rectangle, physical pixels. |
| `snapshotId` | string or null | The snapshot of **that** window the agent still holds. Null when it holds none. |
| `elementId` | string or null | The element's `id` in that snapshot. |
| `element` | object or null | That snapshot's descriptor for it, unchanged. |

**A point is never an error.** A hotkey pressed over nothing answers the same shape with nulls,
so the client needs one code path. The three states it can tell apart:

- `snapshotId` null — nothing has been captured for this window yet: offer to capture it.
- `snapshotId` set, `elementId` null — the window has changed since the capture: offer to
  capture it again.
- both set — select that node.

**The element is identified, not just located.** The stored rectangle finds the candidates and
`CompareElements` decides which one is the element — every candidate, even a single one. Bounds
alone would be enough only while a window keeps the same elements in the same rectangles, and
the changes that break that are ordinary: a tab switched, a list scrolled, a wizard page
replaced. Each leaves the rectangle in place with another element behind it, so without the
comparison the answer would be the stale node with nothing saying so. When no candidate
compares equal, the deepest same-bounds candidate is still the answer — a wrapper chain, and
the raw view the hit test answers from is not the control view the walk reads — but only if its
stored `controlType`, `name` and `automationId` are still the hit element's; otherwise the reply
is the second state above.

The agent holds **one** window's snapshot: the one taken **last** by any `snapshot` call,
whoever made it — a repository import's capture (#15) replaces the Spy's. So a `snapshotId`
that is not the one the client is showing means the same thing as none at all, and a `snapshot`
of another window replaces it. Only `-32001` is possible, when the host has no UI Automation.

```json
→ {"jsonrpc": "2.0", "id": 8, "method": "elementFromPoint", "params": {"x": 785, "y": 312}}
← {"jsonrpc": "2.0", "id": 8, "result": {
    "handle": 657704,
    "bounds": [614, 300, 814, 326],
    "snapshotId": "5e8f0a1b-3c2d-4e6f-8a9b-1c0d2e3f4a5b",
    "elementId": "e8",
    "element": {"automationId": "QApplication.loginWindow.usernameInput", "name": "Username",
                "controlType": "Edit", "nearestLabel": "Username", "bounds": [614, 300, 814, 326]}}}
```

A point in a window nothing has been captured for:

```json
→ {"jsonrpc": "2.0", "id": 9, "method": "elementFromPoint", "params": {"x": 40, "y": 1050}}
← {"jsonrpc": "2.0", "id": 9, "result": {
    "handle": 66768, "bounds": [0, 1040, 1920, 1080],
    "snapshotId": null, "elementId": null, "element": null}}
```

Measured on Windows 11 at 120 DPI against the trial app, taken after the capture, which is the
Spy's order (#22 asks for under 300 ms): median **2.2 ms**, p95 3.0 ms, worst 3.2 ms over 50
calls, and 2.5 / 3.7 / 4.2 ms on a second run. All 50 named an element, so the identity
comparison the answer now makes is inside the noise of the two runs.

### `runSteps`

Plays a step document against one window and answers with one result per step, in order (#26,
#40). **All six keywords of the step schema are performed**: Click, Type, Wait, Select,
SelectRow and Verify. A keyword outside the schema comes back as that step's `failed` result
naming itself, so a test is never reported as passed because a keyword was skipped.

| Param | Type | Meaning |
|---|---|---|
| `handle` | integer | The window to play against, from `listWindows`. #40 makes this optional and finds the window from a target's `windowTitle`; until then an explicit handle keeps window discovery (FR-35's "unexpected window") a separate problem. |
| `steps` | object | A step document, `{version, steps}` (`schemas/step.schema.json`). Versions **0.1 and 0.2** are both read: v0.2 only adds SelectRow, `row` and the three row checkpoints, so every 0.1 document means the same thing in both. |
| `targets` | object | Per logical name, the repository object's property sets: `properties` (its primary, "Find by") and optional `fallback` (its "Backup", #25). `serverElementId` and `featureVersion` from the healing request below are accepted and ignored. |
| `runId`, `appVersionId` | UUID string, optional | Accepted and ignored, so the client can send one request shape before and after #40. |
| `defaultTimeoutMs` | integer 1–600000, optional | What a step without `timeoutMs` waits. Default **10 000 ms** (RS NFR-05). A step's own `timeoutMs: 0` means check once and never means "use this". |

**How a target is resolved.** The window is read and every element is matched against
`properties`; the result is one of three, and all three are different outcomes:

- **exactly one** — the element is acted on;
- **none** — `fallback` is tried, and if that also matches none the step keeps waiting and then
  fails as FR-35 *element not found*;
- **more than one** — the step fails too, and **playback never picks one**. UI Automation does
  not promise a stable child order between runs, so a guess would act on a different element on
  a different day; the message says how many matched and asks for another property. `fallback`
  is tried only when `properties` matches *nothing*: a fallback replaces a primary set, it
  cannot narrow one.

Waiting is a re-read every 250 ms until the step can proceed or its time runs out — never a
fixed sleep.

**What a step waits for is "ready", which is more than "resolves"** (#40): the target resolves
to exactly one element *and* that element is neither disabled nor off screen, which is what the
schema means by ready. `enabled`/`offscreen` that the provider does not report count as ready,
since refusing would make every step of such an application time out. A **Verify is the
exception** and waits only for resolution: a checkpoint may be *about* a disabled or offscreen
element, and the check does its own re-reading afterwards. Two waits, two words in the message:
` within N ms` for an element that never appeared, ` after N ms` for a state that never changed.

**Actions use UI Automation patterns only, never coordinates.** A pattern that is present can
still refuse (a disabled button has `Invoke`), so a refusal falls through to the next one.

| Keyword | How |
|---|---|
| `Click` | `Invoke`, `Toggle`, `SelectionItem.Select`, then `LegacyIAccessible.DoDefaultAction`. |
| `Type` | `Value.SetValue`, then focus-and-keys. A read-only ValuePattern fails the step rather than being worked around. |
| `Wait` | Nothing: the pre-step wait above *is* the keyword, so nothing performed it. |
| `Select` | The item of the target whose text is `value` (ValuePattern value when non-empty, else Name — the schema's rule for a cell), then `SelectionItem.Select`, then `Invoke`. **A closed combo box has no items at all**, so when the target offers `ExpandCollapse` it is expanded and the window **read again** before looking; a box it opened is closed again on success. Last, only after the whole wait, an **editable** box takes `value` as text through `Value.SetValue`, read back to confirm, and reports `performedWith: "SetValue"`. |
| `SelectRow` | The row `row` addresses — `{index}` from the top, counted from 1, or the first row whose cell equals `{value}` (in `{column}` when given) — through `SelectionItem.Select`, then MSAA's `LegacyIAccessible.Select` (KeePass 2's list has nothing else). Never `Invoke`: invoking a row *activates* it. |
| `Verify` | The checkpoint, re-read until it holds or the time runs out. |

**Rows come from the captured tree, in the three shapes the v0.2 ADR measured**: the item is the
row and its children are the cells (KeePass 2's `ListItem`s, a WinForms `DataGridView` row); the
items *are* the cells and only `GridItemPattern` says which row they belong to (a Qt table has no
row element); or the item is a one-cell row (a `QListWidget`). `rowCount` prefers
`GridPattern.RowCount`, which also counts rows a virtualised grid has not materialised. The
column names come from the same rule the server uses to fill `RepoObject.columns` (#221), so the
column a tester picked in the editor is the column playback reads. A target that reports no
columns at all makes a keyed row match nothing rather than failing on the column; a column that
is not among the ones it does report is a mistake, and the message lists the ones it has.

**A SelectRow on a view that selects cells rather than rows** selects the row's first cell, which
is the ADR's rule, and the step **passes with a message saying so** instead of claiming the row:
a pilot app's selection behaviour is not ours to change, and silence would be the one outcome a
tester cannot debug.

**On a table with no row element (Qt), SelectRow also makes the row the current one** (#265).
`SelectionItem.Select` changes Qt's selection but not its current row, so an application that
acts on "the current row" would act on another one. After selecting, the agent focuses the
table through UI Automation and presses `Ctrl+Home`, then `Down` once per row above it: the keys
a person would press, never a coordinate. It then checks the row is still the selected one. When
that cannot be done (the table will not take the focus, the row is more than 500 rows down, or
the keys landed elsewhere), the step still **passes with a message** that the row is selected
but not current, and the selection is put back on the row the step named.

A result carries `stepIndex`, `status` (`passed`, `failed` or `notRun`), `durationMs`, and when
known `stepId`, `message`, `matched` (`primary` or `fallback` — a fallback match is what #73
heals) and `performedWith` (the pattern that did it). **A failed step stops the run** and every
step after it is `notRun` (TBD-6).

**The screenshot (#54, FR-19).** Every step that *ran* is photographed straight after it acted,
and its result carries `screenshotPath` and `screenshotAt`:

| Field | Type | Meaning |
|---|---|---|
| `screenshotPath` | string, optional | Absolute path to the PNG **on the machine the agent runs on**. The client reads the bytes from there and uploads them under #51's contract (`PUT /api/runs/{runId}/results/{stepIndex}/screenshot`). |
| `screenshotAt` | string, optional | When the image was taken: ISO 8601 with a UTC offset, to the millisecond. |

The image travels as a path, not as base64 in this message: a 50-step run is about 15 MB of PNG,
base64 would add a third to that, and the agent and the client always share a machine. The PNG is
cropped to the window as a person sees it — DWM's extended frame bounds, not `GetWindowRect` with
its invisible resize border — so the image and a candidate's `bounds` are in one coordinate space
(physical pixels, virtual-desktop coordinates; see [Starting the agent](#starting-the-agent)).

**Both fields are absent whenever there is no image, and that is not an error.** A `notRun` step
is never photographed, because it never reached a screen; and a capture that fails is logged and
skipped rather than failing the step, since the commonest reason a step fails is that the window
is not what the test expected — including gone. A reader (#59's report, the client's step list)
must treat a missing screenshot as normal.

Nothing deletes these files. The agent cannot know when the client has finished uploading them,
so whoever owns the run owns the cleanup.

**One directory per run — once `runId` reaches the backend.** `UiaDesktop.run_steps` names the
directory after the run when it is given the run id, and falls back to a timestamp otherwise.
`_run_steps` still only accepts `runId` and drops it (the table above), so **today every call
opens its own directory**. That is invisible to a caller that plays a whole run in one call, and
wrong for one that sends a step at a time as #44's client does: a seven-step run leaves seven
folders, each with a single `step-0000.png`, and there is no one folder for the client to delete.
Passing `params["runId"]` through is one line in `rpc.py` (#54, asked of galip).

**Why a step failed (#63, FR-35).** A `failed` step may carry a `category`, one of
`elementNotFound`, `unexpectedWindow`, `assertionFailed`, `timeout` or `searchIncomplete` (ADR
*A failed step's category*). It appears **only** with `status: failed`, never more than one, and
a reader shows an unknown value as it is, because new ones come in a minor version.

**It is absent whenever the failure was not about the application under test**, and that is a
decision rather than a gap. A keyword this agent has not implemented, a step document it
refuses, a property set it cannot match on, a provider that refuses the action — none of those
is evidence about the application, and the field is read by RQ2 and RQ5. A `timeout` that was
really "this agent has no `SelectRow` yet" would be AYNA measuring its own unfinished state and
filing it under the application's flakiness, and nothing downstream could separate the two
again. `agent/ayna_agent/playback/triage.py` is the single place that decides, and the agent's
decision log keeps a finer `reason` for every failure, including the uncategorised ones.

Two of the five have a boundary worth stating. **More than one element matched is
`elementNotFound`** — no *unique* element matched and playback never picks one. **An element
that matched but never became visible and enabled is `timeout`, not `elementNotFound`** — the
difference tells a tester whether to fix the locator or to wait longer.

```json
→ {"jsonrpc": "2.0", "id": 7, "method": "runSteps", "params": {
    "handle": 657704,
    "steps": {"version": "0.1", "steps": [
      {"keyword": "Type", "target": "login.userNameInput", "value": "admin"},
      {"keyword": "Click", "target": "login.loginButton"}]},
    "targets": {
      "login.userNameInput": {"properties": {"automationId": "QApplication.loginWindow.usernameInput"}},
      "login.loginButton": {"properties": {"automationId": "QApplication.loginWindow.loginButton"},
                            "fallback": {"name": "Login", "controlType": "Button"}}}}}
← {"jsonrpc": "2.0", "id": 7, "result": {"results": [
    {"stepIndex": 0, "status": "passed", "durationMs": 31, "matched": "primary", "performedWith": "SetValue",
     "screenshotPath": "C:\\Users\\you\\AppData\\Local\\Temp\\ayna-screenshots\\run-20261115-140311-004812\\step-0000.png",
     "screenshotAt": "2026-11-15T14:03:11.250+03:00"},
    {"stepIndex": 1, "status": "failed", "durationMs": 10000, "matched": "primary",
     "category": "elementNotFound",
     "message": "no element matches login.loginButton (automationId=…) within 10000 ms",
     "screenshotPath": "C:\\Users\\you\\AppData\\Local\\Temp\\ayna-screenshots\\run-20261115-140311-004812\\step-0001.png",
     "screenshotAt": "2026-11-15T14:03:21.402+03:00"}]}}
```

A document the agent cannot read at all is `-32602`; a handle that is not a top-level window is
`-32000`, and a window that cannot be read inside its budget is `-32002`, because reading the
window is how a target is resolved.

**Not yet:** healing (#73), the `run.stepResult` notifications below, and finding the window
without a handle. `repairProposed` is not emitted until #74 is on `main`, as agreed on #223.
Screenshots came off this list with #54 and are documented above. `ping` still answers
`rpcVersion` `"0.1"`; see the note at the top about which number `runSteps` and
`elementFromPoint` belong to.

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

## Proposed (#149): step results and healing proposals (draft)

> **Agreed, not implemented.** Decision: `memory-bank/decisions/2026-10-28-healing-proposal-transport.md` (Accepted), extended by `memory-bank/decisions/2026-10-31-healing-proposal-schema-0-2.md` (**Proposed** until Galip, Ömerfaruk and Hasan approve it: proposal schema 0.2 and the review follow-ups below). Playback (#40, #73) implements it. Until then `ping` answers the version above (1.0, or 1.1 once `category` is filled); with these messages it answers the next minor version (an addition).

When no element matches a step's target after the wait, the step ends as "repair proposed" with the top 3 candidate elements and the reasons for their scores (#73). This section says how that result reaches the client, which forwards it to the server unchanged. The CLI runner (#61) builds the same document without JSON-RPC and writes it to the same server endpoint.

### Notifications from the agent

- During a run the agent sends JSON-RPC **notifications**: objects with `jsonrpc`, `method` and `params`.
- Notifications carry no `id` (JSON-RPC 2.0 notifications), so they answer no request. Replies come in any order (see [Messages](#messages)), so the client recognises a notification by the missing `id` and routes it by `method`, never by its position among replies.
- The client never answers a notification, not even with an error, and ignores a notification method it does not know, so that later minor versions can add some.
- All notifications of a run go to the connection that sent the run request, in the order the agent sends them.
- Nothing acknowledges a notification, and the agent never sends one again. A result lost between the client receiving it and writing it to the outbox (a client crash) is gone for good; that is why such a run is finished as `aborted`, which makes the gap visible instead of silent.
- While a failing step's candidates are collected the agent sends nothing, possibly for minutes (the snapshot walk; 278.5 s for one KeePass 2 window in #6). The draft has no progress message: the client shows the step after the last result as running, with its elapsed time (#44).

### The run request (defined by #40)

Playback's request belongs to #40. **Its first three params exist now** — see
[`runSteps`](#runsteps) (#26: `handle`, `steps`, `targets`, where a target carries the object's
primary *and* fallback property sets). `runId` and `appVersionId` are already accepted and
ignored, so the client can send one shape throughout. For healing the request must carry these
params, which the agent copies into its results:

| Param | Type | Meaning |
|---|---|---|
| `runId` | UUID string | The Run the client created on the server before starting (#44, #51). |
| `appVersionId` | UUID string | The AppVersion under test. |
| `targets` (name for #40 to settle) | object | Per logical name, the element the object resolved to before: `serverElementId` (graph `Element.id`), `featureVersion` (the feature version it was recorded with; left out when the server does not know it) and `properties`, with the keys of `agent/ayna_agent/heal/scorer.py`, `dpi` included when recorded. Candidates are compared against it. |

Illustrative, with the request name used in the step schema ADR (`steps` shortened):

```json
→ {"jsonrpc": "2.0", "id": 7, "method": "runSteps", "params": {
    "runId": "3f6c2a9e-8b1d-4e7a-9c55-0d2f4b7a1e90",
    "appVersionId": "9a1d7c3e-2f4b-4c8a-b6e5-7d0f1a2b3c4d",
    "steps": {"version": "0.1", "steps": ["… four steps; the third is Click login.loginButton …"]},
    "targets": {
      "login.loginButton": {
        "serverElementId": "c2d4e6f8-0a1b-4c3d-8e5f-7a9b1c3d5e7f",
        "featureVersion": "features-v0",
        "properties": {"automationId": "QApplication.loginWindow.loginButton", "name": "Giriş",
                       "controlType": "Button", "className": "QPushButton", "bounds": [600, 412, 720, 444],
                       "dpi": 96, "parentPath": "Window/Group", "siblingIndex": 4, "windowTitle": "AYNA Trial"}
      }
    }
  }}
```

### `run.stepResult`

One notification per step of the run, in step order, when the step has finished or will not run.

| Field | Type | Meaning |
|---|---|---|
| `runId` | UUID string | From the run request. |
| `stepIndex` | integer ≥ 0 | The step's position in the run, from 0. With `runId`, the key of the result. Deliberately unlike the 1-based row numbers a tester sees (`row.index`, PR #150): a screen adds 1 to show it. |
| `stepId` | UUID string or null | The step's server id; `null` for a step that was never saved. |
| `status` | string | `passed`, `failed`, `repairProposed` or `notRun`. |
| `snapshot` | object | Only with `repairProposed`: the snapshot document (`schemas/snapshot.schema.json`, #12) of the window the candidates came from, captured when the wait ended. |
| `healingProposal` | object | Only with `repairProposed`: a document per `schemas/healing-proposal.schema.json` (below). |

The other fields are the ones `runSteps` returns per step: `durationMs` and `message` (#40; the name `durationMs` matches `timeoutMs` and `budgetMs`, hasan on #193), `matched` and `performedWith`. #63 adds a failed step's `category` (proposed in PR #240), and #54 adds the screenshot's.

**Screenshot of a `repairProposed` step (#54).** The agent takes it immediately before the snapshot walk starts, not "at the same moment": a walk can take minutes, and the application may change meanwhile. The result records both times (`screenshotAt`, `snapshotAt`), so the approval screen can say how much older the image is than the geometry. **`screenshotAt` is settled by #54**: ISO 8601 with a UTC offset, to the millisecond, because steps are faster than a second. The screenshot's crop rectangle and the candidates' `bounds` are in the same coordinate space: physical pixels in virtual-desktop coordinates, which holds because the agent is per-monitor-v2 DPI aware (see [Starting the agent](#starting-the-agent)). `dpi` never rescales `bounds` for drawing. The image travels as a **path** (`screenshotPath`), settled by #54 above; the proposal itself carries no image.

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
      "version": "0.2",
      "runId": "3f6c2a9e-8b1d-4e7a-9c55-0d2f4b7a1e90", "stepIndex": 2,
      "stepId": "b7e4d1c2-5a3f-4e8b-9d61-2c0a7f3e5b14",
      "logicalName": "login.loginButton",
      "appVersionId": "9a1d7c3e-2f4b-4c8a-b6e5-7d0f1a2b3c4d",
      "snapshotId": "5e8f0a1b-3c2d-4e6f-8a9b-1c0d2e3f4a5b",
      "target": {"serverElementId": "c2d4e6f8-0a1b-4c3d-8e5f-7a9b1c3d5e7f", "featureVersion": "features-v0",
                 "properties": {"automationId": "QApplication.loginWindow.loginButton", "name": "Giriş", "…": "…"}},
      "scorer": {"id": "similo-v0", "featureVersion": "features-v0",
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

Schema: `schemas/healing-proposal.schema.json`, version `0.2` (proposed; ADR `2026-10-31-healing-proposal-schema-0-2`). It adds per-element `dpi` and the feature versions to 0.1, all optional, so a 0.1 document is valid once relabelled. Examples, including a CLI run without a server: `schemas/examples/healing-proposal/`.

| Field | Type | Meaning |
|---|---|---|
| `version` | string | `"0.2"`. |
| `runId`, `stepIndex`, `stepId` | | As in the step result. |
| `logicalName` | string | The repository object that was not found. |
| `appVersionId` | UUID string or null | The AppVersion under test; approving a candidate makes the object resolve to it for this version. `null` only without a server. |
| `snapshotId` | string | Id of the snapshot sent with the result. |
| `target` | object | `serverElementId` (UUID or null), `featureVersion` (optional: the feature version the target was recorded with, left out when unknown) and `properties`: what the candidates were compared against, exactly as scored. |
| `scorer` | object | `id` (`"similo-v0"`), `featureVersion` (`"features-v0"`: how the agent derived the candidates' `nearestLabel`, `parentPath`, `siblingIndex`, `windowTitle` and `dpi`; the agent always writes it) and `weights` per property. |
| `candidatesScored` | integer | How many candidates were ranked. |
| `candidates` | array of 1–3 | By score descending, then `elementId` ascending. Each has `rank` (1 = best), `elementId` (the element's id inside the snapshot, not a server id), `element` (its properties as scored), `score`, `contributions` and `similarities` (per compared property). |

Element properties (`target.properties`, each candidate's `element`) are the scorer's keys. `bounds` are physical pixels in virtual-desktop coordinates; `dpi` (optional integer, 96 = 100 %) is the DPI of the element's window, which the scorer uses to compare location and area in device-independent pixels. `dpi` is not a scored property, so it never appears in `weights`, `contributions` or `similarities`. A replay or comparison of stored proposals (#103, RQ5) groups them by `scorer.id` and `scorer.featureVersion`, and treats a proposal whose `target.featureVersion` differs from `scorer.featureVersion` as not comparable.

**Numbers are exact fractions written as strings**, as Python's `str(Fraction)` writes them: `"0"`, `"1"` or `"p/q"` in lowest terms; never floats. Scores, contributions and similarities lie in [0, 1]; weights may be larger. For each candidate, `contributions[p] = weights[p] × similarities[p] / Σ weights` over the compared properties, and the contributions add up exactly to `score`; the compared properties are the same for every candidate. Convert to a double only to draw.

### What the client does with a result

1. Append its `params`, unchanged, to a durable outbox, with the server URL the item is for. Append **before** showing: a result the client shows but has not stored is lost in a crash.
2. Show it live.
3. One forwarder writes the outbox in order, only to that server, with `params` as the body of `PUT /api/runs/{runId}/results/{stepIndex}` (proposed in the ADRs; the REST contract is #51's and #74's). An identical repeat answers 200; another body for the same key answers 409 and goes to the dead-letter file. The transport ADR lists the retry rules for an unreachable server, a client closed mid-run and a rejected document.

The client does not need to read the proposal to forward it. There are no new error codes: notifications get no reply.
