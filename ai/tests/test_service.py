"""The HTTP service with a fake Ollama: contract, error codes, target guard (#71)."""

import http.client
import json
import logging
import random
import socket
import threading

import pytest
from jsonschema import Draft202012Validator

from ayna_ai import service as service_module
from ayna_ai.generate import PROMPT_VERSION, REASON_PROMPT, GenerationResult, Status
from ayna_ai.retrieve import PassThroughRetriever, RetrievalInputError, RetrievalQuery
from ayna_ai.service import (
    FAILURES,
    GENERATE_PATH,
    HEALTH_PATH,
    ServiceConfig,
    StepService,
    create_server,
    is_loopback_host,
    main,
)
from ayna_ai.validate import load_step_schema

STEP_SCHEMA = Draft202012Validator(load_step_schema())
TEXT = "Kullanıcı adı alanına admin yaz ve giriş butonuna tıkla."
STEPS = [
    {
        "keyword": "Type",
        "target": "login.userNameInput",
        "value": "admin",
        "reason": "'kullanıcı adı alanına admin yaz'",
    },
    {
        "keyword": "Click",
        "target": "login.loginButton",
        "reason": "'giriş butonuna tıkla'",
    },
]


def chat_reply(content: str, done_reason: str = "stop") -> dict:
    """An Ollama /api/chat answer (stream: false)."""
    return {
        "model": "qwen3:8b",
        "message": {"role": "assistant", "content": content},
        "done": True,
        "done_reason": done_reason,
        "prompt_eval_count": 500,
        "eval_count": 60,
    }


def document(steps=STEPS) -> str:
    return json.dumps({"version": "0.1", "steps": steps}, ensure_ascii=False)


def model_answers(
    fake_ollama, content: str | None = None, *, done_reason="stop", delay=0.0
):
    """Answer /api/chat with `content` (default: STEPS) and /api/tags with qwen3:8b."""
    content = document() if content is None else content

    def respond(path, body):
        if path == "/api/tags":
            return 200, {"models": [{"name": "qwen3:8b"}]}, 0, {}
        return 200, chat_reply(content, done_reason), delay, {}

    fake_ollama.respond = respond


def chats(fake_ollama) -> list[dict]:
    return [body for path, body in fake_ollama.requests if path == "/api/chat"]


def free_port() -> int:
    """A loopback port nobody listens on."""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class Running:
    """A started service and a tiny HTTP client for it."""

    def __init__(self, server) -> None:
        self.server = server
        self.port = server.server_address[1]

    def request(self, method, path, body=None, headers=None, **kwargs):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        try:
            conn.request(method, path, body=body, headers=headers or {}, **kwargs)
            response = conn.getresponse()
            data = response.read()
            payload = json.loads(data) if data else None
            return response.status, payload, dict(response.getheaders())
        finally:
            conn.close()

    def generate(self, payload, content_type="application/json"):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        status, payload, _ = self.request(
            "POST", GENERATE_PATH, body, {"Content-Type": content_type}
        )
        return status, payload

    def health(self):
        status, payload, _ = self.request("GET", HEALTH_PATH)
        return status, payload


@pytest.fixture
def start_service(fake_ollama):
    """start(retriever=None, **ServiceConfig fields) -> Running, on 127.0.0.1:<free>."""
    servers = []

    def start(retriever=None, **fields):
        fields.setdefault("model_host", fake_ollama.url)
        service = StepService(ServiceConfig(**fields), retriever=retriever)
        server = create_server(service, "127.0.0.1", 0)
        thread = threading.Thread(
            target=server.serve_forever, args=(0.05,), daemon=True
        )
        thread.start()
        servers.append(server)
        return Running(server)

    yield start
    for server in servers:
        server.shutdown()
        server.server_close()


@pytest.fixture
def request_body(spike_objects):
    return {
        "text": TEXT,
        "app": "customer-records",
        "version": "1.0",
        "screen": "login",
        "objects": [
            {"name": name, "description": description}
            for name, description in spike_objects.items()
        ],
    }


# --- happy path ---------------------------------------------------------------


