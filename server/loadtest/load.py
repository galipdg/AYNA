"""Load test for NFR-07 under the load of NFR-08 (#152).

`--clients` threads (default 10) each log in with their own session, as ten AYNA clients would, and
repeat an editor session against the application `seed.py` filled: open the repository and the test
list, open tests and objects, save a test's steps, then run a test the way the client posts the
agent's results (create run, one result per step, finish, read it back). Nothing waits between
requests unless `--think-ms` says so, so this is the worst case of ten people working at once.

Requests made during the first `--warmup` seconds are not counted (the JVM is still compiling).
The report gives p50 / p95 / p99 per endpoint and the share of all requests answered within
`--limit-ms` (NFR-07: 95 % within 500 ms); a non-2xx answer counts as not answered in time.

    python3 load.py --seed out/seed.json --out-dir out
"""

from __future__ import annotations

import argparse
import json
import math
import os
import pathlib
import platform
import random
import subprocess
import threading
import time
from collections import defaultdict
from datetime import UTC, datetime

from common import Client, login

NFR_SHARE = 0.95


def percentile(sorted_values: list[float], p: float) -> float:
    """Nearest-rank percentile of an ascending list: the smallest value with at least p % at or below it."""
    if not sorted_values:
        return float("nan")
    rank = max(1, math.ceil(p / 100 * len(sorted_values)))
    return sorted_values[rank - 1]


class Recorder:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.samples: dict[str, list[float]] = defaultdict(list)
        self.late: dict[str, int] = defaultdict(int)
        self.errors: dict[str, list[str]] = defaultdict(list)
        self.counting = False

    def add(self, endpoint: str, seconds: float, status: int, detail: object, limit_s: float) -> None:
        if not self.counting:
            return
        ok = 200 <= status < 300
        with self.lock:
            self.samples[endpoint].append(seconds)
            # An error counts as not answered in time, whatever its time.
            if not ok or seconds > limit_s:
                self.late[endpoint] += 1
            if not ok:
                self.errors[endpoint].append(f"{status} {json.dumps(detail)[:200]}")


class SimulatedClient(threading.Thread):
    def __init__(self, index: int, args: argparse.Namespace, seed: dict, recorder: Recorder, stop: threading.Event):
        super().__init__(name=f"client-{index}", daemon=True)
        self.index = index
        self.args = args
        self.seed = seed
        self.recorder = recorder
        self.stop = stop
        self.random = random.Random(index)
        # Writes and runs touch only this client's own tests, as two people rarely edit one test at once.
        self.own_tests = seed["tests"][index :: args.clients]
        self.iterations = 0
        self.failure: str | None = None

    def timed(self, client: Client, endpoint: str, method: str, path: str, body: object | None = None):
        response = client.request(method, path, body)
        self.recorder.add(endpoint, response.seconds, response.status, response.body, self.args.limit_ms / 1000)
        if not 200 <= response.status < 300:
            return None
        return response.body

    def pause(self) -> None:
        if self.args.think_ms:
            time.sleep(self.random.uniform(0.5, 1.5) * self.args.think_ms / 1000)

    def session(self, client: Client) -> None:
        seed = self.seed
        app = seed["appId"]
        self.timed(client, "GET /api/apps/{appId}/repo-objects", "GET", f"/api/apps/{app}/repo-objects")
        self.pause()
        self.timed(client, "GET /api/apps/{appId}/tests", "GET", f"/api/apps/{app}/tests")
        self.pause()
        for _ in range(2):
            test = self.random.choice(seed["tests"])
            self.timed(client, "GET /api/tests/{testId}", "GET", f"/api/tests/{test}")
            self.pause()
        for _ in range(3):
            obj = self.random.choice(seed["objects"])
            self.timed(client, "GET /api/repo-objects/{objectId}", "GET", f"/api/repo-objects/{obj}")
            self.pause()

        # Edit and save one of this client's tests: change the text of its first Type step.
        test = self.random.choice(self.own_tests)
        current = self.timed(client, "GET /api/tests/{testId}", "GET", f"/api/tests/{test}")
        self.pause()
        if current is not None:
            document = current["document"]
            for step in document["steps"]:
                if step["keyword"] == "Type":
                    step["value"] = f"edited by {self.name} #{self.iterations}"
                    break
            self.timed(client, "PUT /api/tests/{testId}/steps", "PUT", f"/api/tests/{test}/steps", document)
            self.pause()

        # Run it: the client posts each step's result as the agent reports it, then finishes the run.
        run = self.timed(
            client, "POST /api/runs", "POST", "/api/runs", {"testId": test, "appVersionId": seed["appVersionId"]}
        )
        if run is None:
            return
        for index, step in enumerate(run["document"]["steps"]):
            result = {
                "runId": run["id"],
                "stepIndex": index,
                "stepId": step["id"],
                "status": "passed",
                "durationMs": self.random.randint(50, 400),
            }
            self.timed(
                client,
                "PUT /api/runs/{runId}/results/{stepIndex}",
                "PUT",
                f"/api/runs/{run['id']}/results/{index}",
                result,
            )
        self.timed(
            client, "POST /api/runs/{runId}/finish", "POST", f"/api/runs/{run['id']}/finish", {"status": "passed"}
        )
        self.pause()
        self.timed(client, "GET /api/runs/{runId}", "GET", f"/api/runs/{run['id']}")
        self.timed(client, "GET /api/tests/{testId}/runs", "GET", f"/api/tests/{test}/runs")
        self.pause()

    def run(self) -> None:
        try:
            client = login(self.args.url, self.args.username, self.args.password)
            while not self.stop.is_set():
                self.session(client)
                self.iterations += 1
            client.close()
        except Exception as exc:  # noqa: BLE001 - reported in the summary, the other clients go on
            self.failure = f"{type(exc).__name__}: {exc}"


