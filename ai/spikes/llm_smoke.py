"""Smoke test for local LLMs: Turkish sentences -> JSON test steps (#7).

Talks only to a local Ollama server and uses the standard library only.

Usage:
    python3 ai/spikes/llm_smoke.py --model qwen3:8b --model gemma4:e4b-it-qat
    python3 ai/spikes/llm_smoke.py --model qwen3:8b --note "wifi off"
"""

from __future__ import annotations

import argparse
import json
import platform
import re
import statistics
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
SCHEMA = json.loads((HERE / "step-spike.schema.json").read_text(encoding="utf-8"))
INPUTS = HERE / "llm-smoke-inputs.jsonl"
LOOPBACK = {"127.0.0.1", "localhost", "::1"}

# Fake object repository of a small customer-records app. It stands in for
# real repository grounding (C1) until retrieval exists (#57).
OBJECTS = {
    "login.userNameInput": "Kullanıcı adı alanı",
    "login.passwordInput": "Şifre alanı",
    "login.loginButton": "Giriş butonu",
    "login.errorLabel": "Giriş hata mesajı",
    "main.statusLabel": "Ana ekran durum etiketi",
    "main.newCustomerButton": "Yeni müşteri butonu",
    "main.searchInput": "Arama kutusu",
    "main.searchButton": "Ara butonu",
    "main.customerGrid": "Müşteri tablosu",
    "customer.nameInput": "Ad alanı",
    "customer.surnameInput": "Soyad alanı",
    "customer.cityCombo": "Şehir listesi",
    "customer.typeCombo": "Müşteri tipi listesi",
    "customer.saveButton": "Kaydet butonu",
    "customer.cancelButton": "İptal butonu",
    "dialog.messageLabel": "Bilgi penceresindeki mesaj",
    "dialog.okButton": "Bilgi penceresindeki Tamam butonu",
}

SYSTEM_PROMPT = f"""You turn Turkish test instructions for a Windows desktop app into test steps.
Answer with JSON only: {{"steps": [{{"keyword": ..., "target": ..., "value": ...}}]}}.

Keywords:
- Click: press a button. value = "".
- Type: enter text into a field. value = the text.
- Select: choose an item in a list. value = the item.
- Verify: check the text of an element. value = the expected text ("" for empty).
- Wait: wait until an element appears. value = timeout in seconds.

target must be one of these object names (Turkish description after the dash):
{chr(10).join(f"- {name} — {desc}" for name, desc in OBJECTS.items())}

Keep the order of the actions in the instruction. Add no steps it does not ask for."""


def schema_errors(value: object, schema: dict, path: str = "$") -> list[str]:
    """Validate the JSON Schema subset used by step-spike.schema.json."""
    types = {"object": dict, "array": list, "string": str}
    if "type" in schema and not isinstance(value, types[schema["type"]]):
        return [f"{path}: expected {schema['type']}"]
    errors = []
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: {value!r} not in enum")
    if isinstance(value, str) and len(value) < schema.get("minLength", 0):
        errors.append(f"{path}: shorter than {schema['minLength']}")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{path}: fewer than {schema['minItems']} items")
        for i, item in enumerate(value):
            errors += schema_errors(item, schema["items"], f"{path}[{i}]")
    if isinstance(value, dict):
        props = schema.get("properties", {})
        errors += [f"{path}: missing {k}" for k in schema.get("required", []) if k not in value]
        if schema.get("additionalProperties") is False:
            errors += [f"{path}: unexpected {k}" for k in value if k not in props]
        for key, sub in props.items():
            if key in value:
                errors += schema_errors(value[key], sub, f"{path}.{key}")
    return errors


def call(host: str, path: str, body: dict | None = None) -> dict:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        host + path, data=data, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=600) as resp:
        return json.load(resp)


def chat(host: str, model: str, text: str) -> dict:
    return call(
        host,
        "/api/chat",
        {
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            "format": SCHEMA,
            "stream": False,
            "think": False,
            "options": {"temperature": 0, "seed": 42, "num_ctx": 4096},
        },
    )


def loaded_size_mb(host: str, model: str) -> float | None:
    """Memory Ollama reports for the loaded model (weights + KV cache + buffers)."""
    for m in call(host, "/api/ps").get("models", []):
        if model in (m.get("name"), m.get("model")):
            return round(m["size"] / 2**20)
    return None


def runner_rss_mb() -> float | None:
    """Resident memory of Ollama's runner processes, in MB.

    RSS, not the macOS footprint: the weights are mmap'd and Metal wraps the
    mapping, so the footprint misses them while RSS counts the resident pages.
    """
    if sys.platform == "win32":
        return None
    out = subprocess.run(["ps", "-axo", "rss=,comm="], capture_output=True, text=True).stdout
    total_kb = 0
    for line in out.splitlines():
        rss, _, comm = line.strip().partition(" ")
        if re.search(r"llama-server|ollama", comm):
            total_kb += int(rss)
    return round(total_kb / 1024)


