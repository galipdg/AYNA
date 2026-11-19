"""The CI side of a suite run (#67): start the app, run `ayna run`, report, check.

`ayna run --from-file` (#61) plays a suite against windows that are **already open**, as a
user's pipeline would have it (SC-33: "a Windows CI runner that has started version 1.0 of the
sample app"). This script is that pipeline's part, nothing more:

1. start the sample app once per distinct `launch` of the suite (one window per screen; the
   CLI finds each test's window by its ClassName);
2. run `python -m ayna_cli run --from-file SUITE --junit OUT/junit.xml` and keep its output;
3. stop the app;
4. read the JUnit XML back (`ayna_cli.junit.summary_of`) and put one row per test on the job
   summary (`$GITHUB_STEP_SUMMARY`), with the CLI's output folded under it;
5. with `--expect-failed`, turn "these tests must fail on this bug build" into the job's
   verdict, read from the XML.

Exit codes are the CLI's own (0, 1, 2) unless `--expect-failed` is given: then 0 when exactly
the named tests failed and the others passed, 1 when not, 2 when the run itself broke.

The app is started with this script's own interpreter, so run it in **one environment that
has both the agent and PySide6** (`pip install -e ./agent -e ./eval`). Without PySide6 the app
dies at once and the CLI only says, 60 s later, that no window with that ClassName appeared.

The XML is the one source of which test passed: the CLI's console lines are for people and may
change. The workflow uploads `OUT/` (the XML and the console log) as an artifact. No
third-party reporter action reads the XML (decided on PR #254): the job summary is the view.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

#: The XML's file name in `--out`.
JUNIT = "junit.xml"

#: `(args) -> process`, and `(process) -> None`; injected so the tests need no app.
Launch = Callable[[list[str]], Any]
Stop = Callable[[Any], None]
#: `(suite path, JUnit path) -> (exit code, output)`
RunCli = Callable[[Path, Path], tuple[int, str]]
#: What `summary_of` gives for one `<testcase>`: "passed", "failure", "error" or "skipped".
Outcomes = dict[str, str]


def launches_of(suite: dict[str, Any]) -> list[list[str]]:
    """Each distinct `launch` once, in suite order."""
    seen: list[list[str]] = []
    for test in suite.get("tests", []):
        launch = list(test.get("launch") or [])
        if launch not in seen:
            seen.append(launch)
    return seen


def results_of(document: bytes | None) -> Outcomes:
    """`{test name: outcome}` from the CLI's JUnit XML; empty when there is none."""
    if not document:
        return {}
    from ayna_cli.junit import summary_of

    try:
        return {case["name"]: case["outcome"] for case in summary_of(document)["cases"]}
    except ET.ParseError:
        return {}


def verdict(
    code: int, results: Outcomes, names: Sequence[str], expect_failed: Sequence[str]
) -> tuple[int, str]:
    """The job's exit code and one line saying why.

    On a bug build only a `failure` counts as caught: an `error` means the test could not be
    played (no window, say), which says nothing about the bug.
    """
    if not expect_failed:
        return code, f"ayna run exited {code}"
    if code not in (0, 1):
        return 2, f"ayna run exited {code}: the run itself broke"
    if not results:
        return 2, f"ayna run exited {code} but wrote no JUnit XML"
    wrong = []
    for name in names:
        wanted = "failure" if name in expect_failed else "passed"
        if results.get(name) != wanted:
            wrong.append(f"{name}: {results.get(name, 'no result')}, expected {wanted}")
    if wrong:
        return 1, "not what this build must give: " + "; ".join(wrong)
    return 0, "the bug build failed exactly the tests it must fail"


MARK = {
    "passed": "✅ passed",
    "failure": "❌ failure",
    "error": "⚠️ error",
    "skipped": "skipped",
}


def summary(
    build: str, names: Sequence[str], results: Outcomes, output: str, line: str
) -> str:
    """The job summary: one row per test of the suite, from the XML, then the console log."""
    rows = [
        f"| {name} | {MARK.get(results.get(name, ''), 'no result')} |" for name in names
    ]
    table = "\n".join(["| Test | Result |", "| --- | --- |", *rows])
    if not results:
        table += "\n\nNo JUnit XML was written: see the log."
    fence = "~~~"
    return (
        f"### `ayna run` on the sample app ({build})\n\n{table}\n\n{line}\n\n"
        f"<details><summary>ayna run output</summary>\n\n"
        f"{fence}text\n{output.rstrip()}\n{fence}\n\n</details>\n"
    )


def default_run_cli(suite: Path, junit: Path) -> tuple[int, str]:
    done = subprocess.run(
        [
            sys.executable,
            "-m",
            "ayna_cli",
            "run",
            "--from-file",
            str(suite),
            "--junit",
            str(junit),
        ],
        capture_output=True,
        encoding="utf-8",  # the CLI prints UTF-8 whatever the console is
        errors="replace",
        check=False,
    )
    return done.returncode, done.stdout + done.stderr


def default_stop(proc: Any) -> None:
    if os.name == "nt":
        # The interpreter may sit behind a launcher process; /T takes the window's owner too.
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
            capture_output=True,
            check=False,
        )
    else:
        proc.kill()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        pass


def main(
    argv: Sequence[str] | None = None,
    *,
    launch: Launch | None = None,
    stop: Stop = default_stop,
    run_cli: RunCli = default_run_cli,
) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("suite", type=Path)
    parser.add_argument("--app", type=Path, required=True, help="the app's main script")
    parser.add_argument(
        "--app-arg",
        action="append",
        default=[],
        help="for every app start, e.g. --app-arg=--bug",
    )
    parser.add_argument("--expect-failed", action="append", default=[], metavar="TEST")
    parser.add_argument(
        "--build", default="v1", help="the build's name, for the summary"
    )
    parser.add_argument(
        "--out", type=Path, default=Path("out"), help="where the XML and the log go"
    )
    args = parser.parse_args(argv)

    try:
        suite = json.loads(args.suite.read_text(encoding="utf-8"))
        names = [t["name"] for t in suite["tests"]]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"error: {args.suite}: {exc}", file=sys.stderr)
        return 2
    unknown = sorted(set(args.expect_failed) - set(names))
    if unknown:
        print(
            f"error: --expect-failed names no test of the suite: {unknown}",
            file=sys.stderr,
        )
        return 2

    if launch is None:
        env = dict(os.environ)
        env.pop(
            "QT_QPA_PLATFORM", None
        )  # an inherited `offscreen` would hide the window

        def launch(extra: list[str]) -> Any:
            return subprocess.Popen([sys.executable, str(args.app), *extra], env=env)

    args.out.mkdir(parents=True, exist_ok=True)
    junit = args.out / JUNIT
    junit.unlink(missing_ok=True)  # an old file must not stand in for this run's
    started = []
    try:
        for screen in launches_of(suite):
            started.append(launch([*screen, *args.app_arg]))
        code, output = run_cli(args.suite, junit)
    finally:
        for proc in started:
            stop(proc)

    results = results_of(junit.read_bytes() if junit.exists() else None)
    result, line = verdict(code, results, names, args.expect_failed)
    (args.out / "ayna-run.txt").write_text(output, encoding="utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # cp1252 on a runner
    print(output.rstrip())
    print(line)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as out:
            out.write(summary(args.build, names, results, output, line))
    return result


if __name__ == "__main__":
    sys.exit(main())
