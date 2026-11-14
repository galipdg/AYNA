"""NFR-12: how slow is the local model on Windows, where AYNA actually ships (#162).

Every latency the project has for the AI service comes from one MacBook M2 (#37, #71,
``ai/spikes/llm-smoke.md``), and the service's own 30 s deadline already fires there. This
drives **galip's harness rather than a copy of it**: ``ayna_ai.generate`` supplies the prompt,
the derived schema, the timing and the summary, so a number here is the service's number.
``ayna_ai`` needs only ``jsonschema``, which ``eval`` already depends on, so the
repository-root ``.venv`` runs this and no new dependency is added.

Two things the issue's body does not know, both of which change what the result means:

* Ollama was already installed on this machine.
* **This machine has a usable GPU** (RTX 3060 Laptop, 6 GB) and Ollama offloads most of an
  8B model to it. The closed-network box the requirement is about plausibly has none, so
  every configuration is run twice -- as Ollama chooses, and forced CPU-only -- and the pair
  is what gets reported. :class:`CpuOnly` is the whole of that difference.

Run it from the repository root, one configuration at a time, with the machine idle:

    .venv/Scripts/python.exe eval/llm-latency/run.py list
    .venv/Scripts/python.exe eval/llm-latency/run.py run cli-qwen-gpu
    .venv/Scripts/python.exe eval/llm-latency/run.py report

``run`` writes ``results/<id>-<stamp>.json`` and never overwrites one. Configurations are
grouped by offload on purpose: Ollama reloads the model whenever ``num_gpu`` changes, so an
interleaved matrix would charge half the runs a cold load.
"""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]

# By repository layout, exactly as `eval/rq1/measure.py` reaches `agent/`: `eval` installs no
# packages and does not depend on the AI service. Importing it is what makes this measure the
# product's own prompt, schema and timing instead of a second implementation of them.
if str(REPO / "ai") not in sys.path:
    sys.path.insert(0, str(REPO / "ai"))

from ayna_ai.generate import (
    DEFAULT_HOST,
    PROMPT_VERSION,
    GenerationSettings,
    StepGenerator,
    run_batch,
    summarize,
)
from ayna_ai.ollama import OllamaClient

AI = REPO / "ai"
INPUTS = AI / "spikes" / "llm-smoke-inputs.jsonl"
OBJECTS = AI / "tests" / "data" / "spike-objects.json"
RESULTS = HERE / "results"

#: The deadline the service ships with (`ServiceConfig.timeout_s`). Runs are measured with a
#: long timeout and this is applied afterwards: answering 504 at 30 s would censor exactly
#: the tail the issue asks about.
SERVICE_DEADLINE_S = 30.0

#: Long enough that a CPU-only run finishes rather than being cut off. A request that hits
#: even this is a finding, not a measurement.
RUN_TIMEOUT_S = 600.0


class CpuOnly(StepGenerator):
    """`StepGenerator` that asks Ollama to keep every layer on the CPU.

    ``options.num_gpu = 0`` is per request, so the prompt, the derived schema, the seed and
    the token caps stay byte-identical to the GPU run -- the offload is the only difference,
    which is the only way the pair is a comparison. The server-side ``OLLAMA_NUM_GPU`` would
    have needed `ollama serve` restarted, and would have applied to everything else on the
    machine.
    """

    def request_body(self, text: str, objects: Any) -> dict:
        body = super().request_body(text, objects)
        body["options"] = {**body["options"], "num_gpu": 0}
        return body


@dataclass(frozen=True)
class Config:
    """One row of the matrix."""

    id: str
    #: "cli" drives `ayna_ai.generate`; "http" drives a running `ayna_ai.service`.
    path: str
    model: str
    group: str
    why: str
    format: str = "schema"
    reasons: bool = False
    gpu: bool = True
    port: int = 8090


QWEN = "qwen3:8b"
GEMMA = "gemma4:e4b-it-qat"

