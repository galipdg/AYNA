"""StepGenerator and the batch CLI with the model server mocked (#37)."""

import json
import logging
import time

import pytest

from ayna_ai.generate import (
    PROMPT_VERSION,
    REASON_PROMPT,
    GenerationSettings,
    Status,
    StepGenerator,
    generation_schema,
    main,
    percentile,
)
from ayna_ai.ollama import ModelServerError, ModelTimeout
from ayna_ai.validate import load_step_schema

TEXT = "Kullanıcı adı alanına admin yaz ve giriş butonuna tıkla."
STEPS = [
    {"keyword": "Type", "target": "login.userNameInput", "value": "admin"},
    {"keyword": "Click", "target": "login.loginButton"},
]


def reply(content: str, done_reason: str = "stop") -> dict:
    """An Ollama /api/chat answer (stream: false)."""
    return {
        "model": "qwen3:8b",
        "message": {"role": "assistant", "content": content},
        "done": True,
        "done_reason": done_reason,
        "total_duration": 3_200_000_000,
        "load_duration": 50_000_000,
        "prompt_eval_count": 441,
        "eval_count": 38,
    }


def document(steps=STEPS) -> str:
    return json.dumps({"version": "0.1", "steps": steps}, ensure_ascii=False)


class FakeClient:
    def __init__(self, answer=None, error=None, delay=0.0):
        self.answer, self.error, self.delay = answer, error, delay
        self.bodies = []

    def chat(self, body):
        self.bodies.append(body)
        time.sleep(self.delay)
        if self.error:
            raise self.error
        return self.answer


def test_valid_output_returns_the_document_and_metrics(spike_objects):
    result = StepGenerator(FakeClient(reply(document()))).generate(TEXT, spike_objects)
    assert result.status is Status.OK and result.ok
    assert result.document == {"version": "0.1", "steps": STEPS}
    assert result.errors == []
    assert (result.prompt_tokens, result.output_tokens) == (441, 38)
    assert result.load_s == 0.05
    assert result.latency_s >= 0


def test_request_is_constrained_and_deterministic(spike_objects):
    client = FakeClient(reply(document()))
    StepGenerator(client).generate(TEXT, spike_objects)
    body = client.bodies[0]
    assert body["format"] == generation_schema(load_step_schema(), list(spike_objects))
    assert body["think"] is False and body["stream"] is False
    assert body["options"] == {
        "temperature": 0,
        "seed": 42,
        "num_ctx": 4096,
        "num_predict": 512,
    }
    system, user = body["messages"]
    assert user == {"role": "user", "content": TEXT}
    assert "- customer.cityCombo — Şehir listesi" in system["content"]
    assert '"version": "0.1"' in system["content"]


def test_json_format_is_the_unconstrained_baseline(spike_objects):
    client = FakeClient(reply(document()))
    StepGenerator(client, GenerationSettings(format="json")).generate(
        TEXT, spike_objects
    )
    assert client.bodies[0]["format"] == "json"


def test_unknown_format_is_refused():
    with pytest.raises(ValueError):
        StepGenerator(FakeClient(), GenerationSettings(format="gbnf"))


@pytest.mark.parametrize(
    ("content", "done_reason", "status"),
    [
        (
            '{"version": "0.1", "steps": [{"keyword": "Click", "target": "login.lo',
            "stop",
            "invalid_json",
        ),
        (
            '{"version": "0.1", "steps": [{"keyword": "Type", "value": "}}}}}}',
            "length",
            "truncated",
        ),
        ("", "stop", "invalid_json"),
    ],
)
def test_unparseable_output_is_a_failure(spike_objects, content, done_reason, status):
    result = StepGenerator(FakeClient(reply(content, done_reason))).generate(
        TEXT, spike_objects
    )
    assert result.status == status and not result.ok
    assert result.document is None
    assert result.errors[0].startswith("invalid JSON")
    assert result.output == content


@pytest.mark.parametrize(
    ("output", "path"),
    [
        (
            document(
                [{"keyword": "Click", "target": "login.loginButton", "value": "x"}]
            ),
            "$.steps[0]",
        ),
        (
            document([{"keyword": "Type", "target": "login.userNameInput"}]),
            "$.steps[0]",
        ),
        (
            document([{"keyword": "Press", "target": "login.loginButton"}]),
            "$.steps[0].keyword",
        ),
        (json.dumps({"steps": STEPS}), "$"),
    ],
    ids=["Click with value", "Type without value", "unknown keyword", "no version"],
)
def test_output_against_the_step_schema_is_rejected(spike_objects, output, path):
    result = StepGenerator(FakeClient(reply(output))).generate(TEXT, spike_objects)
    assert result.status is Status.INVALID_SCHEMA
    assert result.document is None
    assert any(error.startswith(path) for error in result.errors), result.errors


