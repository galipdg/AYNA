"""The CI side of a suite run (#67): start the app, run `ayna run`, report, check.

`ayna run --from-file` (#61) plays a suite against windows that are **already open**, as a
user's pipeline would have it (SC-33: "a Windows CI runner that has started version 1.0 of the
sample app"). This script is that pipeline's part, nothing more:

1. start the sample app once per distinct `launch` of the suite (one window per screen; the
   CLI finds each test's window by its ClassName);
2. run `python -m ayna_cli run --from-file SUITE` and keep its output;
3. put that output on the job summary (`$GITHUB_STEP_SUMMARY`), since JUnit XML is #66's;
4. with `--expect-failed`, turn "these tests must fail on this bug build" into the job's
   verdict;
5. stop the app.

Exit codes are the CLI's own (0, 1, 2) unless `--expect-failed` is given: then 0 when exactly
the named tests failed and the others passed, 1 when not, 2 when the run itself broke.

The app is started with this script's own interpreter, so run it in **one environment that
has both the agent and PySide6** (`pip install -e ./agent -e ./eval`). Without PySide6 the app
dies at once and the CLI only says, 60 s later, that no window with that ClassName appeared.

Until #66 writes JUnit XML, which test passed is read from the CLI's `pass  NAME` /
`FAIL  NAME` lines (`ayna_cli/cli.py:_say`). Switch to the XML when it exists.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

LINE = re.compile(r"^(pass|FAIL)  (.+?)(?: \((SC-[0-9]+)\))?$")

#: `(args) -> process`, and `(process) -> None`; injected so the tests need no app.
Launch = Callable[[list[str]], Any]
Stop = Callable[[Any], None]
#: `(suite path) -> (exit code, output)`
RunCli = Callable[[Path], tuple[int, str]]


def launches_of(suite: dict[str, Any]) -> list[list[str]]:
    """Each distinct `launch` once, in suite order."""
    seen: list[list[str]] = []
    for test in suite.get("tests", []):
        launch = list(test.get("launch") or [])
        if launch not in seen:
            seen.append(launch)
    return seen


def results_of(output: str) -> dict[str, str]:
    """`{test name: "pass" | "FAIL"}` from the CLI's per-test lines."""
    found = {}
    for line in output.splitlines():
        match = LINE.match(line.rstrip())
        if match:
            found[match.group(2)] = match.group(1)
    return found


def verdict(
    code: int, output: str, names: Sequence[str], expect_failed: Sequence[str]
) -> tuple[int, str]:
    """The job's exit code and one line saying why."""
    if not expect_failed:
        return code, f"ayna run exited {code}"
    if code not in (0, 1):
        return 2, f"ayna run exited {code}: the run itself broke"
    seen = results_of(output)
    wrong = []
    for name in names:
        wanted = "FAIL" if name in expect_failed else "pass"
        if seen.get(name) != wanted:
            wrong.append(f"{name}: {seen.get(name, 'no result')}, expected {wanted}")
    if wrong:
        return 1, "not what this build must give: " + "; ".join(wrong)
    return 0, "the bug build failed exactly the tests it must fail"


def summary(build: str, output: str, line: str) -> str:
    fence = "~~~"
    return f"### `ayna run` on the sample app ({build})\n\n{fence}text\n{output.rstrip()}\n{fence}\n\n{line}\n"


def default_run_cli(suite: Path) -> tuple[int, str]:
    done = subprocess.run(
        [sys.executable, "-m", "ayna_cli", "run", "--from-file", str(suite)],
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
        "--out", type=Path, default=Path("out"), help="where the log goes"
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

    started = []
    try:
        for screen in launches_of(suite):
            started.append(launch([*screen, *args.app_arg]))
        code, output = run_cli(args.suite)
    finally:
        for proc in started:
            stop(proc)

    result, line = verdict(code, output, names, args.expect_failed)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "ayna-run.txt").write_text(output, encoding="utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # cp1252 on a runner
    print(output.rstrip())
    print(line)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as out:
            out.write(summary(args.build, output, line))
    return result


if __name__ == "__main__":
    sys.exit(main())