def score(case: dict, content: str) -> dict:
    result = {
        "json_ok": False,
        "schema_errors": [],
        "keywords": [],
        "keyword_match": False,
        "ungrounded": [],
    }
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        result["schema_errors"] = [f"invalid JSON: {exc}"]
        return result
    result["json_ok"] = True
    result["schema_errors"] = schema_errors(parsed, SCHEMA)
    if not result["schema_errors"]:
        steps = parsed["steps"]
        result["keywords"] = [s["keyword"] for s in steps]
        result["ungrounded"] = [s["target"] for s in steps if s["target"] not in OBJECTS]
    result["keyword_match"] = result["keywords"] == case["expected"]
    return result


def run_model(host: str, model: str, cases: list[dict]) -> dict:
    responses, rss_samples = [], []
    for case in cases:
        started = time.perf_counter()
        reply = chat(host, model, case["text"])
        wall_s = time.perf_counter() - started
        content = reply["message"]["content"]
        responses.append(
            {
                "id": case["id"],
                "text": case["text"],
                "expected": case["expected"],
                "output": content,
                **score(case, content),
                "wall_s": round(wall_s, 2),
                "load_s": round(reply.get("load_duration", 0) / 1e9, 2),
                "prompt_tokens": reply.get("prompt_eval_count"),
                "prompt_tps": tps(reply.get("prompt_eval_count"), reply.get("prompt_eval_duration")),
                "gen_tokens": reply.get("eval_count"),
                "gen_tps": tps(reply.get("eval_count"), reply.get("eval_duration")),
            }
        )
        rss_samples.append(runner_rss_mb())
        print(f"  {model} #{case['id']}: {responses[-1]['keywords']} ({wall_s:.1f}s)", flush=True)
    size_mb = loaded_size_mb(host, model)
    call(host, "/api/generate", {"model": model, "keep_alive": 0})  # unload before the next model
    rss_samples = [s for s in rss_samples if s is not None]
    return {
        "model": model,
        "summary": {
            "n": len(responses),
            "json_valid": sum(r["json_ok"] for r in responses),
            "schema_valid": sum(r["json_ok"] and not r["schema_errors"] for r in responses),
            "keyword_match": sum(r["keyword_match"] for r in responses),
            "all_targets_grounded": sum(
                r["json_ok"] and not r["schema_errors"] and not r["ungrounded"] for r in responses
            ),
            "gen_tps_median": median([r["gen_tps"] for r in responses]),
            "prompt_tps_median": median([r["prompt_tps"] for r in responses]),
            "wall_s_median": median([r["wall_s"] for r in responses]),
            "first_load_s": responses[0]["load_s"] if responses else None,
            "ollama_loaded_size_mb": size_mb,
            "runner_rss_peak_mb": max(rss_samples) if rss_samples else None,
        },
        "responses": responses,
    }


def tps(count: int | None, duration_ns: int | None) -> float | None:
    return round(count / (duration_ns / 1e9), 1) if count and duration_ns else None


def median(values: list[float | None]) -> float | None:
    values = [v for v in values if v is not None]
    return round(statistics.median(values), 1) if values else None


def sysctl(key: str) -> str:
    return subprocess.run(["sysctl", "-n", key], capture_output=True, text=True).stdout.strip()


def machine(host: str) -> dict:
    info = {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "ollama": call(host, "/api/version").get("version"),
    }
    if sys.platform == "darwin":
        info["cpu"] = sysctl("machdep.cpu.brand_string")
        info["ram_gb"] = int(sysctl("hw.memsize")) // 2**30
    return info


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model", action="append", required=True, help="Ollama model tag; repeat")
    parser.add_argument("--host", default="http://127.0.0.1:11434")
    parser.add_argument("--note", default="", help="free text stored in the results, e.g. 'wifi off'")
    parser.add_argument("--out", type=Path, help="results JSON (default: ai/spikes/results/...)")
    args = parser.parse_args()

    if urlparse(args.host).hostname not in LOOPBACK:
        sys.exit("Only a local Ollama server is allowed (closed network).")

    cases = [json.loads(line) for line in INPUTS.read_text(encoding="utf-8").splitlines() if line]
    started = datetime.now().astimezone()
    results = {
        "started": started.isoformat(timespec="seconds"),
        "note": args.note,
        "machine": machine(args.host),
        "models": [run_model(args.host, model, cases) for model in args.model],
    }

    out = args.out or HERE / "results" / f"llm-smoke-{started:%Y%m%d-%H%M}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"\nResults: {out}")
    for entry in results["models"]:
        print(entry["model"], json.dumps(entry["summary"]))


if __name__ == "__main__":
    main()