def test_target_outside_the_repository_is_rejected(spike_objects):
    steps = STEPS + [{"keyword": "Click", "target": "settings.deleteAllButton"}]
    result = StepGenerator(FakeClient(reply(document(steps)))).generate(
        TEXT, spike_objects
    )
    assert result.status is Status.UNKNOWN_TARGET
    assert result.document is None
    assert result.errors == [
        "$.steps[2].target: 'settings.deleteAllButton' is not in the object repository"
    ]


def test_timeout_is_a_failure_with_latency(spike_objects):
    client = FakeClient(error=ModelTimeout("no answer within 0.05 s"), delay=0.05)
    result = StepGenerator(client).generate(TEXT, spike_objects)
    assert result.status is Status.TIMEOUT and not result.ok
    assert result.document is None and result.output is None
    assert result.latency_s >= 0.05
    assert result.errors == ["no answer within 0.05 s"]


def test_server_error_is_a_failure(spike_objects):
    client = FakeClient(error=ModelServerError("HTTP 404: model 'x' not found"))
    result = StepGenerator(client).generate(TEXT, spike_objects)
    assert result.status is Status.SERVER_ERROR
    assert result.errors == ["HTTP 404: model 'x' not found"]


def test_latency_is_logged_per_scenario(spike_objects, caplog):
    generator = StepGenerator(FakeClient(reply(document()), delay=0.01))
    with caplog.at_level(logging.INFO, logger="ayna_ai.generate"):
        generator.generate(TEXT, spike_objects, scenario="login-1")
        generator.generate(TEXT, spike_objects, scenario="login-2")
    records = [json.loads(record.getMessage()) for record in caplog.records]
    assert [r["scenario"] for r in records] == ["login-1", "login-2"]
    for record in records:
        assert record["event"] == "generate"
        assert record["status"] == "ok"
        assert record["model"] == "qwen3:8b"
        assert record["latency_ms"] >= 10
        assert (record["prompt_tokens"], record["output_tokens"], record["steps"]) == (
            441,
            38,
            2,
        )


REASONED = [
    {**STEPS[0], "reason": "'kullanıcı adı alanına admin yaz'"},
    {**STEPS[1], "reason": "'giriş butonuna tıkla'"},
]


def test_reasons_are_asked_for_and_returned_beside_the_steps(spike_objects):
    client = FakeClient(reply(document(REASONED)))
    generator = StepGenerator(client, GenerationSettings(reasons=True))
    result = generator.generate(TEXT, spike_objects)
    assert result.ok
    assert result.document == {"version": "0.1", "steps": STEPS}
    assert result.reasons == [
        "'kullanıcı adı alanına admin yaz'",
        "'giriş butonuna tıkla'",
    ]
    body = client.bodies[0]
    assert body["format"] == generation_schema(
        load_step_schema(), list(spike_objects), reason_max_length=100
    )
    assert body["messages"][0]["content"].endswith(REASON_PROMPT)
    assert generator.prompt_version == PROMPT_VERSION + "+reason"


def test_without_reasons_the_prompt_and_result_are_unchanged(spike_objects):
    client = FakeClient(reply(document()))
    generator = StepGenerator(client)
    result = generator.generate(TEXT, spike_objects)
    assert result.ok and result.reasons is None
    assert REASON_PROMPT not in client.bodies[0]["messages"][0]["content"]
    assert generator.prompt_version == PROMPT_VERSION


@pytest.mark.parametrize(
    "steps",
    [
        [REASONED[0], STEPS[1]],
        [REASONED[0], {**STEPS[1], "reason": "x" * 101}],
    ],
    ids=["missing reason", "reason too long"],
)
def test_a_bad_reason_is_a_schema_failure(spike_objects, steps):
    result = StepGenerator(
        FakeClient(reply(document(steps))), GenerationSettings(reasons=True)
    ).generate(TEXT, spike_objects)
    assert result.status is Status.INVALID_SCHEMA
    assert result.document is None and result.reasons is None
    assert result.errors[0].startswith("$.steps[1].reason")


def test_a_reason_without_reasons_enabled_is_a_schema_failure(spike_objects):
    result = StepGenerator(FakeClient(reply(document(REASONED)))).generate(
        TEXT, spike_objects
    )
    assert result.status is Status.INVALID_SCHEMA