def test_generates_steps_with_a_reason_each(fake_ollama, start_service, request_body):
    model_answers(fake_ollama)
    status, body = start_service().generate(request_body)

    assert status == 200
    assert body["status"] == "ok"
    assert body["steps"] == STEPS
    assert (body["model"], body["schemaVersion"]) == ("qwen3:8b", "0.1")
    assert body["promptVersion"] == PROMPT_VERSION + "+reason"
    assert isinstance(body["latencyMs"], int) and body["latencyMs"] >= 0
    # Without its reason, each step is a step-schema step.
    steps = [{k: v for k, v in s.items() if k != "reason"} for s in body["steps"]]
    assert STEP_SCHEMA.is_valid({"version": body["schemaVersion"], "steps": steps})


def test_the_model_call_is_constrained_to_the_request_objects(
    fake_ollama, start_service, request_body, spike_objects
):
    model_answers(fake_ollama)
    start_service().generate(request_body)

    (chat,) = chats(fake_ollama)
    assert chat["model"] == "qwen3:8b"
    assert chat["options"]["num_predict"] == 768
    for branch in chat["format"]["properties"]["steps"]["items"]["anyOf"]:
        assert branch["properties"]["target"]["enum"] == list(spike_objects)
        assert "reason" in branch["required"]
    system, user = chat["messages"]
    assert user["content"] == TEXT
    assert system["content"].endswith(REASON_PROMPT)
    assert "- customer.cityCombo — Şehir listesi" in system["content"]


def test_a_description_is_optional(fake_ollama, start_service):
    model_answers(fake_ollama, document([STEPS[1]]))
    objects = [{"name": "login.loginButton"}]
    status, body = start_service().generate(
        {"text": "Girişe tıkla.", "app": "a", "objects": objects}
    )
    assert status == 200 and len(body["steps"]) == 1
    assert "- login.loginButton\n" in chats(fake_ollama)[0]["messages"][0]["content"]


def test_a_request_can_pick_an_offered_model(fake_ollama, start_service, request_body):
    model_answers(fake_ollama)
    running = start_service(models=("qwen3:8b", "gemma4:e4b-it-qat"))
    status, body = running.generate({**request_body, "model": "gemma4:e4b-it-qat"})
    assert status == 200 and body["model"] == "gemma4:e4b-it-qat"
    assert chats(fake_ollama)[0]["model"] == "gemma4:e4b-it-qat"


# --- target guard: never a step outside the retrieved objects -----------------


class DroppingRetriever:
    """Keeps the request's objects except `drop`: the model may still name it."""

    def __init__(self, drop: str) -> None:
        self.drop = drop

    def retrieve(self, query):
        return {k: v for k, v in query.objects.items() if k != self.drop}


@pytest.mark.parametrize(
    ("steps", "retriever"),
    [
        ([{**STEPS[1], "target": "settings.deleteAllButton"}], None),
        ([STEPS[0], {**STEPS[1], "target": "login.logoutButton"}], None),
        ([{**STEPS[1], "target": "login.loginbutton"}], None),
        ([{**STEPS[1], "target": "Login.loginButton"}], None),
        (STEPS, DroppingRetriever("login.loginButton")),
    ],
    ids=[
        "not in the repository",
        "second step unknown",
        "wrong case",
        "invalid logical name",
        "in the request but not retrieved",
    ],
)
def test_an_unknown_target_is_422_never_200(
    fake_ollama, start_service, request_body, steps, retriever
):
    model_answers(fake_ollama, document(steps))
    status, body = start_service(retriever=retriever).generate(request_body)
    assert status == 422
    assert body["status"] in ("unknown_target", "invalid_schema")
    assert "steps" not in body
    assert body["details"]


