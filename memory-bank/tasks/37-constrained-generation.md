# #37 Constrained JSON generation prototype

- Issue: https://github.com/galipdg/AYNA/issues/37
- Owner: galip · Branch: `galip/37-constrained-generation` (stacked on `galip/13-step-schema`, PR #134)
- Started: 2026-10-27 · Last update: 2026-10-27

## Approach
`ai/ayna_ai/generate.py` loads `schemas/step.schema.json` at runtime and, per request, derives a generation schema: one `anyOf` branch per keyword built from the step schema's `if`/`then` rules (grammar converters ignore `if`/`then`), the checkpoint split the same way by `property`, `target` as an `enum` of the caller's objects, free strings capped, `id` left out, `$ref`s inlined. It goes to Ollama `/api/chat` as `format` (`think: false`, temperature 0, seed 42, `num_predict` 512). The answer is validated against the **original** schema and the object list (`ayna_ai/validate.py`); failures are a typed `Status` (`invalid_json`, `truncated`, `invalid_schema`, `unknown_target`, `timeout`, `server_error`). Each call logs one JSON line (`event: generate`, scenario, status, latency_ms, tokens). `ayna_ai/ollama.py` is the loopback-only client. CLI: `python -m ayna_ai.generate` (see `ai/README.md`). This answers #7 findings 1 and 5.

## Decisions (small, local to this task)
- 2026-10-27 — Derive the schema generically from `if`/`then` rules and **fail loudly** (`SchemaDerivationError`) on any construct the derivation does not know, instead of hand-writing a grammar schema — a step schema change then breaks a test instead of silently loosening generation. A sampling test checks the derived schema is never wider than the step schema.
- 2026-10-27 — Generation bounds: `maxLength` 200 on free strings (`value`, `expected`; the contract allows 1000), 1–12 steps, `num_predict` 512 (~25–40 tokens per step), request timeout 120 s in the CLI. Truncation (`done_reason: length`) is its own status. All are `GenerationSettings` fields.
- 2026-10-27 — The model emits `version` too (forced `const` by the grammar), so the raw answer is already a complete step document.
- 2026-10-27 — `validate.py` holds the schema + repository check now (AGENTS layout names it); #71 builds on it. No new dependency (`jsonschema` came with #134).
- 2026-10-27 — Client ignores proxy env vars and refuses redirects, on top of the loopback check, so a request can never leave the machine.
- 2026-10-27 — Prompt is English, short, in one place (`SYSTEM_PROMPT`); it names keywords and checkpoint properties but not the JSON field layout — the grammar carries the structure. Prompt v2 (20:31) clarified `name` vs `value` after v1 (20:29) used `value` for every label check (UIA labels have no ValuePattern, so playback would fail).
- 2026-10-27 — CLI warms the model up before timing (`--no-warmup` to skip), because the server (#71) keeps the model loaded; cold load is reported as `warmup_s`.

## Live run (MacBook M2 16 GB, Ollama 0.40.11, 10 spike inputs, 17 spike objects)
Machine shared with other agents (load average ~6 during the runs), so latencies are pessimistic. Results in `ai/spikes/results/generate-20261027-*.json`, per-scenario logs in `*.log.jsonl`.

| Run | Model | Format | Parse + schema + targets | Keyword sequence | p50 / p95 latency | Output tokens (median) |
|---|---|---|---|---|---|---|
| 20:29 (prompt v1) | qwen3:8b | derived schema | 10/10 | 9/10 | 5.41 / 9.02 s | 63 |
| 20:31 | qwen3:8b | derived schema | **10/10** | 9/10 | **5.61 / 9.07 s** | 63 |
| 20:32 | gemma4:e4b-it-qat | derived schema | **10/10** | **10/10** | **6.22 / 8.68 s** | 70.5 |
| 20:34 | gemma4:e4b-it-qat | `json` (no schema) | 0/10 | — | 6.08 / 12.55 s | 66.5 |

- gemma4 #5 (the spike's 3712-token runaway) now ends in 38 tokens / 4.1 s with `timeoutMs: 5000`. Without the schema it emits `<tool_call|>` garbage again (211 tokens) and every answer invents its own field names (`action`, `step`), so the structure comes from the grammar.
- qwen3 #8 still drops the first Click (spike finding 2); gemma4 gets it right.
- Latency is above the spike's (qwen3 median 3.4 s): ~15 more output tokens per answer (`version`, checkpoint objects) plus machine load.

## Status
- [x] Branch, task note, board In progress
- [x] `generate.py`, `ollama.py`, `validate.py`; tests in `ai/tests/` (fake Ollama server, no model needed): 134 pass with #134's schema tests, ruff clean
- [x] Live run qwen3:8b + gemma4:e4b-it-qat on the 10 spike inputs: 10/10 valid each, latency logged per scenario
- [ ] Acceptance criterion 1 on the **40 pairs** — waits on #36 (`eval/nl/pairs.jsonl`), which waits on hasan's sample app #33
- Next step: when #36 lands, run `python -m ayna_ai.generate --input ../eval/nl/pairs.jsonl --objects <sample app objects>.json` for both models (convert the pairs' gold steps to `expected` keywords if the format differs) and tick criterion 1; merge after #134.

## Manual checks
- none (no UI); the live runs above are the check.

## Open issues
- Step schema v0 cannot express "the table lists Yılmaz" (spike #6): both models produce `Verify main.customerGrid name contains "Yılmaz"`, which is schema-valid but checks the grid's UIA Name, not its rows. Raise on #134 / a v0.2 issue; noted in hasan's inbox for #36 pairs and playback.
- Local env: files under this repo on galip's Mac get the macOS `hidden` flag, and Python 3.11.13+/3.15 skip hidden `.pth` files, so `pip install -e` stops working; run tests with `PYTHONPATH=.` (see `learnings.md`). CI is unaffected.
- Prompt quality (property choice, dropped steps) is measured properly in RQ3 (#77, held-out split of #57), not on these 10 sentences.
- 2026-10-27 — `ai/spikes/llm-smoke.md` cited board keys as issue numbers (#35/#56, #57, #71 for AYNA-035/056/057/071); corrected to issues #36/#57, #58, #72 on this branch.

## Handoff
- `generation_schema()` raises `SchemaDerivationError` when `schemas/step.schema.json` gains a construct it does not know: extend `_variants`/`_intersect` and the tests, never fall back to the raw schema.
- Retrieval (#58) should pass `{logical name: Turkish description}`; adding the control type to the description would likely help the `name`/`value` choice.

## Outcome (fill when the issue closes)
