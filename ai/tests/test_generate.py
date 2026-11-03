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
from ayna_ai.validate import NO_MATCH, load_step_schema

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
        self.bodies, self.timeouts = [], []

    def chat(self, body, timeout_s=None):
        self.bodies.append(body)
        self.timeouts.append(timeout_s)
        time.sleep(self.delay)
        if self.error:
            raise self.error
        return self.answer


def test_valid_output_returns_the_document_and_metrics(spike_objects):
    result = StepGenerator(FakeClient(reply(document()))).generate(TEXT, spike_objects)
    assert result.status is Status.OK and result.ok
    assert result.document == {"version": "0.1", "steps": STEPS}
    assert result.errors == [] and result.dropped == []
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
    assert (
        f"after the dash), or {NO_MATCH} if none of them fits:\n" in system["content"]
    )
    assert PROMPT_VERSION == "3"


def test_the_model_call_gets_the_callers_timeout(spike_objects):
    client = FakeClient(reply(document()))
    generator = StepGenerator(client)
    generator.generate(TEXT, spike_objects)
    generator.generate(TEXT, spike_objects, timeout_s=12.5)
    assert client.timeouts == [None, 12.5]


def test_the_reserved_name_is_not_an_object(spike_objects):
    client = FakeClient(reply(document()))
    with pytest.raises(ValueError, match="reserved"):
        StepGenerator(client).generate(TEXT, {**spike_objects, NO_MATCH: "yok"})
    assert client.bodies == []


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
    ("output", "error"),
    [
        (json.dumps({"steps": STEPS}), "$: 'version' is a required property"),
        (json.dumps({"version": "0.2", "steps": STEPS}), "$.version"),
        (json.dumps({"version": "0.1", "steps": STEPS[0]}), "$.steps"),
        (json.dumps({"version": "0.1", "steps": STEPS, "x": 1}), "$: Additional"),
        (json.dumps(STEPS), "$: "),
    ],
    ids=["no version", "wrong version", "steps not a list", "extra field", "a list"],
)
def test_an_answer_that_is_not_a_step_document_is_rejected_whole(
    spike_objects, output, error
):
    result = StepGenerator(FakeClient(reply(output))).generate(TEXT, spike_objects)
    assert result.status is Status.INVALID_SCHEMA
    assert result.document is None and result.dropped == []
    assert any(e.startswith(error) for e in result.errors), result.errors


@pytest.mark.parametrize(
    ("step", "code", "reason"),
    [
        (
            {"keyword": "Click", "target": "login.loginButton", "value": "x"},
            "invalid_step",
            "$.value: not allowed for this keyword",
        ),
        (
            {"keyword": "Type", "target": "login.userNameInput"},
            "invalid_step",
            "$: 'value' is a required property",
        ),
        (
            {"keyword": "Press", "target": "login.loginButton"},
            "unknown_keyword",
            "unknown keyword 'Press'",
        ),
        (
            {"keyword": "Click", "target": "settings.deleteAllButton"},
            "unknown_target",
            "'settings.deleteAllButton' is not in the object repository",
        ),
        (
            {"keyword": "Click", "target": "Login Button"},
            "unknown_target",
            "'Login Button' is not in the object repository",
        ),
        (
            {"keyword": "Click", "target": NO_MATCH},
            "no_match",
            "no repository object matches",
        ),
        (
            {"keyword": "Click"},
            "invalid_step",
            "$: 'target' is a required property",
        ),
        (
            {"keyword": "DoubleClick", "target": "login.forgotPasswordLink"},
            "unknown_keyword",
            (
                "unknown keyword 'DoubleClick'; 'login.forgotPasswordLink' is not "
                "in the object repository"
            ),
        ),
        ("Click login.loginButton", "invalid_step", "$: 'Click login.loginButton'"),
    ],
    ids=[
        "Click with value",
        "Type without value",
        "unknown keyword",
        "unknown target",
        "invalid logical name",
        "no match",
        "no target",
        "two problems",
        "not an object",
    ],
)
def test_a_bad_step_is_dropped_with_its_reason_and_the_rest_kept(
    spike_objects, step, code, reason
):
    steps = [STEPS[0], step, STEPS[1]]
    result = StepGenerator(FakeClient(reply(document(steps)))).generate(
        TEXT, spike_objects
    )
    assert result.status is Status.OK
    assert result.document == {"version": "0.1", "steps": STEPS}
    (dropped,) = result.dropped
    assert (dropped.index, dropped.code, dropped.step) == (1, code, step)
    assert dropped.reason.startswith(reason), dropped.reason
    assert result.errors == []


def test_when_every_step_is_dropped_nothing_is_suggested(spike_objects):
    steps = [
        {"keyword": "Click", "target": NO_MATCH},
        {"keyword": "Click", "target": "settings.deleteAllButton"},
    ]
    result = StepGenerator(FakeClient(reply(document(steps)))).generate(
        TEXT, spike_objects
    )
    assert result.status is Status.NO_VALID_STEPS and not result.ok
    assert result.document is None and result.reasons is None
    assert [(d.index, d.code) for d in result.dropped] == [
        (0, "no_match"),
        (1, "unknown_target"),
    ]
    assert result.errors == [
        "$.steps[0]: no repository object matches",
        "$.steps[1]: 'settings.deleteAllButton' is not in the object repository",
    ]