def test_random_answers_only_pass_when_every_target_was_retrieved(
    fake_ollama, start_service, spike_objects
):
    """Property check over seeded random model answers that ignore the grammar."""
    rng = random.Random(71)
    known = list(spike_objects)
    unknown = ["login.adminPanel", "settings.deleteAllButton", "main.exitButton"]
    retrieved = set(rng.sample(known, 8))
    request = {
        "text": TEXT,
        "app": "customer-records",
        "objects": [{"name": name} for name in sorted(retrieved)],
    }
    answers = []
    fake_ollama.respond = lambda path, body: (200, chat_reply(answers[-1]), 0, {})
    running = start_service()

    outcomes = set()
    for _ in range(150):
        pool = rng.choice([sorted(retrieved), known, known + unknown])
        targets = [rng.choice(pool) for _ in range(rng.randint(1, 4))]
        steps = [{"keyword": "Click", "target": t, "reason": "r"} for t in targets]
        answers.append(document(steps))
        status, body = running.generate(request)
        all_retrieved = set(targets) <= retrieved
        assert (status == 200) == all_retrieved, (targets, body)
        if status == 200:
            assert {step["target"] for step in body["steps"]} <= retrieved
        else:
            assert status == 422 and "steps" not in body
        outcomes.add(status)
    assert outcomes == {200, 422}


def test_the_service_guard_catches_a_generator_that_lets_one_through(
    fake_ollama, request_body, caplog
):
    """Defence in depth: even a generator that skips its own check is caught."""

    class Lenient:
        def generate(self, text, objects):
            steps = [{"keyword": "Click", "target": "main.exitButton"}]
            document = {"version": "0.1", "steps": steps}
            return GenerationResult(Status.OK, document=document, reasons=["r"])

    service = StepService(ServiceConfig(model_host=fake_ollama.url))
    service.generators["qwen3:8b"] = Lenient()
    with caplog.at_level(logging.ERROR, logger="ayna_ai.service"):
        code, body = service.generate_steps(request_body)
    assert code == 422 and body["status"] == "unknown_target"
    assert "steps" not in body
    assert any('"event": "target_guard"' in r.getMessage() for r in caplog.records)


# --- generation failures --------------------------------------------------------


@pytest.mark.parametrize(
    ("content", "done_reason", "status"),
    [
        ('{"version": "0.1", "steps": [{"keyword": "Cl', "stop", "invalid_json"),
        (
            '{"version": "0.1", "steps": [{"keyword": "Type", "value": "}}}',
            "length",
            "truncated",
        ),
        (document([{**STEPS[1], "value": "x"}]), "stop", "invalid_schema"),
        (
            document([{k: v for k, v in STEPS[1].items() if k != "reason"}]),
            "stop",
            "invalid_schema",
        ),
    ],
    ids=["invalid JSON", "truncated", "Click with value", "no reason"],
)
def test_a_bad_model_answer_is_422(
    fake_ollama, start_service, request_body, content, done_reason, status
):
    model_answers(fake_ollama, content, done_reason=done_reason)
    code, body = start_service().generate(request_body)
    assert code == 422
    assert body["status"] == status
    assert body["error"] and body["details"]
    assert "steps" not in body
    assert body["model"] == "qwen3:8b" and "promptVersion" in body


def test_a_slow_model_server_is_504(fake_ollama, start_service, request_body):
    model_answers(fake_ollama, delay=0.5)
    code, body = start_service(timeout_s=0.1).generate(request_body)
    assert code == 504
    assert body["status"] == "timeout"
    assert "steps" not in body


def test_a_model_server_that_is_down_is_503_and_health_says_not_ready(
    start_service, request_body
):
    running = start_service(model_host=f"http://127.0.0.1:{free_port()}")
    code, body = running.generate(request_body)
    assert code == 503
    assert body["status"] == "server_error"
    assert body["error"] == "the model server is unavailable"
    assert "cannot reach" in body["details"][0]

    code, health = running.health()
    assert code == 200
    assert health["ready"] is False
    assert health["status"] == "model_server_down"
    assert health["modelServer"]["reachable"] is False
    assert health["models"] == [{"name": "qwen3:8b", "available": False}]
    assert "cannot reach" in health["error"]


def test_a_missing_model_is_503(fake_ollama, start_service, request_body):
    fake_ollama.respond = lambda path, body: (
        404,
        {"error": "model 'qwen3:8b' not found"},
        0,
        {},
    )
    code, body = start_service().generate(request_body)
    assert code == 503
    assert body["details"] == ["HTTP 404: model 'qwen3:8b' not found"]


