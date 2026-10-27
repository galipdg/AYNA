"""Send the 10 spike inputs to a running AI service and report latency (#71).

From `ai/`, with `python -m ayna_ai.service` running:

    python spikes/service_check.py --out spikes/results/service-<date>-<model>.json

Prints each answer and a summary: HTTP 200 count, keyword-sequence matches,
client-side p50/p95/max latency in seconds.
"""

import argparse
import http.client
import json
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent


def call(port, method, path, body=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=180)
    headers = {"Content-Type": "application/json"} if body is not None else {}
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode()
    started = time.perf_counter()
    conn.request(method, path, data, headers)
    response = conn.getresponse()
    payload = json.loads(response.read())
    elapsed = time.perf_counter() - started
    conn.close()
    return response.status, payload, elapsed


def percentile(values, q):
    values = sorted(values)
    pos = (len(values) - 1) * q / 100
    lo = int(pos)
    hi = min(lo + 1, len(values) - 1)
    return values[lo] + (values[hi] - values[lo]) * (pos - lo)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8090)
    parser.add_argument("--model", help="model to ask for (default: the service's)")
    parser.add_argument("--input", type=Path, default=HERE / "llm-smoke-inputs.jsonl")
    parser.add_argument(
        "--objects", type=Path, default=HERE.parent / "tests/data/spike-objects.json"
    )
    parser.add_argument("--out", type=Path, help="results JSON")
    args = parser.parse_args()

    cases = [
        json.loads(line)
        for line in args.input.read_text("utf-8").splitlines()
        if line
    ]
    objects = json.loads(args.objects.read_text("utf-8"))
    objects = [{"name": k, "description": v} for k, v in objects.items()]

    code, health, _ = call(args.port, "GET", "/ai/health")
    print("health", code, json.dumps(health, ensure_ascii=False))

    rows = []
    for case in cases:
        body = {"text": case["text"], "app": "customer-records", "objects": objects}
        if args.model:
            body["model"] = args.model
        code, payload, elapsed = call(args.port, "POST", "/ai/generate-steps", body)
        keywords = [s["keyword"] for s in payload.get("steps", [])]
        rows.append(
            {
                "id": case["id"],
                "code": code,
                "status": payload["status"],
                "client_s": round(elapsed, 3),
                "latencyMs": payload.get("latencyMs"),
                "keywords": keywords,
                "expected": case["expected"],
                "keyword_match": keywords == case["expected"],
                "response": payload,
            }
        )
        print(f"#{case['id']} {code} {payload['status']} {elapsed:.2f}s {keywords}")
        for step in payload.get("steps", []):
            print("    ", json.dumps(step, ensure_ascii=False))
        for dropped in payload.get("dropped", []):
            print("    dropped", json.dumps(dropped, ensure_ascii=False))

    latencies = [r["client_s"] for r in rows]
    summary = {
        "n": len(rows),
        "http_200": sum(r["code"] == 200 for r in rows),
        "keyword_match": sum(r["keyword_match"] for r in rows),
        "steps_dropped": sum(len(r["response"].get("dropped", [])) for r in rows),
        "p50_s": round(percentile(latencies, 50), 2),
        "p95_s": round(percentile(latencies, 95), 2),
        "max_s": round(max(latencies), 2),
    }
    print(json.dumps(summary))
    if args.out:
        result = {"health": health, "summary": summary, "rows": rows}
        args.out.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", "utf-8"
        )


if __name__ == "__main__":
    main()