# Grouped by offload, and within a group by what each run is for. The GPU group is what this
# laptop does; the CPU group is what a closed-network box without a GPU would do.
CONFIGS: tuple[Config, ...] = (
    # --- group A: as Ollama chooses (70 % of qwen3 on the RTX 3060 here)
    Config("cli-qwen-gpu", "cli", QWEN, "A-gpu", "the #37 number on this machine"),
    Config("cli-gemma-gpu", "cli", GEMMA, "A-gpu", "the second model, same path"),
    Config(
        "cli-qwen-gpu-json",
        "cli",
        QWEN,
        "A-gpu",
        "format baseline, as PR #142 compared",
        format="json",
    ),
    Config(
        "cli-qwen-gpu-reasons",
        "cli",
        QWEN,
        "A-gpu",
        "what reasons cost: same path, one flag",
        reasons=True,
    ),
    Config(
        "http-qwen-gpu", "http", QWEN, "A-gpu", "the service as shipped, reasons on"
    ),
    Config("http-gemma-gpu", "http", GEMMA, "A-gpu", "the service on the second model"),
    # --- group B: forced CPU-only, the box NFR-12 is actually about
    Config(
        "cli-qwen-cpu", "cli", QWEN, "B-cpu", "the closed-network number", gpu=False
    ),
    Config(
        "cli-gemma-cpu", "cli", GEMMA, "B-cpu", "the second model, CPU only", gpu=False
    ),
    Config(
        "cli-qwen-cpu-reasons",
        "cli",
        QWEN,
        "B-cpu",
        "what reasons cost where it hurts",
        reasons=True,
        gpu=False,
    ),
    Config("http-qwen-cpu", "http", QWEN, "B-cpu", "the service CPU only", gpu=False),
)

BY_ID = {config.id: config for config in CONFIGS}


# --------------------------------------------------------------------------- the machine


def nvidia_smi() -> str | None:
    """The GPU, or None when there is no `nvidia-smi` to ask."""
    for candidate in (
        str(Path(sys.prefix).anchor) + r"Windows\System32\nvidia-smi.exe",
        "nvidia-smi",
    ):
        try:
            out = subprocess.run(
                [
                    candidate,
                    "--query-gpu=name,memory.total,driver_version",
                    "--format=csv,noheader",
                ],
                capture_output=True,
                text=True,
                timeout=20,
                check=True,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        return out.stdout.strip()
    return None


def ollama_ps() -> list[dict[str, Any]]:
    """What Ollama has loaded, which is where the CPU/GPU split is readable."""
    try:
        with urllib.request.urlopen(f"{DEFAULT_HOST}/api/ps", timeout=10) as answer:
            return json.loads(answer.read()).get("models", [])
    except (urllib.error.URLError, OSError, ValueError):
        return []


def machine() -> dict[str, Any]:
    """SDD 6.7 wants the hardware beside the number, so it is stored in every run."""
    return {
        "platform": platform.platform(),
        "processor": platform.processor(),
        "python": platform.python_version(),
        "gpu": nvidia_smi(),
        "ollama_ps": ollama_ps(),
        "prompt_version": PROMPT_VERSION,
    }


def _system_times() -> tuple[int, int] | None:
    """`(idle, total)` 100 ns ticks across all CPUs, from `GetSystemTimes`."""
    if sys.platform != "win32":
        return None
    import ctypes
    from ctypes import wintypes

    idle, kernel, user = (wintypes.FILETIME() for _ in range(3))
    ok = ctypes.windll.kernel32.GetSystemTimes(
        ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)
    )
    if not ok:
        return None

    def ticks(value: wintypes.FILETIME) -> int:
        return (value.dwHighDateTime << 32) | value.dwLowDateTime

    # `kernel` already includes idle, so kernel + user is the whole wall time x CPUs.
    return ticks(idle), ticks(kernel) + ticks(user)