# --- health -------------------------------------------------------------------


def test_health_is_ready_when_the_default_model_is_pulled(fake_ollama, start_service):
    model_answers(fake_ollama)
    code, health = start_service(models=("qwen3:8b", "gemma4:e4b-it-qat")).health()
    assert code == 200
    assert health["ready"] is True and health["status"] == "ok"
    assert health["modelServer"] == {"url": fake_ollama.url, "reachable": True}
    assert health["defaultModel"] == "qwen3:8b"
    assert health["models"] == [
        {"name": "qwen3:8b", "available": True},
        {"name": "gemma4:e4b-it-qat", "available": False},
    ]
    assert health["promptVersion"] == PROMPT_VERSION + "+reason"
    assert "error" not in health
    assert chats(fake_ollama) == []  # health never runs the model


@pytest.mark.parametrize(
    ("pulled", "model", "ready"),
    [
        (["gemma4:e4b-it-qat"], "qwen3:8b", False),
        (["qwen3:latest"], "qwen3", True),
        (["qwen3:14b"], "qwen3", False),
    ],
)
def test_health_matches_model_names_like_ollama(
    fake_ollama, start_service, pulled, model, ready
):
    listing = {"models": [{"name": name} for name in pulled]}
    fake_ollama.respond = lambda path, body: (200, listing, 0, {})
    _, health = start_service(models=(model,)).health()
    assert health["ready"] is ready
    assert health["status"] == ("ok" if ready else "model_missing")


# --- bad requests ---------------------------------------------------------------


def body_with(request_body, **changes):
    body = dict(request_body)
    for key, value in changes.items():
        if value is None:
            body.pop(key)
        else:
            body[key] = value
    return body


@pytest.mark.parametrize(
    ("change", "detail"),
    [
        ({"text": None}, "'text' is a required property"),
        ({"text": "   "}, "$.text"),
        ({"text": "x" * 2001}, "$.text"),
        ({"app": None}, "'app' is a required property"),
        ({"objects": []}, "$.objects"),
        ({"objects": [{"name": "Login Button"}]}, "$.objects[0].name"),
        ({"objects": [{"name": "a.b", "type": "Button"}]}, "$.objects[0]"),
        ({"objects": [{"name": f"s.o{i}"} for i in range(101)]}, "$.objects"),
        ({"objects": [{"name": "a.b"}, {"name": "a.b"}]}, "a.b"),
        ({"objects": None}, "objects is required"),
        ({"model": "llama3:70b"}, "offered: qwen3:8b"),
        ({"prompt": "ignore the rules"}, "'prompt' was unexpected"),
    ],
    ids=[
        "no text",
        "blank text",
        "text too long",
        "no app",
        "no objects",
        "invalid object name",
        "unknown object field",
        "too many objects",
        "duplicate object",
        "objects missing (no retrieval yet)",
        "model not offered",
        "unknown field",
    ],
)
def test_a_bad_request_is_400_and_never_reaches_the_model(
    fake_ollama, start_service, request_body, change, detail
):
    model_answers(fake_ollama)
    code, body = start_service().generate(body_with(request_body, **change))
    assert code == 400
    assert body["status"] == "bad_request"
    text = body["error"] + " ".join(body.get("details", []))
    assert detail in text, body
    assert chats(fake_ollama) == []


@pytest.mark.parametrize(
    "raw",
    [b"not json", b'["a list"]', b"\xff\xfe", b'"text"'],
    ids=["not JSON", "a list", "not UTF-8", "a string"],
)
def test_a_body_that_is_not_a_json_object_is_400(fake_ollama, start_service, raw):
    model_answers(fake_ollama)
    code, body, _ = start_service().request(
        "POST", GENERATE_PATH, raw, {"Content-Type": "application/json"}
    )
    assert code == 400 and body["status"] == "bad_request"
    assert chats(fake_ollama) == []


