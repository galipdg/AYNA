# #7 Local LLM smoke test (Turkish → JSON)

- Issue: https://github.com/galipdg/AYNA/issues/7
- Owner: galip · Branch: `galip/7-llm-smoke-test`
- Started: 2026-10-25 · Last update: 2026-10-25

## Approach
`ai/spikes/llm_smoke.py` uses only the standard library and talks to a local Ollama server (loopback only). It sends 10 Turkish sentences, with a fake object repository in the system prompt, and constrains the output with Ollama's `format` (JSON Schema). Write-up and numbers: `ai/spikes/llm-smoke.md`.

## Decisions (small, local to this task)
- 2026-10-25 — Models: `qwen3:8b` (8.2B, Q4_K_M, 5.2 GB) and `gemma4:e4b-it-qat` (7.5B, Q4_0, 6.1 GB). They are two families, both recent and Apache-2.0. `qwen3.5:9b` was skipped because the MacBook (M2, 16 GB) had only 18 GB of free disk. Bigger models wait for #71 / better hardware.
- 2026-10-25 — The spike schema lives in `ai/spikes/step-spike.schema.json`, not in `schemas/`, because `schemas/step.schema.json` does not exist yet and is a frozen shared contract.
- 2026-10-25 — No new dependencies: a small JSON Schema subset validator in the script replaces `jsonschema`.
- 2026-10-25 — Memory is measured as Ollama's `/api/ps` size plus the runner's RSS. The macOS footprint misses the mmap'd weights.
- 2026-10-25 — Ollama installed with Homebrew (0.40.11) and run as `ollama serve` (no login service).

## Status
- [x] Branch, task note, Ollama, both models pulled
- [x] Script, inputs, schema; run 2026-10-25 19:41 → qwen3 10/10, gemma4 9/10 schema-valid
- [x] `ai/spikes/llm-smoke.md` and `ai/spikes/gpu-request-draft.md`
- [x] Offline repeat: pass (same steps as online)
- [ ] Galip sends the GPU request to the advisor
- Next step: push the branch and open the PR (after the user's OK). The issue closes once the GPU request is sent.

## Manual checks
- 2026-10-25 19:58 · galip · offline repeat of both models · **pass**: ping failed (no route), qwen3 10/10, gemma4 9/10 schema-valid · evidence: `ai/spikes/results/llm-smoke-20261025-1958.json`, terminal output pasted in the session
  - **Setup**: Terminal in the repo, on branch `galip/7-llm-smoke-test`. If `curl -s 127.0.0.1:11434/api/version` prints nothing, start `OLLAMA_FLASH_ATTENTION=1 OLLAMA_KV_CACHE_TYPE=q8_0 OLLAMA_MAX_LOADED_MODELS=1 ollama serve` in a second tab.
  - **Steps**:
    1. Turn off Wi-Fi and unplug any cable.
    2. Run `ping -c 1 -t 2 1.1.1.1`.
    3. Run `python3 ai/spikes/llm_smoke.py --model qwen3:8b --model gemma4:e4b-it-qat --note "wifi off"`.
    4. Turn Wi-Fi back on.
  - **Expected**:
    1. Wi-Fi shows as off.
    2. The ping fails.
    3. 20 progress lines, then `Results: …` and two summary lines, each with `schema_valid` ≥ 8. This takes 1–5 min; gemma4 #5 may run away for about 200 s.
    4. Wi-Fi is back on.
  - **Report back**: the two summary lines and the results file name, or the error text.

## Open issues
- The user mentioned possibly using a hosted API later. That conflicts with the closed-network requirement (`memory-bank/project/brief.md`, `/AGENTS.md` §9) and `ai/AGENTS.md` ("local models only"), and would need a new ADR. A stronger local machine (department GPU) fits the rules.
- `ruff` is not installed on this Mac and `ai/` has no `pyproject.toml` yet, so the spike script is not linted. Scaffold `ai/` with ruff/pytest when real code starts (#37).
- Gemma4's runaway inside a free string (see llm-smoke.md, finding 1) is input for #37: `maxLength`, a `target` enum, a `num_predict` cap.

## Handoff
- `brew install ollama` also installed `python@3.15` and upgraded some Homebrew libraries, so `python3` on PATH is now 3.15.1 (it was 3.13.3, which is still installed).
- Free disk after the downloads: about 9.6 GB.

## Outcome (fill when the issue closes)
