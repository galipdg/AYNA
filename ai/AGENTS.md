# ai/ — AI service: Turkish NL → steps, retrieval

Owner: galip. Read `/AGENTS.md` first; this file adds only what is specific to `ai/`.

## Layout
- `ayna_ai/service.py` — HTTP service for the server: `POST /ai/generate-steps`, `GET /ai/health`; contract in `API.md`
- `ayna_ai/ollama.py` — loopback-only client for the local model server
- `ayna_ai/generate.py` — constrained JSON generation
- `ayna_ai/retrieve.py` — candidate objects of a request; the server chooses them and the service never reads the graph (#58)
- `ayna_ai/validate.py` — checks each generated step; drops unknown keywords, unknown objects and the no-match target

## Commands
Python >= 3.11. Run from `ai/` inside the module's virtual environment (`.venv/` is git-ignored):
- `python3 -m venv .venv`, activate it (`source .venv/bin/activate`; Windows: `.venv\Scripts\activate`), then `pip install -e ".[dev]"` — install with ruff and pytest
- `ruff check .` — lint (`spikes/` is excluded: throwaway scripts)
- `ruff format --check .` — formatting check; `ruff format .` fixes it
- `pytest` — tests in `tests/`
- Local model server for experiments: see `spikes/llm-smoke.md` (Ollama on 127.0.0.1 only)

Before committing: `ruff check . && ruff format --check . && pytest` (the CI `ai` job runs the same on Ubuntu).

## Rules
- Local models only (Ollama / llama.cpp); no external API calls.
- Never tune prompts on `eval/nl/heldout.jsonl`.
- Model weights are not committed.
