# ai/ — AI service: Turkish NL → steps, retrieval

Owner: galip. Read `/AGENTS.md` first; this file adds only what is specific to `ai/`.

## Layout
- `ayna_ai/generate.py` — constrained JSON generation
- `ayna_ai/retrieve.py` — graph + vector retrieval of repository objects
- `ayna_ai/validate.py` — rejects steps that target unknown objects

## Commands
To be filled in when the module is scaffolded (build, test, lint, run). Until then, ask before inventing tooling.

## Rules
- Local models only (Ollama / llama.cpp); no external API calls.
- Never tune prompts on `eval/nl/heldout.jsonl`.
- Model weights are not committed.