def test_warm_up_only_loads_the_model():
    client = FakeClient({"done": True})
    StepGenerator(client, GenerationSettings(model="gemma4:e4b-it-qat")).warm_up()
    assert client.bodies == [{"model": "gemma4:e4b-it-qat", "messages": []}]


@pytest.mark.parametrize(
    ("values", "q", "expected"),
    [
        ([], 50, None),
        ([3.0], 95, 3.0),
        ([1, 2, 3, 4], 50, 2.5),
        (list(range(1, 11)), 95, 9.55),
    ],
)
def test_percentile(values, q, expected):
    assert percentile(values, q) == pytest.approx(expected)


@pytest.fixture
def batch_files(tmp_path, spike_objects):
    cases = [
        {"id": 1, "text": TEXT, "expected": ["Type", "Click"]},
        {"id": 2, "text": "Giriş butonuna tıkla.", "expected": ["Click"]},
    ]
    inputs = tmp_path / "inputs.jsonl"
    inputs.write_text(
        "".join(json.dumps(c, ensure_ascii=False) + "\n" for c in cases), "utf-8"
    )
    objects = tmp_path / "objects.json"
    objects.write_text(json.dumps(spike_objects, ensure_ascii=False), "utf-8")
    return inputs, objects, tmp_path


def serve(fake_ollama, outputs: list[str]):
    """Answer /api/chat with `outputs` in turn; a warm-up gets an empty answer."""
    pending = list(outputs)

    def respond(path, body):
        if path == "/api/version":
            return 200, {"version": "0.0.test"}, 0, {}
        if not body["messages"]:
            return 200, {"done": True, "done_reason": "load"}, 0, {}
        return 200, reply(pending.pop(0)), 0, {}

    fake_ollama.respond = respond


def test_cli_batch_writes_results_and_a_latency_log(fake_ollama, batch_files, capsys):
    inputs, objects, tmp = batch_files
    serve(
        fake_ollama,
        [document(), document([{"keyword": "Wait", "target": "login.loginButton"}])],
    )
    out, log = tmp / "results.json", tmp / "latency.jsonl"
    argv = ["--input", str(inputs), "--objects", str(objects), "--out", str(out)]
    code = main(argv + ["--log", str(log), "--host", fake_ollama.url, "--note", "test"])

    # Scenario 2 is a valid document with the wrong keyword: ok, but no keyword match.
    assert code == 0
    results = json.loads(out.read_text("utf-8"))
    summary = results["summary"]
    assert (summary["n"], summary["ok"], summary["ok_rate"]) == (2, 2, 1.0)
    assert summary["by_status"] == {"ok": 2}
    assert summary["keyword_match"] == 1
    assert summary["latency_p50_s"] is not None and summary["latency_p95_s"] is not None
    assert results["environment"]["ollama"] == "0.0.test"
    assert results["settings"]["model"] == "qwen3:8b"
    assert results["prompt_version"] == PROMPT_VERSION
    assert results["warmup_s"] is not None
    assert [s["keywords"] for s in results["scenarios"]] == [
        ["Type", "Click"],
        ["Wait"],
    ]

    lines = [json.loads(line) for line in log.read_text("utf-8").splitlines()]
    assert [line["scenario"] for line in lines] == [1, 2]
    assert all("latency_ms" in line for line in lines)
    assert fake_ollama.requests[0] == (
        "/api/chat",
        {"model": "qwen3:8b", "messages": []},
    )
    assert "Results:" in capsys.readouterr().out


def test_cli_exits_1_when_a_scenario_fails(fake_ollama, batch_files):
    inputs, objects, tmp = batch_files
    serve(fake_ollama, [document(), '{"version": "0.1", "steps": [{"keyword": "Cl'])
    out = tmp / "results.json"
    argv = ["--input", str(inputs), "--objects", str(objects), "--out", str(out)]
    assert main(argv + ["--host", fake_ollama.url, "--no-warmup"]) == 1
    summary = json.loads(out.read_text("utf-8"))["summary"]
    assert summary["by_status"] == {"ok": 1, "invalid_json": 1}
    assert all(body["messages"] for _, body in fake_ollama.requests if body)


def test_cli_refuses_a_remote_model_server(batch_files):
    inputs, objects, tmp = batch_files
    argv = [
        "--input",
        str(inputs),
        "--objects",
        str(objects),
        "--out",
        str(tmp / "r.json"),
    ]
    with pytest.raises(SystemExit) as caught:
        main(argv + ["--host", "http://192.168.1.20:11434"])
    assert caught.value.code == 2
    assert not (tmp / "r.json").exists()
