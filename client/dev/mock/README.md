# Mock server and agent

`npm run dev:mock` (from `client/`) opens the client against a stub server and a fake agent, so screens can be checked on any OS without the real server, Neo4j or a UI Automation backend. Needs Python 3 on PATH (`python3`; `python` on Windows), standard library only. Development only: not packed into the app.

- `stub_server.py` — `GET /api/health`, `GET`/`POST /api/apps` in memory, no login, on `127.0.0.1:8099`.
- `ayna_agent/rpc.py` — fake agent: `ping`, `listWindows` (from `windows.json`), `snapshot` (from `schemas/examples/snapshot/trial-login.json`, for any listed window; an unlisted handle answers `-32000`), `elementFromPoint` (out of the snapshot taken last, on the fake geometry of `windows.json` and the tree, not on what is really on screen), `runSteps` (#44: each step passes after 300 ms; a step whose value is `fail` fails with `assertionFailed` and the rest are `notRun`; nothing is played). The client starts it as it starts the real agent (`python -m ayna_agent.rpc`); `run.mjs` puts this folder first on `PYTHONPATH`.
- The tree is the trial app's login window (14 elements), the schema's own example from #12, read where it lives so it cannot drift (#204). Every listed window answers with it, with its own handle, a fresh `snapshotId` and the current time. To try another tree, copy it somewhere, pass `--snapshot <file>`, edit the copy and press Capture again.
- `windows.json` — the window list; edit it and press the Spy's Refresh. It covers a normal window, an empty title with an unknown process, a long title on a monitor left of the primary, and a minimized window (Windows reports those at −32000).

The pick key (⌘⇧A / Ctrl+Shift+A) in the Spy answers by where the cursor is on screen, in these fake coordinates: after capturing "AYNA Trial", (700, 240) is the Username field and (600, 350) the Login button; (300, 600) is inside "AYNA Trial" but on no element, which reads as "the window has changed"; (100, 30) is the uncaptured `Shell_TrayWnd`; (1300, 800) is no window. The Spy's footer shows the point it picked.

Options, after `--`: `--port <n>` for the stub server, `--windows <file>` for another window list, `--snapshot <file>` for another tree, `--no-uia` to answer `listWindows`, `snapshot` and `elementFromPoint` with `-32001` as on a machine without UI Automation, `--slow-snapshots` to make every walk take 20 s, so `snapshot` answers `-32002` (walk over its time budget) until Capture again sends a longer budget (#204). Example: `npm run dev:mock -- --no-uia`.

In the app, enter `http://127.0.0.1:8099` as the server address. Ctrl+C or closing the app stops all three processes.

Once the server needs a login (#60), the stub server must answer the login calls too.

`npm run demo` (`dev/demo/`) uses the same fake agent, but with the real server and sample data; `DEMO.md` at the repository root explains it. `fake-agent-env.mjs` is what the two share.
