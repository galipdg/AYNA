# Mock server and agent

`npm run dev:mock` (from `client/`) opens the client against a stub server and a fake agent, so screens can be checked on any OS without the real server, Neo4j or a UI Automation backend. Needs Python 3 on PATH (`python3`; `python` on Windows), standard library only. Development only: not packed into the app.

- `stub_server.py` — `GET /api/health`, `GET`/`POST /api/apps` in memory, no login, on `127.0.0.1:8099`.
- `ayna_agent/rpc.py` — fake agent: `ping`, `listWindows` (from `windows.json`), `snapshot` answers `-32001`. The client starts it as it starts the real agent (`python -m ayna_agent.rpc`); `run.mjs` puts this folder first on `PYTHONPATH`.
- `windows.json` — the window list; edit it and press the Spy's Refresh. It covers a normal window, an empty title with an unknown process, a long title on a monitor left of the primary, and a minimized window (Windows reports those at −32000).

Options, after `--`: `--port <n>` for the stub server, `--windows <file>` for another window list, `--no-uia` to answer `listWindows` with `-32001` as on a machine without UI Automation. Example: `npm run dev:mock -- --no-uia`.

In the app, enter `http://127.0.0.1:8099` as the server address. Ctrl+C or closing the app stops all three processes.

Once the server needs a login (#60), the stub server must answer the login calls too.
