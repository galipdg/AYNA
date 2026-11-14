"""Tests for the NFR-12 latency harness (#162).

Nothing here talks to a model: the point of these is the reporting logic and the one claim
the whole CPU-vs-GPU comparison rests on, which is that forcing CPU-only changes the request
and nothing else. The latencies themselves are measured by `ayna_ai`, which has its own tests.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import run


def test_forcing_cpu_only_changes_the_offload_and_nothing_else() -> None:
    """The pair of numbers is only a comparison while this holds.

    If `CpuOnly` also changed the prompt, the derived schema, the seed or the token caps,
    the GPU and CPU runs would differ in more than the offload and the ratio between them
    would mean nothing.
    """
    objects = run.objects()
    client = run.OllamaClient(run.DEFAULT_HOST, 5)
    settings = run.GenerationSettings()
    gpu = run.StepGenerator(client, settings).request_body("Giriş yap", objects)
    cpu = run.CpuOnly(client, settings).request_body("Giriş yap", objects)

    assert cpu["options"]["num_gpu"] == 0
    assert "num_gpu" not in gpu["options"]
    assert {key: value for key, value in cpu.items() if key != "options"} == {
        key: value for key, value in gpu.items() if key != "options"
    }
    assert {
        key: value for key, value in cpu["options"].items() if key != "num_gpu"
    } == gpu["options"]


def test_the_30_second_share_is_computed_from_the_recorded_latencies() -> None:
    """Criterion 3. Computed, not observed: the runs raise the timeout on purpose, so the
    tail exists to be counted at all."""
    rows = [{"latency_s": value} for value in (4.0, 12.0, 29.9, 30.1, 95.0)]
    share = run.deadline_share(rows)

    assert share["deadline_s"] == 30.0
    assert share["over"] == 2
    assert share["share"] == 0.4
    assert share["worst_s"] == 95.0


def test_a_latency_exactly_on_the_deadline_is_not_over_it() -> None:
    assert run.deadline_share([{"latency_s": 30.0}])["over"] == 0


def test_the_share_of_no_requests_is_empty_rather_than_zero() -> None:
    """Zero would read as "nothing timed out" on a run that never happened."""
    share = run.deadline_share([])
    assert share["over"] == 0
    assert share["share"] is None
    assert share["worst_s"] is None


def test_the_machine_busy_share_is_a_fraction_or_nothing() -> None:
    busy = run.busy_share(sample_s=0.05)
    assert busy is None or 0.0 <= busy <= 1.0


def test_every_configuration_has_a_unique_id_and_a_known_path() -> None:
    assert len(run.BY_ID) == len(run.CONFIGS)
    assert {config.path for config in run.CONFIGS} == {"cli", "http"}
    assert {config.model for config in run.CONFIGS} == {run.QWEN, run.GEMMA}


def test_both_offloads_are_measured_for_the_same_model_and_path() -> None:
    """The issue's premise is a box without a GPU, so a GPU-only matrix would not answer it."""
    pairs = {
        (config.path, config.model, config.format, config.reasons)
        for config in run.CONFIGS
        if config.gpu
    }
    cpu = {
        (config.path, config.model, config.format, config.reasons)
        for config in run.CONFIGS
        if not config.gpu
    }
    assert cpu and cpu <= pairs, (
        "every CPU-only run needs a GPU run to be compared with"
    )


def test_the_report_takes_the_newest_result_per_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(run, "RESULTS", tmp_path)
    for stamp, p50 in (("20261114-1000", 9.9), ("20261114-1200", 6.1)):
        (tmp_path / f"cli-qwen-gpu-{stamp}.json").write_text(
            json.dumps(
                {
                    "key": "cli-qwen-gpu",
                    "config": {"id": "cli-qwen-gpu", "path": "cli", "model": run.QWEN},
                    "summary": {"latency_p50_s": p50},
                    "deadline": {"over": 0},
                }
            ),
            encoding="utf-8",
        )

    found = run.latest()
    assert set(found) == {"cli-qwen-gpu"}
    assert found["cli-qwen-gpu"]["summary"]["latency_p50_s"] == 6.1


