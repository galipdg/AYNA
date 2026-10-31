# ai/

Python AI service that turns Turkish natural-language test descriptions into structured test steps. It runs local models only (Ollama / llama.cpp) and validates every generated step against the object repository.

Owner: galip. Build, test and AI rules: [AGENTS.md](AGENTS.md).

## HTTP service

`ayna_ai.service` serves `POST /ai/generate-steps` (Turkish instruction + candidate objects → suggested steps, each with a short Turkish `reason`, and the dropped steps with why) and `GET /ai/health` to the AYNA server. The contract — request and response, status codes, health, timeouts — is in **[API.md](API.md)**.

From `ai/`, with `ollama serve` running:

```
python -m ayna_ai.service --port 8090 --model qwen3:8b
python spikes/service_check.py   # the 10 spike sentences through HTTP, with p50/p95
```

It listens on loopback only unless started with `--allow-remote`. Candidate objects come from the request through a `Retriever` (`ayna_ai/retrieve.py`); repository retrieval (#58) will replace the pass-through one.

## Generating steps

`ayna_ai.generate` turns a Turkish instruction into a step document (`schemas/step.schema.json`) with a local Ollama model. Each request derives a JSON schema from the step schema, with `target` limited to the repository objects you pass in, and Ollama decodes only text that fits it. The answer is validated again against the step schema and the object list, one step at a time: a step with an unknown keyword, an unknown target, the reserved target `none.noMatch` (the model's "no object fits") or any other schema error is dropped with its reason (`result.dropped`), and the valid ones are kept (`result.document`). Failures of the whole answer (invalid JSON, truncated, not a step document, no valid step left, timeout, server error) come back as a `Status`. With `GenerationSettings(reasons=True)` (what the service uses) every step also gets a short Turkish reason in the same constrained call; it is removed before validation and returned in `result.reasons`.

```python
from ayna_ai.generate import StepGenerator

generator = StepGenerator()  # Ollama on 127.0.0.1:11434, qwen3:8b
result = generator.generate(
    "Giriş butonuna tıkla.", {"login.loginButton": "Giriş butonu"}
)
result.ok, result.document, result.latency_s
```

Batch run with one JSON log line per scenario (from `ai/`, with `ollama serve` running):

```
python -m ayna_ai.generate --input spikes/llm-smoke-inputs.jsonl \
    --objects tests/data/spike-objects.json --model qwen3:8b \
    --out spikes/results/generate-<date>-qwen3-8b.json --log <file>.log.jsonl
```

Input lines are `{"id", "text", "expected"?}` (`expected`: the keyword sequence, reported as `keyword_match`); `--objects` is a JSON object mapping logical names to Turkish descriptions. `--format json` drops the schema constraint as a baseline. The client refuses any host that is not a loopback address.