def test_an_answer_without_steps_has_no_valid_steps(spike_objects):
    result = StepGenerator(FakeClient(reply(document([])))).generate(
        TEXT, spike_objects
    )
    assert result.status is Status.NO_VALID_STEPS
    assert result.dropped == [] and result.errors == ["the answer has no steps"]
    assert result.step_limit_reached is False


# --- step limit (#142 review: a cap must not shorten an answer silently) -------


def steps_of(count: int) -> list[dict]:
    return [STEPS[i % 2] for i in range(count)]


def test_the_step_limit_is_the_grammars_max_items(spike_objects):
    client = FakeClient(reply(document()))
    generator = StepGenerator(client, GenerationSettings(max_steps=3))
    generator.generate(TEXT, spike_objects)
    assert generator.step_limit == 3
    assert client.bodies[0]["format"]["properties"]["steps"]["maxItems"] == 3
    assert StepGenerator(FakeClient()).step_limit == 12


@pytest.mark.parametrize(
    ("steps", "reached"),
    [
        (steps_of(2), False),
        (steps_of(3), True),
        # A dropped step counts: the model wrote it.
        ([*steps_of(2), {"keyword": "Click", "target": NO_MATCH}], True),
        # Longer than the grammar allows: the server ignored it, nothing was cut.
        (steps_of(4), False),
    ],
)
def test_an_answer_at_the_step_limit_is_flagged(spike_objects, steps, reached):
    generator = StepGenerator(
        FakeClient(reply(document(steps))), GenerationSettings(max_steps=3)
    )
    result = generator.generate(TEXT, spike_objects)
    assert result.ok
    assert result.step_limit_reached is reached
    assert result.to_dict()["step_limit_reached"] is reached


def test_every_step_dropped_at_the_limit_is_still_flagged(spike_objects):
    steps = [{"keyword": "Click", "target": NO_MATCH}] * 3
    generator = StepGenerator(
        FakeClient(reply(document(steps))), GenerationSettings(max_steps=3)
    )
    result = generator.generate(TEXT, spike_objects)
    assert result.status is Status.NO_VALID_STEPS
    assert result.step_limit_reached is True


def test_without_the_grammar_there_is_no_step_limit(spike_objects):
    generator = StepGenerator(
        FakeClient(reply(document(steps_of(12)))), GenerationSettings(format="json")
    )
    assert generator.step_limit is None
    assert generator.generate(TEXT, spike_objects).step_limit_reached is False


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
        assert record["step_limit_reached"] is False


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
    ("steps", "reason"),
    [
        ([REASONED[0], STEPS[1]], "reason: missing or empty"),
        (
            [REASONED[0], {**STEPS[1], "reason": "x" * 101}],
            "reason: longer than 100 characters",
        ),
    ],
    ids=["missing reason", "reason too long"],
)
def test_a_step_with_a_bad_reason_is_dropped(spike_objects, steps, reason):
    result = StepGenerator(
        FakeClient(reply(document(steps))), GenerationSettings(reasons=True)
    ).generate(TEXT, spike_objects)
    assert result.ok
    assert result.document["steps"] == [STEPS[0]]
    assert result.reasons == [REASONED[0]["reason"]]
    (dropped,) = result.dropped
    assert (dropped.index, dropped.code, dropped.reason) == (1, "invalid_step", reason)
    assert dropped.step == steps[1]  # as the model wrote it


def test_a_dropped_step_keeps_the_models_reason(spike_objects):
    steps = [REASONED[0], {**REASONED[1], "target": "login.forgotPasswordLink"}]
    result = StepGenerator(
        FakeClient(reply(document(steps))), GenerationSettings(reasons=True)
    ).generate(TEXT, spike_objects)
    assert result.reasons == [REASONED[0]["reason"]]
    assert result.dropped[0].step == steps[1]
    assert result.dropped[0].to_dict() == {
        "index": 1,
        "code": "unknown_target",
        "reason": "'login.forgotPasswordLink' is not in the object repository",
        "step": steps[1],
    }


def test_a_reason_without_reasons_enabled_drops_the_step(spike_objects):
    result = StepGenerator(FakeClient(reply(document(REASONED)))).generate(
        TEXT, spike_objects
    )
    assert result.status is Status.NO_VALID_STEPS
    assert {d.code for d in result.dropped} == {"invalid_step"}
    assert "'reason' was unexpected" in result.dropped[0].reason


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
    unknown = {"keyword": "Click", "target": "login.forgotPasswordLink"}
    serve(
        fake_ollama,
        [
            document(),
            document([{"keyword": "Wait", "target": "login.loginButton"}, unknown]),
        ],
    )
    out, log = tmp / "results.json", tmp / "latency.jsonl"
    argv = ["--input", str(inputs), "--objects", str(objects), "--out", str(out)]
    code = main(argv + ["--log", str(log), "--host", fake_ollama.url, "--note", "test"])

    # Scenario 2 keeps one valid step with the wrong keyword and drops one:
    # ok, but no keyword match.
    assert code == 0
    results = json.loads(out.read_text("utf-8"))
    summary = results["summary"]
    assert (summary["n"], summary["ok"], summary["ok_rate"]) == (2, 2, 1.0)
    assert summary["by_status"] == {"ok": 2}
    assert summary["keyword_match"] == 1
    assert summary["steps_dropped"] == 1
    assert summary["step_limit_reached"] == 0
    assert results["scenarios"][1]["dropped"] == [
        {
            "index": 1,
            "code": "unknown_target",
            "reason": "'login.forgotPasswordLink' is not in the object repository",
            "step": unknown,
        }
    ]
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
    assert [line["dropped"] for line in lines] == [0, 1]
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
