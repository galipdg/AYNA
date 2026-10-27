# AI service HTTP API (v0)

Contract between the AYNA server and the AI service (`ai/ayna_ai/service.py`, #71). The server is the only caller: it asks for suggested steps while a user writes a test (NL chat panel, #78). The AI service saves nothing; the server shows the suggestions and saves only what the user accepts.

- Base URL: `AYNA_AI_URL` (`.env.example`: `http://localhost:8090`)
- JSON in and out, UTF-8. No authentication: the service listens on loopback only (see [Network](#network)).
- Owner: galip. Changes to this file are contract changes: tell omer (server) in his inbox.

Start it from `ai/` (Ollama running on the same machine):

```
python -m ayna_ai.service --port 8090 --model qwen3:8b --model gemma4:e4b-it-qat
```

| Option | Default | Meaning |
|---|---|---|
| `--host` | `127.0.0.1` | Listen address. A non-loopback address is refused unless `--allow-remote`. |
| `--port` | `8090` | |
| `--allow-remote` | off | Allow e.g. `0.0.0.0` (inside a container, #82). Logged as a warning at start. |
| `--model` | `qwen3:8b` | Model the service offers; repeatable. The first is the default. |
| `--model-host` | `http://127.0.0.1:11434` | Ollama URL; must be a loopback address. |
| `--timeout` | `60` | Seconds per generation, a cold model load included. |
| `--max-body-bytes` | `65536` | Larger requests get 413. |
| `--no-warmup` | warm-up on | By default the default model is loaded in the background at start. |

The service logs one JSON line per request to stderr (`event: request`, code, status, model, steps, latency_ms) and one per generation (`event: generate`, tokens, latency). **The instruction text is never logged**: it is test data and may hold passwords.

## POST /ai/generate-steps

Turns one Turkish instruction into suggested steps, each with a short Turkish reason.

Request: `Content-Type: application/json` (else 415), body at most 64 KiB, with `Content-Length` or chunked transfer encoding.

| Field | Type | Required | Meaning |
|---|---|---|---|
| `text` | string, 1–2000 chars, not blank | yes | The user's Turkish instruction. |
| `app` | string, 1–200 chars | yes | Application under test (name or id). |
| `version` | string, ≤ 100 chars | no | Application version. |
| `screen` | string, ≤ 200 chars | no | Screen the user is writing the test for. |
| `objects` | array of 1–100 `{name, description?}` | yes, until #58 | Candidate repository objects. `name`: logical name as in the step schema (`screen.element`, e.g. `login.loginButton`), unique. `description`: short Turkish text, ≤ 200 chars (e.g. the control's label: "Giriş butonu"). |
| `model` | string | no | One of the models the service offers (see health); default: the first. |

Unknown fields are rejected (400), so a typo cannot be ignored silently. `app`, `version` and `screen` are not used yet; send them anyway — retrieval (#58) will use them, and the request will not change for you.

```json
{
  "text": "Kullanıcı adı alanına admin yaz ve giriş butonuna tıkla.",
  "app": "customer-records",
  "version": "1.0",
  "screen": "login",
  "objects": [
    {"name": "login.userNameInput", "description": "Kullanıcı adı alanı"},
    {"name": "login.passwordInput", "description": "Şifre alanı"},
    {"name": "login.loginButton", "description": "Giriş butonu"}
  ]
}
```

Response **200**:

```json
{
  "status": "ok",
  "model": "qwen3:8b",
  "steps": [
    {"keyword": "Type", "target": "login.userNameInput", "value": "admin", "reason": "Kullanıcı adı alanına admin yaz"},
    {"keyword": "Click", "target": "login.loginButton", "reason": "Giriş butonuna tıkla"}
  ],
  "schemaVersion": "0.1",
  "promptVersion": "2+reason",
  "latencyMs": 6721
}
```

- Each step is a step of `schemas/step.schema.json` **plus** `reason` (1–100 chars, Turkish, for the panel). Remove `reason` before saving: `{"version": schemaVersion, "steps": [steps without reason]}` is a valid step document. Steps have no `id`; the server assigns it on save.
- **Every `target` is one of the request's `objects`** (after #58: of the retrieved objects). The service checks this twice and answers 422 rather than return a step with another target; there are tests for it (`ai/tests/test_service.py`).
- There are 1–12 steps. The model is asked to keep the order of the instruction and add nothing, but it can still miss or misread a step (qwen3 drops the first click of "Kaydet'e bastıktan sonra …"), which is why the user reviews every suggestion.
- `latencyMs`: time spent in the service, model included.

### Errors

Every error has the same shape; `details` (a list of strings, at most 20) and the generation fields appear when they apply:

```json
{
  "status": "unknown_target",
  "error": "the model's answer targets an object outside the repository",
  "details": ["$.steps[1].target: 'settings.deleteAllButton' is not in the object repository"],
  "model": "qwen3:8b",
  "schemaVersion": "0.1",
  "promptVersion": "2+reason",
  "latencyMs": 7012
}
```

| HTTP | `status` | When | What the server should do |
|---|---|---|---|
| 400 | `bad_request` | Body is not a JSON object, a field is missing or invalid, duplicate object names, a model the service does not offer, no `objects` | Fix the request (a bug on our side); `details` names the field. |
| 404 | `not_found` | Unknown path | — |
| 405 | `method_not_allowed` | Wrong method; `Allow` header says which | — |
| 411 | `length_required` | Neither `Content-Length` nor chunked | — |
| 413 | `too_large` | Body over the limit (64 KiB) | Send fewer objects. |
| 415 | `unsupported_media_type` | `Content-Type` is not `application/json` | — |
| 422 | `invalid_json`, `truncated`, `invalid_schema`, `unknown_target` | The model's answer failed validation; no steps are returned | Tell the user no suggestion could be made and ask them to rephrase. **Do not retry the same request**: generation is deterministic (temperature 0, fixed seed), so it gives the same answer. |
| 422 | `no_objects` | Retrieval found no candidate objects (after #58) | Tell the user the repository has no objects for this screen. |
| 500 | `internal_error` | A bug in the service | Show a generic error; report it with the service log. |
| 503 | `server_error` | The model server is down or does not have the model (`details` has its message) | Disable the panel as for health `ready: false`. |
| 504 | `timeout` | No answer within the service timeout (60 s) | Offer a retry; the machine may be busy. |

## GET /ai/health

Says whether generation can work right now. It never runs the model and asks Ollama with a 2 s timeout, so it answers within about 2 s.

```json
{
  "status": "ok",
  "ready": true,
  "modelServer": {"url": "http://127.0.0.1:11434", "reachable": true},
  "defaultModel": "qwen3:8b",
  "models": [
    {"name": "qwen3:8b", "available": true},
    {"name": "gemma4:e4b-it-qat", "available": true}
  ],
  "schemaVersion": "0.1",
  "promptVersion": "2+reason",
  "serviceVersion": "0.0.0"
}
```

- HTTP 200 whenever the service process answers; `ready` carries the answer.
- `status`: `ok` (ready) · `model_server_down` (Ollama does not answer; `error` holds the reason) · `model_missing` (Ollama answers but the default model is not pulled).
- `models[].available`: pulled on the model server, so a request may name it.
- For #78: disable the panel with a clear message when the health call fails (connection refused or no answer within a few seconds: the AI service is not running) or `ready` is false; `status` tells which message to show. A later 503 from generate-steps means the same.

## Timeouts and latency

- The service gives a generation 60 s. Use a read timeout of at least 65 s on the server's HTTP client, and do not retry on your own timeout (the model would run twice).
- Measured on a MacBook M2 16 GB under load from other work (load average ~4.5), qwen3:8b, the 10 spike sentences twice: p50 12.6 s, p95 25.3 s, all 20 answers valid (`memory-bank/tasks/71-nl-service.md`). Reasons add about 75% output tokens. Team-hardware and GPU numbers will be added there.
- Ollama unloads an idle model after 5 minutes by default; the next request then pays a cold load (~6 s here). Start Ollama with `OLLAMA_KEEP_ALIVE=30m` (or longer) on the machine that serves it.
- Requests are handled in parallel, but Ollama runs one generation at a time by default, so concurrent requests queue and each one waits longer.

## Versions

- `schemaVersion`: version of the step schema the steps follow (`schemas/step.schema.json`, now `0.1`).
- `promptVersion`: changes whenever the prompt changes. Store it with accepted suggestions if you want to trace which prompt produced them (RQ3).
- `serviceVersion`: the `ayna-ai` package version.

## Network

- Closed network: the service makes no call except to the Ollama server, which must be on a loopback address; the Ollama client ignores proxy settings and refuses redirects.
- It listens on `127.0.0.1` by default and refuses a non-loopback `--host` unless started with `--allow-remote` (logged). In a container (#82) use `--host 0.0.0.0 --allow-remote` and publish the port only on the internal network, never on the test machines.

## Until retrieval exists (#58)

The service has no repository access yet: it takes the candidate objects from the request. Send the objects of the current application and screen from the repository (at most 100, logical name + Turkish description). When #58 adds vector + graph retrieval, the service will choose the candidates itself from `app`/`version`/`screen` and `objects` becomes optional; this file will say how the two combine.