def test_the_report_says_which_configurations_have_not_been_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A half-finished matrix must not read as a finished one."""
    monkeypatch.setattr(run, "RESULTS", tmp_path)
    (tmp_path / "cli-qwen-gpu-20261114-1200.json").write_text(
        json.dumps(
            {
                "key": "cli-qwen-gpu",
                "config": {"id": "cli-qwen-gpu", "path": "cli", "model": run.QWEN},
                "summary": {
                    "latency_p50_s": 6.1,
                    "latency_p95_s": 9.0,
                    "latency_max_s": 9.4,
                    "latency_mean_s": 6.5,
                    "ok": 10,
                    "n": 10,
                },
                "deadline": {"over": 0},
            }
        ),
        encoding="utf-8",
    )

    assert run.report() == 0
    out = capsys.readouterr().out
    assert "cli-qwen-gpu" in out
    assert "Not run yet: cli-gemma-gpu" in out
    assert "cli-qwen-cpu" in out.split("Not run yet:")[1]


def test_reporting_nothing_is_an_error_not_an_empty_table(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(run, "RESULTS", tmp_path)
    assert run.report() == 1


def test_the_inputs_are_the_ten_sentences_the_mac_numbers_used() -> None:
    """A different input set would make the two platforms incomparable, which is the whole
    question the issue asks."""
    cases = run.cases()
    assert len(cases) == 10
    assert all("text" in case and "expected" in case for case in cases)
    assert run.INPUTS == run.AI / "spikes" / "llm-smoke-inputs.jsonl"


def test_the_cpu_only_warm_up_loads_the_thing_being_measured() -> None:
    """The inherited warm-up sends its own body and skips `request_body`.

    Without this override it warmed whichever offload Ollama already had loaded, and the
    first timed request paid for the reload -- an early `cli-qwen-cpu` run printed
    `warm-up 0.0s` beside a 34.5 s first request against a 15.3 s median.
    """
    sent: list[dict] = []

    class Recording:
        def chat(self, body: dict, timeout_s: float | None = None) -> dict:
            sent.append(body)
            return {"message": {"content": "{}"}}

    run.CpuOnly(Recording(), run.GenerationSettings()).warm_up()
    assert sent and sent[0]["options"]["num_gpu"] == 0


@pytest.mark.parametrize(
    ("gpu", "vram", "refused"),
    [
        (True, 4_000_000_000, False),
        (True, 0, True),  # Ollama reused a CPU-only runner: not the GPU number
        (False, 0, False),
        (False, 4_000_000_000, True),  # would publish a GPU number as the CPU one
        (True, None, False),  # not loaded: nothing to check, say so and carry on
    ],
)
def test_a_run_whose_offload_is_not_the_claimed_one_is_refused(
    monkeypatch: pytest.MonkeyPatch, gpu: bool, vram: int | None, refused: bool
) -> None:
    """The guard the whole GPU/CPU pair depends on.

    A CPU-only run that quietly got the GPU would be published as the closed-network number
    and be wrong by about a factor of three, and nothing else in the result file would show
    it -- `size_vram` is the only witness.
    """
    config = run.Config("probe", "cli", run.QWEN, "test", "", gpu=gpu)
    monkeypatch.setattr(run, "loaded_vram", lambda model: vram)
    if refused:
        with pytest.raises(SystemExit):
            run.check_offload(config)
    else:
        assert run.check_offload(config) == vram


def test_the_vram_of_a_model_that_is_not_loaded_is_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(run, "ollama_ps", lambda: [{"name": "other", "size_vram": 7}])
    assert run.loaded_vram(run.QWEN) is None


def test_an_under_load_run_does_not_replace_the_idle_run_it_is_read_against(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Idle and under load are two measurements of one configuration, not two versions of
    it, so they are keyed apart and reported in separate tables."""
    monkeypatch.setattr(run, "RESULTS", tmp_path)
    summary = {
        "latency_p50_s": 5.3,
        "latency_p95_s": 8.4,
        "latency_max_s": 9.2,
        "latency_mean_s": 5.5,
        "ok": 10,
        "n": 10,
    }
    config = {"id": "cli-qwen-gpu", "path": "cli", "model": run.QWEN}
    for key, load, stamp in (
        ("cli-qwen-gpu", 0, "20261114-1002"),
        ("cli-qwen-gpu+load8", 8, "20261114-1102"),
    ):
        (tmp_path / f"{key}-{stamp}.json").write_text(
            json.dumps(
                {
                    "key": key,
                    "config": config,
                    "load_workers": load,
                    "busy_before": 0.1 if not load else 0.55,
                    "summary": summary,
                    "deadline": {"over": 0},
                }
            ),
            encoding="utf-8",
        )

    assert set(run.latest()) == {"cli-qwen-gpu", "cli-qwen-gpu+load8"}
    assert run.report() == 0
    out = capsys.readouterr().out
    assert "A-gpu — idle" in out
    assert "under load — 8 busy processes" in out
    assert "cli-qwen-gpu+load8" in out.split("under load")[1]


def test_the_run_key_carries_the_load_and_nothing_else() -> None:
    assert run.run_key("cli-qwen-gpu", 0) == "cli-qwen-gpu"
    assert run.run_key("cli-qwen-gpu", 8) == "cli-qwen-gpu+load8"


def test_no_background_load_starts_no_processes() -> None:
    with run.background_load(0):
        pass


def test_a_background_load_actually_busies_the_machine_and_stops_after() -> None:
    with run.background_load(4):
        busy = run.busy_share(sample_s=1.0)
    assert busy is None or busy > 0.1, busy
    after = run.busy_share(sample_s=1.0)
    assert after is None or after < 0.95, after


@pytest.mark.parametrize("reasons", [False, True])
def test_the_recorded_prompt_version_says_whether_reasons_were_asked_for(
    reasons: bool,
) -> None:
    """A results file that does not distinguish the two prompts claims a comparability it
    does not have: reasons change the prompt, not just the token count."""
    config = run.Config("probe", "cli", run.QWEN, "test", "", reasons=reasons)
    recorded = run.machine(config)["prompt_version"]
    assert recorded.endswith("+reason") is reasons
    assert recorded.startswith(run.PROMPT_VERSION)
