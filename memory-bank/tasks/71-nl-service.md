# #71 NL → steps service end to end

- Issue: https://github.com/galipdg/AYNA/issues/71
- Owner: galip · Branch: `galip/71-nl-service` (stacked on `galip/37-constrained-generation` PR #142 → `galip/13-step-schema` PR #134)
- Started: 2026-10-27 · Last update: 2026-10-27

## Approach
`ai/ayna_ai/service.py`: stdlib HTTP server (`ThreadingHTTPServer`) with `POST /ai/generate-steps` and `GET /ai/health`; contract in `ai/API.md`. Flow: request validated with a JSON schema (object names use the step schema's `logicalName`; `none.noMatch` refused) → `Retriever` (`ai/ayna_ai/retrieve.py`; `PassThroughRetriever` uses the request's `objects` until #58) → `StepGenerator` from #37 with `reasons=True` → per-step check (envelope, then each step against `steps.items` = `#/$defs/step` and the retrieved set) → guard: the service re-checks every kept step → `steps` with `reason` + `dropped`. Generator failures map to 422 (bad answer / no valid step), 503 (model server down / model missing), 504 (timeout, 30 s per request). Health asks Ollama `/api/tags` with a 2 s timeout and reports `ready` + `status` so #78 can disable the panel. CLI: `python -m ayna_ai.service`.

## Decisions (small, local to this task)
- 2026-10-27 — **stdlib `http.server`, no framework.** Two endpoints, JSON only, one caller (the server); `jsonschema` (already a dependency) validates requests. No new dependency keeps offline packaging (#82) trivial. Costs we accepted: chunked request bodies decoded by hand (~20 lines, Spring's RestClient on the JDK HttpClient may stream JSON chunked), HTTP/1.0 responses (one connection per request; negligible next to seconds of generation). Revisit only if we need streaming responses or many endpoints.
- 2026-10-27 — **Reasons in the same constrained call**: `generation_schema(..., reason_max_length=100)` adds a required `reason` string (1–100 chars) to every step branch; `take_reason()` removes it from each step before validating against the original step schema, so `schemas/` is unchanged. A step schema that gains its own `reason` field raises `SchemaDerivationError`. A missing/blank/too-long reason drops that step as `invalid_step` (revision below; only possible if the server ignores the grammar). Prompt: one added paragraph (`REASON_PROMPT`, English instruction, Turkish answer, "at most 10 words, quoting the instruction"). `reason` sits after the required step fields, so it explains rather than steers the step (keeps #37's accuracy comparable).
- 2026-10-27 — `PROMPT_VERSION = "2"` (#37's v2 text, unchanged); with reasons the service reports `"2+reason"`. The batch CLI now writes `prompt_version` into results.
- 2026-10-27 — Response steps are step-schema steps **plus** `reason` (as the orchestrator specified for #78), with top-level `schemaVersion` so `{version, steps minus reason}` is a valid document.
- 2026-10-27 — Request limits: text ≤ 2000 chars, ≤ 100 objects (prompt must stay well inside `num_ctx` 4096 — ~8–20 tokens per object; Ollama would silently cut the start of an over-long prompt, i.e. the system prompt), description ≤ 200, body ≤ 64 KiB (413). Unknown fields → 400 (typos must not be ignored). Duplicate object names → 400. `Content-Type` must be `application/json` (415): also makes a browser on the machine unable to POST without a CORS preflight, which the service does not answer.
- 2026-10-27 — `model` in the request must be one the service was started with (`--model`, repeatable): a caller cannot make Ollama load an arbitrary model.
- 2026-10-27 — `num_predict` 768 in the service (512 in the CLI): reasons add ~15–25 tokens per step. Health timeout 2 s. (Generation timeout was 60 s; now 30 s per request, revision below.)
- 2026-10-27 — Health answers HTTP 200 whenever the process is up; `ready`/`status` (`ok`, `model_server_down`, `model_missing`) carry the state. Simpler for the server than parsing 503 bodies; a dead process is a connection error anyway.
- 2026-10-27 — Bind: loopback only by default; non-loopback needs `--allow-remote` and logs a `remote_bind` warning (for #82's container). IPv6 loopback (`::1`) supported.
- 2026-10-27 — Logs are JSON lines; the instruction text is never logged (test data may hold passwords) — tested.
- 2026-10-27 — Warm-up of the default model runs in a background thread at start, so the service answers health at once even if Ollama is down.

### Revision 2026-10-27: drop list, no-match target, 30 s timeout (FR-25–FR-27, SC-27; SDD AI-2/AI-3)
- **Per-step validation** (FR-26). `StepValidator` splits the step schema into an *envelope* (root with `steps.items` removed) and the *step* schema (`steps.items` with the root `$defs`, i.e. `#/$defs/step`); together they accept exactly what the whole schema accepts, and the generator re-validates the kept document against the whole schema anyway. Envelope errors (no/wrong `version`, `steps` not a list, extra root field, not an object) still fail the whole answer as `invalid_schema`; invalid_json, truncated, timeout and server_error are unchanged.
- **Drop entry** = `{index, code, reason, step}`. `index`: position in the model's answer, so the panel can interleave (kept steps fill the other positions in order — no index on kept steps needed). `step`: raw, as the model wrote it, its own `reason` included (helps the user see which clause failed). `code` ∈ `unknown_keyword`, `unknown_target`, `no_match`, `invalid_step` (first that applies; `reason` joins all problems with `; `, e.g. DoubleClick on an unknown object → `unknown_keyword` with both texts). Machine `code` + English `reason`; the client shows Turkish text per code (suggestions in `ai/API.md`) — keeps UI language in the client. An invalid logical name as target counts as `unknown_target`, not `invalid_step`: for the user it is the same thing. jsonschema reports a `false`-subschema field (Click with `value`) at the step without the field's name; `_describe()` finds the field by identity of `error.instance` → "$.value: not allowed for this keyword".
- **Nothing survives → HTTP 422, `status: "no_valid_steps"`**, body with `steps: []`, `dropped` and `details` (one line per dropped step). Why 422 and not 200: the existing contract already uses 422 for "the model answered but there is nothing usable; tell the user and ask to rephrase", and SC-27's panel text is exactly that; 200 now always means "at least one step to review", so the server maps codes to panel states without inspecting `steps`. `Status.UNKNOWN_TARGET` removed (a whole-answer status no longer exists), `Status.NO_VALID_STEPS` added; an answer with zero steps (only without the grammar) is also `no_valid_steps`.
- **Guard** stays: the service re-runs `step_problems` on every kept step against the retrieved objects and moves any failure to `dropped` (log `target_guard` with index:code only — a reason may quote a step value). Invariant tested by the property test (150 seeded random answers, now with DoubleClick/Wait keywords and `none.noMatch`): every step is either in `steps` (valid keyword, retrieved target) or in `dropped` with the expected code, order kept.
- **Reserved target `none.noMatch`** (`validate.NO_MATCH`). Always appended to the generation `target` enum; derivation raises `SchemaDerivationError` if the step schema stops accepting it, `ValueError` if a caller passes it as an object; the service answers 400 for a request object with that name (omer asked via inbox to refuse it in the repository too). Keywords get no escape value (SDD AI-3 limit 3).
- **Prompt v3** (`PROMPT_VERSION = "3"`, service reports `3+reason`). Tried four wordings on the 10 spike sentences + the SC-27 sentence (dev data only, never `heldout.jsonl`), qwen3:8b, reasons on: a separate line after the object list — A "If no object in the list fits an action, use the target none.noMatch for that step.", B "Use the target none.noMatch only when no object in the list fits.", C "When no listed object fits, the target is none.noMatch." — A and B made qwen3 add spurious Clicks before Types (A on #9, B on #1; 8/10 keyword match each, v2 had 9/10), C was worse (≤ 8/10). All four sent the SC-27 sentence to `none.noMatch` in those runs. D, folding it into the existing target line ("target must be one of these objects (…), or none.noMatch if none of them fits:"), kept 9/10 (the same #8 miss as v2). Chose D: the change is one prompt line, as asked, but an edited line rather than an added one.
- **Service timeout 30 s per request** (`ServiceConfig.timeout_s`, `--timeout`), was 60 s per generation. A deadline starts when the request is parsed; the model call gets the remaining time as its socket timeout (`OllamaClient.chat(body, timeout_s=)`, `StepGenerator.generate(..., timeout_s=)`); if retrieval used it up the model is not called. 504 `timeout`, `details: ["no answer within 30 s"]`. Retrieval itself is not interrupted (synchronous); #58 should keep it well under the budget (NFR-11: 200 ms). Server read timeout ≥ 35 s (API.md).

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

### Live check after the revision (same Mac, qwen3:8b, prompt 3+reason, 30 s timeout, 2026-10-27 22:22–22:27)
Load average 3.9–5.2 (other agents on the machine). `spikes/service_check.py --port 8097`: results `ai/spikes/results/service-20261027-2222-qwen3-8b.json`, service log `service-20261027-2222-qwen3-8b.log.jsonl` (no instruction text in it — checked).
- 9/10 HTTP 200, 0 steps dropped, keyword sequence 8/10: #8 the known miss; **#9 got 504 at 30.0 s** (4 steps, the longest answer; 27–36 s in the prompt-variant runs at this load). The timeout works end to end and is tight on this busy machine; idle p95 was 9 s (#37). Client p50 / p95 / max: 12.98 / 25.17 / 30.0 s.
- **SC-27 live is borderline**: "Şifremi unuttum bağlantısına çift tıkla" went to `none.noMatch` (→ 422 `no_valid_steps`, dropped `no_match`) in the four prompt-variant runs, but to `Click login.passwordInput` (200, valid and wrong — the forced-choice case) in four later runs with the identical final prompt (2 over HTTP, 2 direct). Same prompt and seed, different answers: Ollama's output at temperature 0 is not fully deterministic across machine load / prompt-cache state when the decision is close. The stub-model test is what FR-26 requires (T — stub-model test) and passes; how often the model uses the escape is measured in #77 (SDD AI-9).

## Status
- [x] Branch, task note, board In progress
- [x] `service.py`, `retrieve.py`, reasons in `generate.py`, `OllamaClient.models()`; tests with the fake Ollama (target guard table + 150 seeded random answers, every error code, bind refusal, log privacy)
- [x] `ai/API.md` contract for omer; README section
- [x] Live check on this Mac (above)
- [x] PR https://github.com/galipdg/AYNA/pull/146 opened 2026-10-27 (`Refs #71`, stacked on #142 → #134, merge after them), reviewers omer (contract) and hasan (FYI); omer's inbox points to `ai/API.md`
- [x] Revision 2026-10-27 (above): per-step drop list, `none.noMatch`, prompt v3, 30 s request timeout; SC-27 stub-model test, mixed answer, no-match and timeout tests (254 tests); API.md, README, `ai/AGENTS.md` layout and the architecture contracts row (both approved by galip); omer told via inbox; live check after the revision
- [ ] Acceptance "works with the network disabled" — manual check below, **pending (galip)**
- [x] Acceptance "never returns a step that targets an object missing from the repository (tests)" — for the pass-through retriever; holds for #58's retriever by construction (guard uses whatever the retriever returns), re-check when #58 lands. Since the revision such steps are listed in `dropped`, never in `steps` (property test).
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
  - **Expected** — 1: ping fails. 2: `"ready": true, "status": "ok"`. 3: `"http_200": 10` in the summary (on a busy machine #9 may get a 504 at 30 s — then rerun with `--timeout 60` and note it), every step has a `reason`, no error lines in the service console. 4: `"ready": false, "status": "model_server_down"`, answered within ~2 s. 5: `"ready": true` again.
  - **Report back** — pass/fail per step; on failure the service console lines (stderr) and `ollama serve` log, macOS version, Ollama version (`ollama -v`).

## Open issues
- Reason cost: ~+75% output tokens. If #78 feels slow, levers in order: shorter reason (prompt "at most 6 words", cap 60), gemma4 (faster per #37), GPU (#131). Measure on the #36 pairs before choosing.
- **30 s timeout is tight on a loaded laptop**: #9 hit it live (load ~5). Keep 30 s (FR-27 panel should not hang; SDD AI-2) but measure on team hardware; if the idle p95 is > ~15 s there, raise the default or shorten reasons first.
- **SC-27 live depends on the model**: qwen3:8b used `none.noMatch` for "Şifremi unuttum bağlantısına çift tıkla" in some runs and `login.passwordInput` in others (identical prompt). #77 should count how often no-match is used and how often it is used wrongly (on sentences whose objects exist); #72 can compare models on it.
- Determinism caveat: identical requests gave different answers across machine load / Ollama cache state (above). API.md now says "nearly always the same"; RQ3 runs should record load and be run on an otherwise idle machine.
- #82 (offline image): Ollama must be in the same container/host (loopback-only client); the service then needs `--host 0.0.0.0 --allow-remote`; set `OLLAMA_KEEP_ALIVE` so the first request after 5 idle minutes does not pay a cold load (~6 s here).
- Concurrency: Ollama runs one generation at a time by default; parallel requests queue. Fine for one server; revisit if several users write tests at once (OLLAMA_NUM_PARALLEL, a queue with 429).

## Handoff
- #58: implement `Retriever.retrieve(query) -> {name: description}` in `retrieve.py` and pass it to `StepService(retriever=...)`. The guard limits targets to exactly what the retriever returns, so it must return only objects that exist. Then decide how request `objects` and retrieval combine and update `ai/API.md` (and tell omer).
- #58: the retriever must never return an object named `none.noMatch` (generation raises ValueError → 500); the server should refuse that name (omer's inbox).
- Status/HTTP mapping lives in `service.FAILURES`; a new generator `Status` must be added there or the service answers 500.
- Per-step checks: `StepValidator.envelope_errors` / `step_problems` (`validate.py`), loop in `StepGenerator._check`, re-check in `StepService._guard`. Drop codes: `validate.DropCode`.
- Tests: `ai/tests/test_service.py` (HTTP, fake Ollama; SC-27, drop list, property test, timeouts), per-step and reason tests in `test_generate.py` / `test_generation_schema.py`.

## Outcome (fill when the issue closes)