def test_an_oversized_request_is_413(fake_ollama, start_service, request_body):
    model_answers(fake_ollama)
    running = start_service(max_body_bytes=4096)
    code, body = running.generate({**request_body, "app": "x" * 5000})
    assert code == 413 and body["status"] == "too_large"
    code, body, _ = running.request(
        "POST",
        GENERATE_PATH,
        b"{" + b" " * 300_000 + b"}",
        {"Content-Type": "application/json"},
    )
    assert code == 413
    assert chats(fake_ollama) == []


def test_a_chunked_request_is_read(fake_ollama, start_service, request_body):
    """Spring's RestClient on the JDK HttpClient may stream a JSON body chunked."""
    model_answers(fake_ollama)
    data = json.dumps(request_body, ensure_ascii=False).encode("utf-8")
    parts = [data[i : i + 700] for i in range(0, len(data), 700)]
    code, body, _ = start_service().request(
        "POST", GENERATE_PATH, iter(parts), {"Content-Type": "application/json"}
    )
    assert code == 200 and body["steps"] == STEPS
    assert len(parts) > 1


def test_an_oversized_chunked_request_is_413(fake_ollama, start_service):
    parts = [b"{" + b" " * 2000] * 5 + [b"}"]
    code, body, _ = start_service(max_body_bytes=4096).request(
        "POST", GENERATE_PATH, iter(parts), {"Content-Type": "application/json"}
    )
    assert code == 413 and body["status"] == "too_large"
    assert chats(fake_ollama) == []


@pytest.mark.parametrize(
    ("headers", "code"),
    [
        ("", 411),
        ("Content-Length: -1\r\n", 400),
        ("Transfer-Encoding: chunked\r\n", 400),  # no chunk follows
    ],
)
def test_a_body_without_a_valid_length_is_rejected(start_service, headers, code):
    running = start_service()
    request = (
        f"POST {GENERATE_PATH} HTTP/1.1\r\nHost: 127.0.0.1\r\n"
        f"Content-Type: application/json\r\n{headers}Connection: close\r\n\r\n"
    )
    with socket.create_connection(("127.0.0.1", running.port), timeout=5) as sock:
        sock.sendall(request.encode("ascii"))
        if "chunked" in headers:
            sock.shutdown(socket.SHUT_WR)
        answer = b""
        while chunk := sock.recv(65536):
            answer += chunk
    status_line, _, rest = answer.partition(b"\r\n")
    assert int(status_line.split()[1]) == code
    assert json.loads(rest.split(b"\r\n\r\n", 1)[1])["status"] in (
        "length_required",
        "bad_request",
    )


def test_a_body_that_is_not_json_content_is_415(
    fake_ollama, start_service, request_body
):
    model_answers(fake_ollama)
    code, body = start_service().generate(request_body, content_type="text/plain")
    assert code == 415 and body["status"] == "unsupported_media_type"
    assert chats(fake_ollama) == []


def test_charset_in_the_content_type_is_fine(fake_ollama, start_service, request_body):
    model_answers(fake_ollama)
    code, _ = start_service().generate(
        request_body, content_type="application/json; charset=utf-8"
    )
    assert code == 200


@pytest.mark.parametrize(
    ("method", "path", "code", "allow"),
    [
        ("GET", GENERATE_PATH, 405, "POST"),
        ("PUT", GENERATE_PATH, 405, "POST"),
        ("POST", HEALTH_PATH, 405, "GET"),
        ("DELETE", HEALTH_PATH, 405, "GET"),
        ("GET", "/", 404, None),
        ("POST", "/ai/generate", 404, None),
    ],
)
def test_wrong_paths_and_methods(start_service, method, path, code, allow):
    status, body, headers = start_service().request(method, path, b"{}")
    assert status == code
    assert body["status"] == ("method_not_allowed" if allow else "not_found")
    assert headers.get("Allow") == allow


def test_an_internal_error_is_500(fake_ollama, start_service, request_body):
    class Broken:
        def retrieve(self, query):
            raise RuntimeError("bug")

    code, body = start_service(retriever=Broken()).generate(request_body)
    assert code == 500 and body["status"] == "internal_error"


