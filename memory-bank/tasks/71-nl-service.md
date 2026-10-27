# #71 NL → steps service end to end

- Issue: https://github.com/galipdg/AYNA/issues/71
- Owner: galip · Branch: `galip/71-nl-service` (stacked on `galip/37-constrained-generation` PR #142 → `galip/13-step-schema` PR #134)
- Started: 2026-10-27 · Last update: 2026-10-27

## Approach
`ai/ayna_ai/service.py`: stdlib HTTP server (`ThreadingHTTPServer`) with `POST /ai/generate-steps` and `GET /ai/health`; contract in `ai/API.md`. Flow: request validated with a JSON schema (object names use the step schema's `logicalName`) → `Retriever` (`ai/ayna_ai/retrieve.py`; `PassThroughRetriever` uses the request's `objects` until #58) → `StepGenerator` from #37 with `reasons=True` → guard: every target must be in the retrieved set, checked by the generator and again by the service → steps with `reason`. Generator failures map to 422 (bad answer), 503 (model server down / model missing), 504 (timeout). Health asks Ollama `/api/tags` with a 2 s timeout and reports `ready` + `status` so #78 can disable the panel. CLI: `python -m ayna_ai.service`.

## Decisions (small, local to this task)
- 2026-10-27 — **stdlib `http.server`, no framework.** Two endpoints, JSON only, one caller (the server); `jsonschema` (already a dependency) validates requests. No new dependency keeps offline packaging (#82) trivial. Costs we accepted: chunked request bodies decoded by hand (~20 lines, Spring's RestClient on the JDK HttpClient may stream JSON chunked), HTTP/1.0 responses (one connection per request; negligible next to seconds of generation). Revisit only if we need streaming responses or many endpoints.
- 2026-10-27 — **Reasons in the same constrained call**: `generation_schema(..., reason_max_length=100)` adds a required `reason` string (1–100 chars) to every step branch; `split_reasons()` removes it before validating against the original step schema, so `schemas/` is unchanged. A step schema that gains its own `reason` field raises `SchemaDerivationError`. A missing/blank/too-long reason is `invalid_schema` (only possible if the server ignores the grammar). Prompt: one added paragraph (`REASON_PROMPT`, English instruction, Turkish answer, "at most 10 words, quoting the instruction"). `reason` sits after the required step fields, so it explains rather than steers the step (keeps #37's accuracy comparable).
- 2026-10-27 — `PROMPT_VERSION = "2"` (#37's v2 text, unchanged); with reasons the service reports `"2+reason"`. The batch CLI now writes `prompt_version` into results.
- 2026-10-27 — Response steps are step-schema steps **plus** `reason` (as the orchestrator specified for #78), with top-level `schemaVersion` so `{version, steps minus reason}` is a valid document.
- 2026-10-27 — Request limits: text ≤ 2000 chars, ≤ 100 objects (prompt must stay well inside `num_ctx` 4096 — ~8–20 tokens per object; Ollama would silently cut the start of an over-long prompt, i.e. the system prompt), description ≤ 200, body ≤ 64 KiB (413). Unknown fields → 400 (typos must not be ignored). Duplicate object names → 400. `Content-Type` must be `application/json` (415): also makes a browser on the machine unable to POST without a CORS preflight, which the service does not answer.
- 2026-10-27 — `model` in the request must be one the service was started with (`--model`, repeatable): a caller cannot make Ollama load an arbitrary model.
- 2026-10-27 — `num_predict` 768 in the service (512 in the CLI): reasons add ~15–25 tokens per step. Generation timeout 60 s (cold load included); health timeout 2 s.
- 2026-10-27 — Health answers HTTP 200 whenever the process is up; `ready`/`status` (`ok`, `model_server_down`, `model_missing`) carry the state. Simpler for the server than parsing 503 bodies; a dead process is a connection error anyway.
- 2026-10-27 — Bind: loopback only by default; non-loopback needs `--allow-remote` and logs a `remote_bind` warning (for #82's container). IPv6 loopback (`::1`) supported.
- 2026-10-27 — Logs are JSON lines; the instruction text is never logged (test data may hold passwords) — tested.
- 2026-10-27 — Warm-up of the default model runs in a background thread at start, so the service answers health at once even if Ollama is down.

## Live check (MacBook M2 16 GB, Ollama 0.40.11, qwen3:8b, 2026-10-27 21:36–21:43)
Service on 127.0.0.1:8090, `ai/spikes/service_check.py` sends the 10 spike sentences with the 17 spike objects over HTTP; run twice. Machine shared with other agents: load average 4.0–5.0 throughout; Ollama's request log shows no other client during the runs and `load_ms` ≈ 1 ms on every request (no model swap). Results: `ai/spikes/results/service-20261027-2136-qwen3-8b.json`, `service-20261027-2141-qwen3-8b.json`, service log `service-20261027-2136-qwen3-8b.log.jsonl`; same-load baseline without reasons `generate-20261027-2139-qwen3-8b.json`.

| Run | Valid (HTTP 200) | Keyword sequence | p50 / p95 / max (client) | Output tokens (median) |
|---|---|---|---|---|
| service, reasons, run 1 | 10/10 | 9/10 | 12.57 / 21.82 / 25.61 s | ~110 |
| service, reasons, run 2 | 10/10 | 9/10 | 12.83 / 24.45 / 25.28 s | ~110 |
| **both runs (n = 20)** | **20/20** | 18/20 | **12.57 / 25.29 / 25.61 s** | — |
| CLI, no reasons, same load | 10/10 | 9/10 | 8.81 / 21.37 / 23.48 s | 63 |

- Deterministic: both runs gave identical steps and reasons.
- Reasons cost ~+75% output tokens (median 63 → ~110), ~+40% p50 at this load. Reason length: median 31 chars, max 73 (cap 100). Most quote the clause ("Şifre alanına 1234 yaz"); #6 gave the same clause as reason for both Type and Click.
- Throughput was ~9 tok/s, vs ~20 at #37's 20:31 run: the machine was far busier. These are pessimistic numbers, not team-hardware numbers.
- Same misses as #37: #8 drops the first Click; #6 checks the grid's Name (step schema v0 limit).
- Service overhead (client time − `latencyMs`): 0–3 ms.

## Status
- [x] Branch, task note, board In progress
- [x] `service.py`, `retrieve.py`, reasons in `generate.py`, `OllamaClient.models()`; tests with the fake Ollama (target guard table + 150 seeded random answers, every error code, bind refusal, log privacy)
- [x] `ai/API.md` contract for omer; README section
- [x] Live check on this Mac (above)
- [ ] Acceptance "works with the network disabled" — manual check below, **pending (galip)**
- [x] Acceptance "never returns a step that targets an object missing from the repository (tests)" — for the pass-through retriever; holds for #58's retriever by construction (guard uses whatever the retriever returns), re-check when #58 lands
- [ ] Acceptance "p95 latency on team hardware recorded" — recorded on galip's M2 under load (25.3 s); rerun on an idle machine / GPU machine (#131) for the report
- [ ] Retrieval (#58) replaces `PassThroughRetriever` — then the issue can close
- Next step: galip runs the offline manual check below and records it here; then rerun `spikes/service_check.py` on an idle machine for the p95.

## Manual checks
- 2026-10-27 · galip · network disabled · **pending**
  - **Setup** — on galip's Mac, in `ai/`: `ollama serve` (if not running) and `ollama list` shows `qwen3:8b`. Start the service: `PYTHONPATH=. python -m ayna_ai.service --port 8090 --model qwen3:8b`. Wait for the `"event": "warmup"` line.
  - **Steps**
    1. Turn Wi-Fi off and unplug any network cable (menu bar → Wi-Fi off). Check: `ping -c 1 -t 2 1.1.1.1` fails.
    2. `curl -s http://127.0.0.1:8090/ai/health`
    3. `PYTHONPATH=. python spikes/service_check.py --out spikes/results/service-<date>-offline-qwen3-8b.json`
    4. Stop Ollama (`pkill -f "ollama serve"` or quit the app), then repeat step 2.
    5. Restart Ollama, wait ~5 s, repeat step 2; turn Wi-Fi back on.
  - **Expected** — 1: ping fails. 2: `"ready": true, "status": "ok"`. 3: `"http_200": 10` in the summary, every step has a `reason`, no error lines in the service console. 4: `"ready": false, "status": "model_server_down"`, answered within ~2 s. 5: `"ready": true` again.
  - **Report back** — pass/fail per step; on failure the service console lines (stderr) and `ollama serve` log, macOS version, Ollama version (`ollama -v`).

## Open issues
- Reason cost: ~+75% output tokens. If #78 feels slow, levers in order: shorter reason (prompt "at most 6 words", cap 60), gemma4 (faster per #37), GPU (#131). Measure on the #36 pairs before choosing.
- `ai/AGENTS.md` layout lists `generate.py`, `retrieve.py`, `validate.py` but not `service.py`; needs the user's OK to edit (AGENTS.md §7).
- `memory-bank/project/architecture.md` contracts table could list "AI service HTTP API | `ai/API.md` | server ↔ AI service" — project memory, needs the user's OK.
- #82 (offline image): Ollama must be in the same container/host (loopback-only client); the service then needs `--host 0.0.0.0 --allow-remote`; set `OLLAMA_KEEP_ALIVE` so the first request after 5 idle minutes does not pay a cold load (~6 s here).
- Concurrency: Ollama runs one generation at a time by default; parallel requests queue. Fine for one server; revisit if several users write tests at once (OLLAMA_NUM_PARALLEL, a queue with 429).

## Handoff
- #58: implement `Retriever.retrieve(query) -> {name: description}` in `retrieve.py` and pass it to `StepService(retriever=...)`. The guard limits targets to exactly what the retriever returns, so it must return only objects that exist. Then decide how request `objects` and retrieval combine and update `ai/API.md` (and tell omer).
- Status/HTTP mapping lives in `service.FAILURES`; a new generator `Status` must be added there or the service answers 500.
- Tests: `ai/tests/test_service.py` (HTTP, fake Ollama), reason tests in `test_generate.py` / `test_generation_schema.py`.

## Outcome (fill when the issue closes)
