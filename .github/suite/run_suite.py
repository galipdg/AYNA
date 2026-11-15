"""Run a suite file against the sample app and write JUnit XML (#67).

A stand-in for `ayna run --from-file suite.json --junit out.xml` until the CLI exists (#61,
#66, hasan's `agent/ayna_cli/`). It plays the steps with the agent's own playback
(`UiaDesktop.run_steps`), so what it checks is what the product does; only the suite file, the
app start and the XML are its own. When the CLI lands, `ayna-suite.yml` calls the CLI and this
file goes.

Per test: start the app with the test's `launch` arguments (plus `--app-arg`s, e.g. `--bug`),
find its window by ClassName, play the steps, stop the app. One app per test, so a test never
starts on the screen the previous one left behind.

Exit codes follow the CLI's (RS FR-23): 0 every test as expected, 1 a test failed (or passed
although `--expect-failed` named it), 2 the suite could not be run at all.

Only `windows_player` needs Windows; everything else is tested on any OS
(`test_run_suite.py`).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

#: A cold PySide6 import on a CI runner; the wait ends as soon as the window is there.
WINDOW_TIMEOUT_S = 60.0


class SuiteError(Exception):
    """The suite file cannot be read, or the app cannot be started: exit code 2."""


@dataclass
class TestOutcome:
    name: str
    scenario: str | None
    status: str  # "passed" | "failed" | "error"
    duration_s: float
    steps: list[dict[str, Any]] = field(default_factory=list)
    message: str | None = None

    @property
    def failing_step(self) -> dict[str, Any] | None:
        return next((s for s in self.steps if s.get("status") == "failed"), None)


#: `(test) -> step results`, as `UiaDesktop.run_steps` returns them.
Player = Callable[[Mapping[str, Any]], list[dict[str, Any]]]


def load_suite(path: Path) -> dict[str, Any]:
    try:
        suite = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SuiteError(f"{path}: {exc}") from exc
    tests = suite.get("tests") if isinstance(suite, dict) else None
    if not isinstance(tests, list) or not tests:
        raise SuiteError(f"{path}: a suite needs a non-empty `tests` list")
    names = set()
    for index, test in enumerate(tests):
        for key in ("name", "launch", "window", "targets", "steps"):
            if key not in test:
                raise SuiteError(f"{path}: test {index} has no `{key}`")
        if test["name"] in names:
            raise SuiteError(f"{path}: two tests are named {test['name']!r}")
        names.add(test["name"])
    return suite


def run_suite(
    suite: Mapping[str, Any],
    play: Player,
    clock: Callable[[], float] = time.monotonic,
) -> list[TestOutcome]:
    outcomes = []
    for test in suite["tests"]:
        started = clock()
        try:
            steps = play(test)
        except SuiteError:
            raise
        except Exception as exc:  # noqa: BLE001 -- one broken test must not hide the rest
            outcomes.append(
                TestOutcome(
                    test["name"],
                    test.get("scenario"),
                    "error",
                    clock() - started,
                    message=f"{type(exc).__name__}: {exc}",
                )
            )
            continue
        passed = bool(steps) and all(s.get("status") == "passed" for s in steps)
        outcomes.append(
            TestOutcome(
                test["name"],
                test.get("scenario"),
                "passed" if passed else "failed",
                clock() - started,
                steps,
            )
        )
    return outcomes


def exit_code(outcomes: Sequence[TestOutcome], expect_failed: Sequence[str]) -> int:
    """0 when every test did what was expected of it, else 1.

    A test named in `expect_failed` must *fail* (a step failed, not an error starting the
    app): that is how the job proves a bug-injected build is caught.
    """
    for outcome in outcomes:
        wanted = "failed" if outcome.name in expect_failed else "passed"
        if outcome.status != wanted:
            return 1
    return 0


def _step_line(step: Mapping[str, Any], source: Mapping[str, Any] | None) -> str:
    what = ""
    if source:
        what = f"{source.get('keyword')} {source.get('target')}"
    text = f"step {step.get('stepIndex')} {what}: {step.get('status')}"
    if step.get("message"):
        text += f" -- {step['message']}"
    return text


def junit_xml(suite: Mapping[str, Any], outcomes: Sequence[TestOutcome]) -> bytes:
    """One <testsuite>, one <testcase> per test; a failed step becomes its <failure>."""
    name = suite.get("suite", "suite")
    root = ET.Element("testsuites", name=name)
    element = ET.SubElement(
        root,
        "testsuite",
        name=name,
        tests=str(len(outcomes)),
        failures=str(sum(o.status == "failed" for o in outcomes)),
        errors=str(sum(o.status == "error" for o in outcomes)),
        skipped="0",
        time=f"{sum(o.duration_s for o in outcomes):.3f}",
    )
    sources = {t["name"]: t["steps"].get("steps", []) for t in suite["tests"]}
    for outcome in outcomes:
        case = ET.SubElement(
            element,
            "testcase",
            name=outcome.name,
            classname=f"{name}.{outcome.scenario or 'test'}",
            time=f"{outcome.duration_s:.3f}",
        )
        own = sources.get(outcome.name, [])
        lines = [
            _step_line(s, own[s["stepIndex"]] if s.get("stepIndex", -1) < len(own) else None)
            for s in outcome.steps
        ]
        if outcome.status == "failed":
            failing = outcome.failing_step
            message = (failing or {}).get("message") or "no step failed, but not every step passed"
            ET.SubElement(case, "failure", message=message, type="stepFailed").text = "\n".join(lines)
        elif outcome.status == "error":
            ET.SubElement(case, "error", message=outcome.message or "", type="runError")
        if lines:
            ET.SubElement(case, "system-out").text = "\n".join(lines)
    ET.indent(root)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True) + b"\n"


def summary_markdown(
    suite: Mapping[str, Any],
    outcomes: Sequence[TestOutcome],
    expect_failed: Sequence[str],
    build: str,
) -> str:
    """For `$GITHUB_STEP_SUMMARY`: the results on the run's page, with no reporter action."""
    icon = {"passed": "✅", "failed": "❌", "error": "⚠️"}
    lines = [
        f"### AYNA suite `{suite.get('suite', 'suite')}` on the sample app ({build})",
        "",
        "| Test | Scenario | Result | Expected | Time | Failing step |",
        "|---|---|---|---|---|---|",
    ]
    for o in outcomes:
        wanted = "failed" if o.name in expect_failed else "passed"
        failing = o.failing_step
        detail = o.message or ""
        if failing:
            detail = f"step {failing.get('stepIndex')}: {failing.get('message', '')}"
        detail = detail.replace("|", "\\|")
        lines.append(
            f"| {o.name} | {o.scenario or ''} | {icon[o.status]} {o.status} | {wanted} "
            f"| {o.duration_s:.1f} s | {detail} |"
        )
    return "\n".join(lines) + "\n"