def command(*argv: str) -> str | None:
    try:
        return subprocess.run(argv, capture_output=True, text=True, timeout=10, check=True).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def machine() -> dict:
    info = {
        "os": platform.platform(),
        "machine": platform.machine(),
        "logicalCpus": os.cpu_count(),
        "python": platform.python_version(),
    }
    if platform.system() == "Darwin":
        info["cpu"] = command("sysctl", "-n", "machdep.cpu.brand_string")
        memsize = command("sysctl", "-n", "hw.memsize")
        info["memoryGiB"] = round(int(memsize) / 2**30, 1) if memsize else None
    elif platform.system() == "Linux":
        model = command("sh", "-c", "grep -m1 'model name' /proc/cpuinfo | cut -d: -f2")
        info["cpu"] = model.strip() if model else None
    else:
        info["cpu"] = platform.processor()
    docker = command("docker", "info", "--format", "{{.NCPU}} {{.MemTotal}} {{.ServerVersion}}")
    if docker:
        cpus, mem, version = docker.split()
        info["docker"] = {"cpus": int(cpus), "memoryGiB": round(int(mem) / 2**30, 1), "version": version}
    return info


def summarise(recorder: Recorder, seconds: float, limit_ms: float) -> dict:
    """Per-endpoint and overall latency; `withinLimitShare` is the share of 2xx answers within `limit_ms`."""
    endpoints = []
    total = within = errors = 0
    everything: list[float] = []
    for endpoint in sorted(recorder.samples):
        values = sorted(recorder.samples[endpoint])
        failed = len(recorder.errors[endpoint])
        total += len(values)
        within += len(values) - recorder.late[endpoint]
        errors += failed
        everything.extend(values)
        endpoints.append(
            {
                "endpoint": endpoint,
                "count": len(values),
                "errors": failed,
                "overLimit": recorder.late[endpoint],
                "p50Ms": round(percentile(values, 50) * 1000, 1),
                "p95Ms": round(percentile(values, 95) * 1000, 1),
                "p99Ms": round(percentile(values, 99) * 1000, 1),
                "maxMs": round(values[-1] * 1000, 1),
                "errorSamples": recorder.errors[endpoint][:3],
            }
        )
    everything.sort()
    share = within / total if total else 0.0
    return {
        "endpoints": endpoints,
        "overall": {
            "requests": total,
            "errors": errors,
            "requestsPerSecond": round(total / seconds, 1) if seconds else None,
            "p50Ms": round(percentile(everything, 50) * 1000, 1),
            "p95Ms": round(percentile(everything, 95) * 1000, 1),
            "p99Ms": round(percentile(everything, 99) * 1000, 1),
            "withinLimitShare": round(share, 4),
            "limitMs": limit_ms,
            "nfr07Met": total > 0 and share >= NFR_SHARE,
        },
    }


