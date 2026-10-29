# agent/ — Python automation agent and CLI runner

Owner: hasan (recognition/, playback/, ayna_cli/) · galip (heal/, rpc.py). Read `/AGENTS.md` first; this file adds only what is specific to `agent/`.

## Layout
- `ayna_agent/recognition/` — UIA reading, descriptors, snapshots, Spy backend (hasan)
- `ayna_agent/heal/` — healing candidates and scorer (galip)
- `ayna_agent/playback/` — keyword execution, smart waits, checkpoints, screenshots, triage (hasan)
- `ayna_agent/rpc.py` — localhost JSON-RPC server (galip)
- `ayna_cli/` — headless runner, JUnit XML (hasan)

## Commands
Python >= 3.11. Run from `agent/` inside the module's virtual environment (`.venv/` is git-ignored):
- `python -m venv .venv`, activate it (Windows: `.venv\Scripts\activate`; macOS: `source .venv/bin/activate`), then `pip install -e ".[dev]"` — install with ruff and pytest
- `ruff check .` — lint
- `ruff format --check .` — formatting check; `ruff format .` fixes it
- `pytest` — all tests; on macOS run `pytest -m "not windows"` to skip the ones that need a real Windows desktop

Before committing: `ruff check . && ruff format --check . && pytest` (the CI `agent` job runs the same on a Windows runner).

## Rules
- Runs only on Windows for real UI tests; mark them `@pytest.mark.windows`.
- Keep pywinauto behind a small interface (`ayna_agent/uia.py`) so recognition, healing and playback logic can be unit-tested on macOS with fakes; only the thin UIA layer needs Windows.
- Never hard-code coordinates; always resolve elements through repository properties.
- No fixed `sleep`; use the smart-wait helper.
- The RPC server binds to 127.0.0.1 only and requires the session token.
