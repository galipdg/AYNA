# AI service HTTP API (v0)

Contract between the AYNA server and the AI service (`ai/ayna_ai/service.py`, #71). The server is the only caller: it asks for suggested steps while a user writes a test (NL chat panel, #78). The AI service saves nothing; the server shows the suggestions and saves only what the user accepts.

- Base URL: `AYNA_AI_URL` (`.env.example`: `http://localhost:8090`)
- JSON in and out, UTF-8. On loopback without a token there is no authentication; with `AYNA_AI_TOKEN` set (required for `--allow-remote`) every request needs `Authorization: Bearer <token>` (see [Network](#network)).
- Owner: galip. Changes to this file are contract changes: tell omer (server) in his inbox.

Start it from `ai/` (Ollama running on the same machine):

```
python -m ayna_ai.service --port 8090 --model qwen3:8b --model gemma4:e4b-it-qat
```

| Option | Default | Meaning |
|---|---|---|
| `--host` | `127.0.0.1` | Listen address. A non-loopback address is refused unless `--allow-remote`. |
| `--port` | `8090` | |
| `--allow-remote` | off | Allow e.g. `0.0.0.0` (inside a container, #82). Needs `AYNA_AI_TOKEN`. Logged as a warning at start. |
| `--model` | `qwen3:8b` | Model the service offers; repeatable. The first is the default. |
| `--model-host` | `http://127.0.0.1:11434` | Ollama URL; must be a loopback address. |
| `--timeout` | `30` | Seconds per request — retrieval and the model call, a cold model load included. Past it the service answers 504 (see [Timeouts](#timeouts-and-latency)). |
| `--max-body-bytes` | `65536` | Larger requests get 413. |
| `--no-warmup` | warm-up on | By default the default model is loaded in the background at start. |
| `AYNA_AI_TOKEN` (environment) | unset | Bearer token, at least 16 characters. When set, every request must carry it, on loopback too; without it the service refuses `--allow-remote` at start. An environment variable, never a command-line option, so it does not show in the process list. |

The service logs one JSON line per request to stderr (`event: request`, code, status, model, steps, dropped, latency_ms) and one per generation (`event: generate`, tokens, latency). **The instruction text is never logged**: it is test data and may hold passwords.

## POST /ai/generate-steps

Turns one Turkish instruction into suggested steps, each with a short Turkish reason.

Request: `Content-Type: application/json` (else 415), body at most 64 KiB, with `Content-Length` or chunked transfer encoding.

| Field | Type | Required | Meaning |
|---|---|---|---|
| `text` | string, 1–2000 chars, not blank | yes | The user's Turkish instruction. |
| `app` | string, 1–200 chars | yes | The application's id (the server's UUID). |
| `version` | string, ≤ 100 chars | no | The application version's id. |
| `screen` | string, ≤ 200 chars | no | The screen prefix of the logical names the user is writing the test for (`login` for `login.*`). |
| `objects` | array of 1–100 `{name, description?}` | yes | Candidate repository objects, chosen by the server (see [Candidate objects](#candidate-objects-and-retrieval-58)). `name`: logical name as in the step schema (`screen.element`, e.g. `login.loginButton`), unique, not `none.noMatch` (reserved, see below). `description`: short Turkish text, ≤ 200 chars (e.g. the control's label: "Giriş butonu"). |
| `model` | string | no | One of the models the service offers (see health); default: the first. |

Unknown fields are rejected (400), so a typo cannot be ignored silently. `app`, `version` and `screen` say which application, version and screen the candidates belong to. The service queries nothing with them; they describe the request, and the generation does not depend on them.

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

Response **200** — at least one suggested step; here the model wrote three and one was dropped:

```json
{
  "status": "ok",
  "model": "qwen3:8b",
  "steps": [
    {"keyword": "Type", "target": "login.userNameInput", "value": "admin", "reason": "Kullanıcı adı alanına admin yaz"},
    {"keyword": "Click", "target": "login.loginButton", "reason": "Giriş butonuna tıkla"}
  ],
  "dropped": [
    {"index": 1, "code": "no_match", "reason": "no repository object matches",
     "step": {"keyword": "Click", "target": "none.noMatch", "reason": "Beni hatırla kutusunu işaretle"}}
  ],
  "schemaVersion": "0.1",
  "promptVersion": "3+reason",
  "latencyMs": 6721
}
```

- `steps`: the suggested steps, in the instruction's order. Each is a step of `schemas/step.schema.json` **plus** `reason` (1–100 chars, Turkish, for the panel). Remove `reason` before saving: `{"version": schemaVersion, "steps": [steps without reason]}` is a valid step document. Steps have no `id`; the server assigns it on save.
- **Every `target` in `steps` is one of the request's `objects`** (after #58: of the retrieved objects). The generator and then the service check every step; a step that fails is never in `steps`, only in `dropped`. There are tests for it (`ai/tests/test_service.py`, including a property test over random model answers).
- `dropped`: the steps the model wrote that cannot be suggested (FR-26), in the model's order; `[]` when none. Each entry:
  - `index` — position in the model's answer (0-based). The model wrote `len(steps) + len(dropped)` steps; the suggested ones fill the other positions in order, so the panel can show a dropped step where it would have been.
  - `code` — why, from the table below; show the Turkish text for it.
  - `reason` — English details for the log or a tooltip (several problems are joined with `; `).
  - `step` — the step exactly as the model wrote it, its own `reason` included when it gave one. It is **not** a valid step; never save it.

  | `code` | Meaning | Suggested panel text |
  |---|---|---|
  | `unknown_keyword` | A keyword other than Click, Type, Select, Verify, Wait (e.g. `DoubleClick`) | "Bilinmeyen adım türü" |
  | `unknown_target` | The target is not a repository object (of this request) | "Depoda olmayan nesne" |
  | `no_match` | The model said no repository object fits (target `none.noMatch`) | "Depoda uygun nesne bulunamadı" |
  | `invalid_step` | Any other step-schema error (e.g. Click with a `value`), or no reason | "Geçersiz adım" |

  With the grammar the model can only produce `no_match`; the other codes appear when a model server ignores the grammar, and the tests cover them.
- There are 1–12 model steps. The model is asked to keep the order of the instruction and add nothing, but it can still miss or misread a step (qwen3 drops the first click of "Kaydet'e bastıktan sonra …"), which is why the user reviews every suggestion.
- `latencyMs`: time spent in the service, model included.

**Reserved object name `none.noMatch`.** The model's target list always offers `none.noMatch`, so it can say "no object fits" instead of picking a wrong object (forced choice). A step with this target is always dropped (`no_match`). A request whose `objects` contain an object of that name is refused with 400; the repository should not allow the name.

### Errors

Every error has the same shape; `details` (a list of strings, at most 20) and the generation fields appear when they apply. When every model step was dropped, the body also has `steps: []` and `dropped` (SC-27: the user asked for a "forgot password" link the repository does not have, and a model answered with an unknown keyword and that link):

```json
{
  "status": "no_valid_steps",
  "model": "qwen3:8b",
  "error": "the description could not be turned into valid steps",
  "details": [
    "$.steps[0]: unknown keyword 'DoubleClick'",
    "$.steps[1]: 'login.forgotPasswordLink' is not in the object repository"
  ],
  "steps": [],
  "dropped": [
    {"index": 0, "code": "unknown_keyword", "reason": "unknown keyword 'DoubleClick'",
     "step": {"keyword": "DoubleClick", "target": "login.loginButton", "reason": "çift tıkla"}},
    {"index": 1, "code": "unknown_target", "reason": "'login.forgotPasswordLink' is not in the object repository",
     "step": {"keyword": "Click", "target": "login.forgotPasswordLink", "reason": "Şifremi unuttum bağlantısına"}}
  ],
  "schemaVersion": "0.1",
  "promptVersion": "3+reason",
  "latencyMs": 7012
}
```

| HTTP | `status` | When | What the server should do |
|---|---|---|---|
| 400 | `bad_request` | Body is not a JSON object, a field is missing or invalid, duplicate object names, an object named `none.noMatch`, a model the service does not offer, no `objects` | Fix the request (a bug on our side); `details` names the field. |
| 401 | `unauthorized` | `AYNA_AI_TOKEN` is set and the request has no `Authorization: Bearer <token>` header, or a wrong one; `WWW-Authenticate: Bearer`. Checked before the path, so it also answers unknown paths | Send the token from `AYNA_AI_TOKEN` (a configuration error on our side). |
| 404 | `not_found` | Unknown path | — |
| 405 | `method_not_allowed` | Wrong method; `Allow` header says which | — |
| 411 | `length_required` | Neither `Content-Length` nor chunked | — |
| 413 | `too_large` | Body over the limit (64 KiB) | Send fewer objects. |
| 415 | `unsupported_media_type` | `Content-Type` is not `application/json` | — |
| 422 | `no_valid_steps` | The model answered, but every step it wrote was dropped (or it wrote none). `steps: []`; `dropped` says why for each step | Tell the user the description could not be turned into valid steps, with the reason per dropped step (`code`, table above), and ask them to rephrase. |
| 422 | `invalid_json`, `truncated`, `invalid_schema` | The model's answer as a whole is unusable: not JSON, cut off at the output limit, or not a step document (`version`, the `steps` list). No `steps`, no `dropped` | Tell the user no suggestion could be made and ask them to rephrase. |
| 422 | `no_objects` | The retriever returned no candidate objects. Not sent while the server chooses the objects: a missing or empty `objects` is a 400 | — |
| 500 | `internal_error` | A bug in the service | Show a generic error; report it with the service log. |
| 503 | `server_error` | The model server is down or does not have the model (`details` has its message) | Disable the panel as for health `ready: false`. |
| 504 | `timeout` | No answer within the service timeout (30 s by default, `--timeout`); `details`: `no answer within 30 s` | Offer a retry; the machine may be busy. |

For every 422 from the model's answer: **do not retry the same request on your own**. Generation uses temperature 0 and a fixed seed, so the same request nearly always gets the same answer. 200 always carries at least one step; a 422 never carries a suggested step.

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
  "promptVersion": "3+reason",
  "serviceVersion": "0.0.0"
}
```

- HTTP 200 whenever the service process answers; `ready` carries the answer.
- `status`: `ok` (ready) · `model_server_down` (Ollama does not answer; `error` holds the reason) · `model_missing` (Ollama answers but the default model is not pulled).
- `models[].available`: pulled on the model server, so a request may name it.
- For #78: disable the panel with a clear message when the health call fails (connection refused or no answer within a few seconds: the AI service is not running) or `ready` is false; `status` tells which message to show. A later 503 from generate-steps means the same.

## Timeouts and latency

- The service gives a whole request 30 s (`--timeout`): retrieval and the model call, a cold model load included. The model call gets what is left of it as its socket timeout and the service closes the connection to Ollama when it runs out, so a request answers within about 30 s, with 504 `timeout` at worst (live: 30.0 s). Use a read timeout of at least 35 s on the server's HTTP client, and do not retry on your own timeout (the model would run twice).
- Measured on a MacBook M2 16 GB under load from other work (load average ~4.5), qwen3:8b, the 10 spike sentences twice: p50 12.6 s, p95 25.3 s, all 20 answers valid (`memory-bank/tasks/71-nl-service.md`). Reasons add about 75% output tokens. On that busy machine the longest sentence (4 steps) can pass 30 s and get a 504; on an idle M2 the p95 was 9 s (#37). Team-hardware and GPU numbers will be added to the task note; raise `--timeout` on slow hardware.
- Ollama unloads an idle model after 5 minutes by default; the next request then pays a cold load (~6 s here). Start Ollama with `OLLAMA_KEEP_ALIVE=30m` (or longer) on the machine that serves it.
- Requests are handled in parallel, but Ollama runs one generation at a time by default, so concurrent requests queue and each one waits longer.

## Versions

- `schemaVersion`: version of the step schema the steps follow (`schemas/step.schema.json`, now `0.1`).
- `promptVersion`: changes whenever the prompt changes. Store it with accepted suggestions if you want to trace which prompt produced them (RQ3).
- `serviceVersion`: the `ayna-ai` package version.

## Network

- Closed network: the service makes no call except to the Ollama server, which must be on a loopback address; the Ollama client ignores proxy settings and refuses redirects.
- It listens on `127.0.0.1` by default and refuses a non-loopback `--host` unless started with `--allow-remote` (logged). In a container (#82) use `--host 0.0.0.0 --allow-remote` and do not publish the port: only the server reaches it, over the Compose network (RS NFR-46).
- **Whatever listens off loopback needs a token**, as the agent (`AYNA_AGENT_TOKEN`) and the CLI runner (`AYNA_SERVER_TOKEN`) do: `--allow-remote` refuses to start without `AYNA_AI_TOKEN` (≥ 16 characters), and with it every request needs `Authorization: Bearer <token>`, compared in constant time. The server reads the same value from its own environment. On loopback the token is optional; when set, it is checked there too. A model run costs up to 30 s, so an open port would let any container on the network keep the machine busy.

## Candidate objects and retrieval (#58)

The server chooses the candidate objects and sends them in `objects`; the AI service never reads the graph and holds no database credentials (decided 2026-10-29, SDD §2.2.2 rule 5 and AI-4). Until #58, send the objects of the current application and screen from the repository (at most 100, logical name + Turkish description). With #58 the server merges the current screen's objects with the vector top-k for the instruction, current screen first. For the vectors, #58 adds `POST /ai/embed` (texts → embeddings, planned): the server calls it for the instruction and when a repository object is created or changed, and stores object vectors in Neo4j itself.