def markdown(report: dict) -> str:
    o = report["overall"]
    s = report["settings"]
    m = report["machine"]
    lines = [
        f"# Load test {report['startedAt']}",
        "",
        f"- Load: {s['clients']} clients, think time {s['thinkMs']} ms, {s['durationS']} s measured after {s['warmupS']} s warm-up",
        (
            f"- Data: {report['seed']['listed']['repoObjects']} repository objects, {report['seed']['listed']['tests']} tests "
            f"of {report['seed']['stepsPerTest']} steps in one application"
        ),
        f"- Machine: {m.get('cpu')}, {m.get('logicalCpus')} logical CPUs, {m.get('memoryGiB')} GiB, {m.get('os')}",
    ]
    if m.get("docker"):
        d = m["docker"]
        lines.append(
            f"- Docker: {d['cpus']} CPUs, {d['memoryGiB']} GiB for server and Neo4j together (Docker {d['version']})"
        )
    verdict = "met" if o["nfr07Met"] else "not met"
    lines += [
        "",
        (
            f"**NFR-07 {verdict}**: {o['withinLimitShare'] * 100:.1f} % of {o['requests']} requests answered within "
            f"{o['limitMs']:.0f} ms (needs 95 %); {o['errors']} errors; {o['requestsPerSecond']} requests/s; "
            f"overall p50 {o['p50Ms']} ms, p95 {o['p95Ms']} ms, p99 {o['p99Ms']} ms."
        ),
        "",
        "| Endpoint | Requests | Errors | p50 ms | p95 ms | p99 ms | max ms |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for e in report["endpoints"]:
        lines.append(
            f"| `{e['endpoint']}` | {e['count']} | {e['errors']} | {e['p50Ms']} | {e['p95Ms']} | {e['p99Ms']} | {e['maxMs']} |"
        )
    if report["clientFailures"]:
        lines += ["", "Clients that stopped early:", *[f"- {f}" for f in report["clientFailures"]]]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seed", default="out/seed.json", help="the file seed.py wrote")
    parser.add_argument("--url", help="server URL (default: the one in the seed file)")
    parser.add_argument("--username", default=os.environ.get("AYNA_LOADTEST_USERNAME", "loadtest"))
    parser.add_argument("--password", default=os.environ.get("AYNA_LOADTEST_PASSWORD", "loadtest-password"))
    parser.add_argument("--clients", type=int, default=10, help="concurrent clients (NFR-08: at least 10)")
    parser.add_argument("--duration", type=float, default=120, help="seconds measured")
    parser.add_argument("--warmup", type=float, default=20, help="seconds run first and not counted")
    parser.add_argument("--think-ms", type=float, default=0, help="mean pause between a client's requests")
    parser.add_argument("--limit-ms", type=float, default=500, help="NFR-07 limit")
    parser.add_argument("--out-dir", default="out")
    args = parser.parse_args()

    seed = json.loads(pathlib.Path(args.seed).read_text())
    args.url = args.url or seed["url"]
    if len(seed["tests"]) < args.clients:
        raise SystemExit("fewer tests than clients; seed more tests")

    recorder = Recorder()
    stop = threading.Event()
    clients = [SimulatedClient(i, args, seed, recorder, stop) for i in range(args.clients)]
    started_at = datetime.now(UTC)
    for c in clients:
        c.start()
    print(f"{args.clients} clients started; warming up for {args.warmup:.0f} s")
    time.sleep(args.warmup)
    recorder.counting = True
    measure_start = time.perf_counter()
    print(f"measuring for {args.duration:.0f} s")
    time.sleep(args.duration)
    recorder.counting = False
    measured = time.perf_counter() - measure_start
    stop.set()
    for c in clients:
        c.join(timeout=60)

    report = {
        "startedAt": started_at.isoformat(timespec="seconds"),
        "settings": {
            "clients": args.clients,
            "durationS": args.duration,
            "warmupS": args.warmup,
            "thinkMs": args.think_ms,
            "url": args.url,
        },
        "seed": {k: seed[k] for k in ("listed", "stepsPerTest", "seconds")},
        "machine": machine(),
        "iterations": sum(c.iterations for c in clients),
        "clientFailures": [f"{c.name}: {c.failure}" for c in clients if c.failure],
        **summarise(recorder, measured, args.limit_ms),
    }
    out_dir = pathlib.Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = started_at.strftime("%Y%m%d-%H%M%S")
    (out_dir / f"load-{stamp}.json").write_text(json.dumps(report, indent=2))
    text = markdown(report)
    (out_dir / f"load-{stamp}.md").write_text(text)
    print()
    print(text)
    print(f"written to {out_dir}/load-{stamp}.json and .md")
    if report["clientFailures"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
