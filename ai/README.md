# ai/

Python AI service that turns Turkish natural-language test descriptions into structured test steps. It runs local models only (Ollama / llama.cpp) and validates every generated step against the object repository.

Owner: galip. Build, test and AI rules: [AGENTS.md](AGENTS.md).

## Generating steps

`ayna_ai.generate` turns a Turkish instruction into a step document (`schemas/step.schema.json`) with a local Ollama model. Each request derives a JSON schema from the step schema, with `target` limited to the repository objects you pass in, and Ollama decodes only text that fits it. The answer is validated again against the step schema and the object list. Failures (invalid JSON, truncated, schema-invalid, unknown target, timeout, server error) come back as a `Status`, never as steps.

```python
from ayna_ai.generate import StepGenerator

generator = StepGenerator()  # Ollama on 127.0.0.1:11434, qwen3:8b
result = generator.generate("Giriş butonuna tıkla.", {"login.loginButton": "Giriş butonu"})
result.ok, result.document, result.latency_s
```

Batch run with one JSON log line per scenario (from `ai/`, with `ollama serve` running):

```
python -m ayna_ai.generate --input spikes/llm-smoke-inputs.jsonl \
    --objects tests/data/spike-objects.json --model qwen3:8b \
    --out spikes/results/generate-<date>-qwen3-8b.json --log <file>.log.jsonl
```

Input lines are `{"id", "text", "expected"?}` (`expected`: the keyword sequence, reported as `keyword_match`); `--objects` is a JSON object mapping logical names to Turkish descriptions. `--format json` drops the schema constraint as a baseline. The client refuses any host that is not a loopback address.