def test_every_generator_failure_has_an_http_status():
    """A new generator Status must get an HTTP mapping, or the service answers 500."""
    assert set(FAILURES) == set(Status) - {Status.OK}
    assert {code for code, _ in FAILURES.values()} == {422, 503, 504}


def test_the_request_log_holds_no_instruction_text(
    fake_ollama, start_service, request_body, caplog
):
    model_answers(fake_ollama)
    secret = "Şifre alanına GizliParola123 yaz."
    with caplog.at_level(logging.INFO, logger="ayna_ai"):
        start_service().generate({**request_body, "text": secret})
    lines = [r.getMessage() for r in caplog.records]
    request = [json.loads(line) for line in lines if '"event": "request"' in line]
    assert request and request[0]["code"] == 200 and request[0]["steps"] == 2
    assert not any("GizliParola123" in line for line in lines)


# --- retriever ----------------------------------------------------------------


def test_the_retriever_gets_the_request_context(
    fake_ollama, start_service, request_body
):
    seen = []

    class Recording(PassThroughRetriever):
        def retrieve(self, query):
            seen.append(query)
            return super().retrieve(query)

    model_answers(fake_ollama)
    start_service(retriever=Recording()).generate(request_body)
    (query,) = seen
    assert (query.text, query.app, query.version, query.screen) == (
        TEXT,
        "customer-records",
        "1.0",
        "login",
    )
    assert list(query.objects)[:2] == ["login.userNameInput", "login.passwordInput"]


def test_a_retriever_that_finds_nothing_is_422(
    fake_ollama, start_service, request_body
):
    class Empty:
        def retrieve(self, query):
            return {}

    model_answers(fake_ollama)
    code, body = start_service(retriever=Empty()).generate(request_body)
    assert code == 422 and body["status"] == "no_objects"
    assert chats(fake_ollama) == []


def test_pass_through_retriever():
    objects = {"login.loginButton": "Giriş butonu"}
    query = RetrievalQuery(text="t", app="a", objects=objects)
    assert PassThroughRetriever().retrieve(query) == objects
    with pytest.raises(RetrievalInputError, match="#58"):
        PassThroughRetriever().retrieve(RetrievalQuery(text="t", app="a"))


# --- binding ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("host", "loopback"),
    [
        ("127.0.0.1", True),
        ("127.0.0.2", True),
        ("::1", True),
        ("localhost", True),
        ("0.0.0.0", False),
        ("", False),
        ("::", False),
        ("192.168.1.20", False),
        ("localhost.example.com", False),
    ],
)
def test_is_loopback_host(host, loopback):
    assert is_loopback_host(host) is loopback


@pytest.mark.parametrize("host", ["0.0.0.0", "192.168.1.20", ""])
def test_a_non_loopback_bind_is_refused(fake_ollama, host):
    service = StepService(ServiceConfig(model_host=fake_ollama.url))
    with pytest.raises(ValueError, match="--allow-remote"):
        create_server(service, host, 0)


def test_the_cli_refuses_a_non_loopback_host(capsys):
    with pytest.raises(SystemExit) as caught:
        main(["--host", "0.0.0.0", "--port", "0", "--no-warmup"])
    assert caught.value.code == 2
    assert "not a loopback address" in capsys.readouterr().err


def test_the_cli_refuses_a_remote_model_server(capsys):
    with pytest.raises(SystemExit) as caught:
        main(["--model-host", "http://10.0.0.5:11434", "--no-warmup"])
    assert caught.value.code == 2
    assert "closed network" in capsys.readouterr().err


def test_allow_remote_binds_and_logs_a_warning(fake_ollama, monkeypatch, caplog):
    bound = []
    monkeypatch.setattr(
        service_module, "ServiceServer", lambda address, service: bound.append(address)
    )
    service = StepService(ServiceConfig(model_host=fake_ollama.url))
    with caplog.at_level(logging.WARNING, logger="ayna_ai.service"):
        create_server(service, "0.0.0.0", 8090, allow_remote=True)
    assert bound == [("0.0.0.0", 8090)]
    (warning,) = [json.loads(r.getMessage()) for r in caplog.records]
    assert warning["event"] == "remote_bind" and warning["host"] == "0.0.0.0"