def busy_share(sample_s: float = 1.0) -> float | None:
    """Fraction of the machine busy over `sample_s`. None off Windows.

    Recorded before and after every run, because the Mac numbers were taken at load average
    4-6 and a comparison that does not say what the machine was doing flatters whichever
    side was quieter. `GetSystemTimes` through `ctypes` rather than a PowerShell one-liner:
    `powershell.exe` is not always on `PATH` of a process started from a POSIX shell here,
    and a measurement helper that silently returns None is worse than no helper.
    """
    first = _system_times()
    if first is None:
        return None
    time.sleep(sample_s)
    second = _system_times()
    if second is None:
        return None
    idle = second[0] - first[0]
    total = second[1] - first[1]
    if total <= 0:
        return None
    return round(1.0 - idle / total, 3)


# -------------------------------------------------------------------------------- running


def cases() -> list[dict[str, Any]]:
    """The same 10 Turkish sentences the Mac numbers were taken on (#7's spike inputs)."""
    return [
        json.loads(line)
        for line in INPUTS.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def objects() -> dict[str, str]:
    return json.loads(OBJECTS.read_text(encoding="utf-8"))


def run_cli(config: Config) -> list[dict[str, Any]]:
    """Drive `ayna_ai.generate` the way PR #142 did, in process."""
    client = OllamaClient(DEFAULT_HOST, RUN_TIMEOUT_S)
    settings = GenerationSettings(
        model=config.model, format=config.format, reasons=config.reasons
    )
    build = StepGenerator if config.gpu else CpuOnly
    generator = build(client, settings)
    # Pay the model load before the timed requests, as the spike did -- but print it, because
    # a cold load is minutes CPU-only and a first-request latency would otherwise hide it.
    started = time.perf_counter()
    generator.warm_up()
    print(f"warm-up {time.perf_counter() - started:.1f}s", flush=True)
    return run_batch(generator, cases(), objects())


def post(port: int, body: dict[str, Any]) -> tuple[int, dict[str, Any], float]:
    data = json.dumps(body, ensure_ascii=False).encode()
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/ai/generate-steps",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=RUN_TIMEOUT_S) as answer:
            payload = json.loads(answer.read())
            code = answer.status
    except urllib.error.HTTPError as exc:  # the service answers JSON on errors too
        payload = json.loads(exc.read())
        code = exc.code
    return code, payload, time.perf_counter() - started


def run_http(config: Config) -> list[dict[str, Any]]:
    """Drive a running `ayna_ai.service`, which is the path #78's panel will use.

    The service hard-codes ``reasons=True`` (`service.py:181`), so every HTTP row has reasons
    on; what reasons cost is measured on the CLI path instead, where it is one flag on the
    same code.
    """
    named = [{"name": name, "description": text} for name, text in objects().items()]
    rows = []
    for case in cases():
        body = {
            "text": case["text"],
            "app": "customer-records",
            "objects": named,
            "model": config.model,
        }
        code, payload, elapsed = post(config.port, body)
        keywords = [step["keyword"] for step in payload.get("steps", [])]
        rows.append(
            {
                "id": case.get("id"),
                "text": case["text"],
                "code": code,
                "status": payload.get("status"),
                "ok": code == 200 and payload.get("status") == "ok",
                "latency_s": round(elapsed, 3),
                "service_latency_ms": payload.get("latencyMs"),
                "keywords": keywords,
                "expected": case.get("expected"),
                "keyword_match": keywords == case.get("expected"),
                "reasons": payload.get("reasons"),
                "dropped": payload.get("dropped", []),
                "output_tokens": None,
                "step_limit_reached": False,
            }
        )
        print(
            f"#{case['id']} {code} {payload.get('status')} {elapsed:.2f}s {keywords}",
            flush=True,
        )
    return rows


def deadline_share(
    rows: list[dict[str, Any]], deadline_s: float = SERVICE_DEADLINE_S
) -> dict[str, Any]:
    """How many requests the shipped 30 s deadline would have turned into a 504.

    This is criterion 3, and it is computed rather than observed on purpose: the runs raise
    the timeout so that the tail exists to be measured at all.
    """
    latencies = [row["latency_s"] for row in rows]
    over = [value for value in latencies if value > deadline_s]
    return {
        "deadline_s": deadline_s,
        "over": len(over),
        "share": round(len(over) / len(latencies), 3) if latencies else None,
        "worst_s": round(max(latencies), 2) if latencies else None,
    }


def run_one(config: Config, note: str = "") -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M")
    path = RESULTS / f"{config.id}-{stamp}.json"
    if path.exists():
        raise SystemExit(f"{path} exists")
    print(f"=== {config.id}: {config.why}")
    print(
        f"    {config.path} · {config.model} · format={config.format} "
        f"· reasons={config.reasons} · gpu={config.gpu}"
    )
    before = busy_share()
    print(f"    machine busy before: {before}", flush=True)
    runner = run_cli if config.path == "cli" else run_http
    started = time.perf_counter()
    rows = runner(config)
    wall = time.perf_counter() - started
    summary = summarize(rows)
    summary["wall_s"] = round(wall, 1)
    summary["latency_mean_s"] = round(
        statistics.fmean(row["latency_s"] for row in rows), 2
    )
    result = {
        "config": asdict(config),
        "note": note,
        "finished_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "busy_before": before,
        "busy_after": busy_share(),
        "machine": machine(),
        "summary": summary,
        "deadline": deadline_share(rows),
        "rows": rows,
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(summary, ensure_ascii=False))
    print(json.dumps(result["deadline"], ensure_ascii=False))
    print(f"wrote {path.relative_to(REPO)}")
    return path


# ----------------------------------------------------------------------------- the report


def latest() -> dict[str, dict[str, Any]]:
    """The newest result per configuration id."""
    newest: dict[str, tuple[str, dict[str, Any]]] = {}
    for path in sorted(RESULTS.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        config_id = data["config"]["id"]
        if config_id not in newest or path.name > newest[config_id][0]:
            newest[config_id] = (path.name, data)
    return {config_id: data for config_id, (_, data) in newest.items()}


def report() -> int:
    """A markdown table per group, ready to paste into the issue."""
    found = latest()
    if not found:
        print(f"no results in {RESULTS}", file=sys.stderr)
        return 1
    for group in dict.fromkeys(config.group for config in CONFIGS):
        rows = [
            (config, found[config.id])
            for config in CONFIGS
            if config.group == group and config.id in found
        ]
        if not rows:
            continue
        print(f"\n### {group}\n")
        print(
            "| run | path | model | p50 s | p95 s | max s | ok | over 30 s | mean s |"
        )
        print("|---|---|---|---|---|---|---|---|---|")
        for config, data in rows:
            summary, deadline = data["summary"], data["deadline"]
            print(
                f"| `{config.id}` | {config.path} | {config.model} | "
                f"**{summary['latency_p50_s']}** | **{summary['latency_p95_s']}** | "
                f"{summary['latency_max_s']} | {summary['ok']}/{summary['n']} | "
                f"{deadline['over']}/{summary['n']} | {summary['latency_mean_s']} |"
            )
    missing = [config.id for config in CONFIGS if config.id not in found]
    if missing:
        print(f"\nNot run yet: {', '.join(missing)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="NFR-12 latency on Windows (#162).")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="the run matrix")
    one = sub.add_parser("run", help="run one configuration")
    one.add_argument("config", choices=sorted(BY_ID))
    one.add_argument("--note", default="", help="free text stored in the result")
    sub.add_parser("report", help="a markdown table per group from the newest results")
    args = parser.parse_args(argv)

    if args.command == "list":
        for group in dict.fromkeys(config.group for config in CONFIGS):
            print(f"{group}:")
            for config in CONFIGS:
                if config.group == group:
                    print(
                        f"  {config.id:<22} {config.path:<5} "
                        f"{config.model:<18} {config.why}"
                    )
        return 0
    if args.command == "report":
        return report()
    run_one(BY_ID[args.config], args.note)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
