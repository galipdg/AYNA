"""Fills one application to the NFR-08 size through the REST API (#152).

1 application with 1 version, `--windows` imported window snapshots, `--objects` repository objects
spread over them and `--tests` tests of `--steps` steps each. Everything goes through the public
API, so the seed passes the same validation as real data and needs no Neo4j access.

    python3 seed.py --url http://127.0.0.1:18090 --out out/seed.json
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import time
import uuid
from datetime import UTC, datetime

from common import login, wait_until_up

CONTROL_TYPES = ("Button", "Edit", "CheckBox", "ComboBox", "Text")


def snapshot(window: int, controls: int) -> dict:
    """A window snapshot (`schemas/snapshot.schema.json` 0.1): the window element, then `controls` children."""
    title = f"Load Test Window {window}"
    handle = 100_000 + window
    elements = [
        {
            "id": "e0",
            "parentId": None,
            "element": {
                "automationId": f"win{window}",
                "name": title,
                "controlType": "Window",
                "className": "LoadTestWindow",
                "frameworkId": "WinForm",
                "bounds": [0, 0, 1280, 800],
                "dpi": 96,
                "siblingIndex": 0,
                "windowTitle": title,
                "enabled": True,
                "offscreen": False,
                "nativeWindowHandle": handle,
            },
        }
    ]
    for i in range(controls):
        control_type = CONTROL_TYPES[i % len(CONTROL_TYPES)]
        row, column = divmod(i, 10)
        elements.append(
            {
                "id": f"e{i + 1}",
                "parentId": "e0",
                "element": {
                    "automationId": f"control{i}",
                    "name": f"Control {window}-{i}",
                    "controlType": control_type,
                    "className": f"WindowsForms10.{control_type.upper()}",
                    "frameworkId": "WinForm",
                    "bounds": [20 + column * 120, 20 + row * 40, 130 + column * 120, 50 + row * 40],
                    "dpi": 96,
                    "parentPath": "Window",
                    "siblingIndex": i,
                    "nearestLabel": f"Label {i}",
                    "windowTitle": title,
                    "enabled": True,
                    "offscreen": False,
                },
            }
        )
    return {
        "version": "0.1",
        "snapshotId": str(uuid.uuid4()),
        "capture": {
            "startedAt": datetime.now(UTC).isoformat(timespec="seconds"),
            "durationMs": 100,
            "budgetMs": 5000,
            "elementCount": len(elements),
            "readErrors": 0,
            "agentVersion": "loadtest",
            "featureVersion": "features-v0",
        },
        "app": {"exeName": "loadtest.exe", "fileVersion": "1.0.0.0"},
        "window": {
            "handle": handle,
            "title": title,
            "className": "LoadTestWindow",
            "bounds": [0, 0, 1280, 800],
            "dpi": 96,
        },
        "elements": elements,
    }


def steps_for(test: int, objects: list[dict], count: int) -> list[dict]:
    """`count` steps over consecutive objects of one window, mixing the keywords a recorded test has."""
    steps = []
    start = (test * count) % len(objects)
    for i in range(count):
        target = objects[(start + i) % len(objects)]["name"]
        kind = i % 4
        if kind == 0:
            steps.append({"keyword": "Click", "target": target})
        elif kind == 1:
            steps.append({"keyword": "Type", "target": target, "value": f"value {test}-{i}"})
        elif kind == 2:
            steps.append({"keyword": "Wait", "target": target, "timeoutMs": 5000})
        else:
            steps.append(
                {
                    "keyword": "Verify",
                    "target": target,
                    "checkpoint": {"property": "enabled", "operator": "equals", "expected": True},
                }
            )
    return steps


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", default=os.environ.get("AYNA_SERVER_URL", "http://127.0.0.1:18090"))
    parser.add_argument("--username", default=os.environ.get("AYNA_LOADTEST_USERNAME", "loadtest"))
    parser.add_argument("--password", default=os.environ.get("AYNA_LOADTEST_PASSWORD", "loadtest-password"))
    parser.add_argument("--windows", type=int, default=10)
    parser.add_argument("--objects", type=int, default=1000, help="repository objects (NFR-08: at least 1 000)")
    parser.add_argument("--tests", type=int, default=500, help="tests (NFR-08: at least 500)")
    parser.add_argument("--steps", type=int, default=10, help="steps per test")
    parser.add_argument("--out", default="out/seed.json")
    args = parser.parse_args()

    wait_until_up(args.url)
    client = login(args.url, args.username, args.password)
    started = time.perf_counter()

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    app = client.call("POST", "/api/apps", {"name": f"Load test {stamp}", "technology": "WinForms"})
    version = client.call("POST", f"/api/apps/{app['id']}/versions", {"version": "1.0"})
    print(f"app {app['id']} version {version['id']}")

    per_window = -(-args.objects // args.windows)
    objects: list[dict] = []
    by_window: list[list[dict]] = []
    for w in range(args.windows):
        controls = min(per_window, args.objects - len(objects))
        if controls <= 0:
            break
        document = snapshot(w, controls)
        client.call("POST", f"/api/apps/{app['id']}/versions/{version['id']}/snapshots", document)
        window_objects = []
        for i in range(controls):
            element = document["elements"][i + 1]["element"]
            created = client.call(
                "POST",
                f"/api/apps/{app['id']}/repo-objects",
                {
                    "name": f"win{w}.control{i}",
                    "snapshotId": document["snapshotId"],
                    "snapshotElementId": f"e{i + 1}",
                    "primary": {"automationId": element["automationId"]},
                    "fallback": {"name": element["name"], "controlType": element["controlType"]},
                },
            )
            window_objects.append({"id": created["id"], "name": created["name"]})
        objects.extend(window_objects)
        by_window.append(window_objects)
        print(f"  window {w}: snapshot + {controls} objects ({len(objects)} in all)")

    tests = []
    for t in range(args.tests):
        created = client.call("POST", f"/api/apps/{app['id']}/tests", {"name": f"Load test case {t:03d}"})
        window_objects = by_window[t % len(by_window)]
        document = {"version": "0.2", "steps": steps_for(t, window_objects, args.steps)}
        client.call("PUT", f"/api/tests/{created['id']}/steps", document)
        tests.append(created["id"])
        if (t + 1) % 100 == 0:
            print(f"  {t + 1} tests")

    seconds = time.perf_counter() - started
    summary = client.call("GET", f"/api/apps/{app['id']}/repo-objects")
    listed_tests = client.call("GET", f"/api/apps/{app['id']}/tests")
    client.close()
    seed = {
        "url": args.url,
        "appId": app["id"],
        "appVersionId": version["id"],
        "objects": [o["id"] for o in objects],
        "tests": tests,
        "stepsPerTest": args.steps,
        "listed": {"repoObjects": len(summary), "tests": len(listed_tests)},
        "seconds": round(seconds, 1),
    }
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(seed, indent=2))
    print(f"seeded {len(summary)} repository objects and {len(listed_tests)} tests in {seconds:.0f} s -> {out}")
    if len(summary) < args.objects or len(listed_tests) < args.tests:
        raise SystemExit("the server lists fewer objects or tests than were created")


if __name__ == "__main__":
    main()