# --- Windows: start the app, find its window, play ---------------------------------------


def windows_player(app: Path, app_args: Sequence[str]) -> tuple[Player, Callable[[], None]]:
    """A player that drives the real app through the agent's UI Automation backend."""
    try:
        from ayna_agent.recognition.uia import UiaDesktop
    except ImportError as exc:
        raise SuiteError(f"the agent is not installed (pip install -e ./agent): {exc}") from exc

    desktop = UiaDesktop()
    desktop.setup()
    if not desktop._ready:
        raise SuiteError(f"no UI Automation here: {desktop._unavailable}")

    def windows_of(class_name: str) -> list[dict[str, Any]]:
        return [w for w in desktop.list_windows() if w.get("className") == class_name]

    def play(test: Mapping[str, Any]) -> list[dict[str, Any]]:
        class_name = test["window"]["className"]
        if windows_of(class_name):
            raise SuiteError(f"a {class_name} window is already open before the test starts")
        env = dict(os.environ)
        env.pop("QT_QPA_PLATFORM", None)  # an inherited `offscreen` would hide the window
        proc = subprocess.Popen(
            [sys.executable, str(app), *test["launch"], *app_args], env=env
        )
        try:
            handle = None
            deadline = time.monotonic() + WINDOW_TIMEOUT_S
            while handle is None and time.monotonic() < deadline:
                if proc.poll() is not None:
                    raise RuntimeError(f"the app exited at once with code {proc.returncode}")
                found = windows_of(class_name)
                if found:
                    handle = found[0]["handle"]
                else:
                    time.sleep(0.25)
            if handle is None:
                raise RuntimeError(
                    f"no {class_name} window within {WINDOW_TIMEOUT_S:.0f} s"
                )
            return desktop.run_steps(handle, dict(test["steps"]), dict(test["targets"]))
        finally:
            _stop(proc)
            # Wait for the window to leave the tree, or the next test of the same screen
            # finds two (eval/apps/sample/uia_check.py:kill_process_tree, 2026-11-15).
            deadline = time.monotonic() + 10
            while windows_of(class_name) and time.monotonic() < deadline:
                time.sleep(0.25)

    return play, desktop.close


def _stop(proc: subprocess.Popen[bytes]) -> None:
    subprocess.run(
        ["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True, check=False
    )
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


# --- command line --------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None, player_factory=windows_player) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("suite", type=Path, help="the suite file, e.g. .github/suite/smoke.json")
    parser.add_argument("--app", type=Path, required=True, help="the app's main script")
    parser.add_argument(
        "--app-arg",
        action="append",
        default=[],
        help="an argument for every app start, e.g. --app-arg=--bug --app-arg=bug4",
    )
    parser.add_argument("--junit", type=Path, required=True, help="where to write JUnit XML")
    parser.add_argument(
        "--expect-failed",
        action="append",
        default=[],
        metavar="TEST",
        help="a test that must fail on this build (the job then passes only if it does)",
    )
    parser.add_argument("--build", default="v1", help="the build's name, for the summary")
    args = parser.parse_args(argv)

    try:
        suite = load_suite(args.suite)
        unknown = set(args.expect_failed) - {t["name"] for t in suite["tests"]}
        if unknown:
            raise SuiteError(f"--expect-failed names no test of the suite: {sorted(unknown)}")
        play, close = player_factory(args.app, args.app_arg)
        try:
            outcomes = run_suite(suite, play)
        finally:
            close()
    except SuiteError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    args.junit.parent.mkdir(parents=True, exist_ok=True)
    args.junit.write_bytes(junit_xml(suite, outcomes))
    summary = summary_markdown(suite, outcomes, args.expect_failed, args.build)
    # A Windows runner's console is cp1252: the summary's ✅ and Turkish text would raise
    # UnicodeEncodeError after the XML was already written (first CI run, PR #249).
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(summary)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as out:
            out.write(summary)
    return exit_code(outcomes, args.expect_failed)


if __name__ == "__main__":
    sys.exit(main())
