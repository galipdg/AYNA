"""`ayna run`: the command line, and the one place an exit code is produced (#61, FR-23).

    ayna run --from-file suite.json
    ayna run --server http://ayna:8080 --suite "AYNA Trial"

The token is read from `AYNA_SERVER_TOKEN`, never from an option: a command line is readable by
other processes on the machine.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from collections.abc import Sequence
from dataclasses import replace
from datetime import datetime
from typing import Any, TextIO

from ayna_cli.exits import OPERATIONAL_FAILURE
from ayna_cli.junit import write_junit
from ayna_cli.playback import AgentPlayer, PlaybackUnavailable
from ayna_cli.run import NoSink, ServerSink, SuiteOutcome, TestOutcome, play_suite
from ayna_cli.server import TOKEN_VARIABLE, AynaServer, ServerError
from ayna_cli.suite import Suite, SuiteError, SuiteTest, read_suite_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ayna run",
        description="Run a suite with a headless agent and report what happened (#61).",
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--from-file",
        metavar="SUITE.JSON",
        help="run a suite from a file, with no server (FR-23; CI without AYNA installed)",
    )
    source.add_argument(
        "--server",
        metavar="URL",
        help=f"the AYNA server; its API token comes from {TOKEN_VARIABLE}",
    )
    parser.add_argument(
        "--suite",
        metavar="NAME",
        help=(
            "with --server: which application's tests to run. The server has no suite of its "
            "own yet, so a suite is an application's tests (#61, asked on the issue)"
        ),
    )
    parser.add_argument(
        "--app-version",
        metavar="ID",
        help="the application version a run is recorded against; default its newest",
    )
    parser.add_argument(
        "--junit",
        metavar="OUT.XML",
        help=(
            "write the run as JUnit XML, so a CI server shows it as tests (#66, FR-24). "
            "Validated against the Apache Ant JUnit schema"
        ),
    )
    parser.add_argument(
        "--window",
        metavar="TITLE",
        help=(
            "the window every test plays against, by its title. With --server this is often "
            "needed: a repository object carries a windowTitle only if whoever captured it "
            "kept one, and the trial app's five objects on our own server carry none"
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None, *, out: TextIO | None = None) -> int:
    """Everything funnels here so there is exactly one place that chooses an exit code."""
    out = out or sys.stdout
    args = build_parser().parse_args(argv)
    if args.server and not args.suite:
        build_parser().error("--server needs --suite")

    try:
        suite, sink = _prepare(args)
    except (SuiteError, ServerError) as exc:
        print(f"error: {exc}", file=out)
        return OPERATIONAL_FAILURE

    try:
        player = AgentPlayer.start()
    except PlaybackUnavailable as exc:
        print(f"error: {exc}", file=out)
        return OPERATIONAL_FAILURE

    started_at = datetime.now().astimezone()
    started = time.monotonic()
    try:
        outcome = play_suite(suite, player, sink, on_test=lambda t: _say(t, out))
    finally:
        player.close()
    elapsed = time.monotonic() - started

    if args.junit:
        # After the run and before the exit code, and never allowed to change it: a report
        # that cannot be written is the job's problem to see, not a reason to relabel a run
        # that already happened.
        try:
            write_junit(
                args.junit,
                suite.name,
                outcome,
                started_at=started_at,
                duration_s=elapsed,
            )
        except OSError as exc:
            print(f"warning: could not write {args.junit}: {exc}", file=out)

    _summarise(suite, outcome, out)
    return outcome.code


def _prepare(args: argparse.Namespace) -> tuple[Suite, Any]:
    if args.from_file:
        suite = read_suite_file(args.from_file)
        if args.window:
            suite = Suite(
                suite.name,
                [
                    replace(test, window_title=args.window, window_class=None)
                    for test in suite.tests
                ],
            )
        return suite, NoSink()

    server = AynaServer(args.server, os.environ.get(TOKEN_VARIABLE, ""))
    return suite_from_server(server, args.suite, args.app_version, args.window)


def suite_from_server(
    server: AynaServer,
    name: str,
    app_version_id: str | None,
    window_title: str | None = None,
) -> tuple[Suite, ServerSink]:
    """Build a suite from an application's tests and its repository.

    `--suite NAME` names an **application**: the server has applications, tests and runs, and
    no suite entity at all (`docs/api/openapi.yaml`). That is a reading of FR-23, not a
    decision — if a suite is meant to be a named subset of tests, it is a server change. Said
    so on #61 and in the task note.
    """
    app = _one_named(server.applications(), name, "application")
    app_id = str(app["id"])

    if app_version_id is None:
        versions = server.versions_of(app_id)
        if not versions:
            raise ServerError(f"{name} has no version to record a run against")
        app_version_id = str(versions[-1]["id"])

    targets = _targets_from(server.repo_objects_of(app_id))
    tests = []
    for test in server.tests_of(app_id):
        # The list is `{id, name, stepCount}` — no steps. They come from the run's own copy
        # (`POST /api/runs`), which is what the ADR says should be played anyway; the empty
        # document here is a placeholder that `ServerSink.start` replaces.
        document: dict[str, Any] = {"version": "0.2", "steps": []}
        tests.append(
            SuiteTest(
                name=str(test.get("name") or test.get("id")),
                document=document,
                targets=targets,
                test_id=str(test["id"]),
                window_title=window_title or _window_title_in(targets),
            )
        )
    if not tests:
        raise ServerError(f"{name} has no tests to run")
    return Suite(name=name, tests=tests), ServerSink(server, app_version_id)


def _one_named(items: list[dict[str, Any]], name: str, what: str) -> dict[str, Any]:
    matches = [item for item in items if item.get("name") == name]
    if not matches:
        known = ", ".join(sorted(str(i.get("name")) for i in items)) or "none"
        raise ServerError(
            f"no {what} named {name!r} on this server (there is: {known})"
        )
    if len(matches) > 1:
        raise ServerError(f"{len(matches)} {what}s are named {name!r}")
    return matches[0]


def _targets_from(objects: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Repository objects as `run_steps` wants them: logical name -> property sets."""
    targets: dict[str, dict[str, Any]] = {}
    for obj in objects:
        name = obj.get("name")
        primary = obj.get("primary")
        if not isinstance(name, str) or not isinstance(primary, dict):
            continue
        target: dict[str, Any] = {"properties": primary}
        if isinstance(obj.get("fallback"), dict):
            target["fallback"] = obj["fallback"]
        targets[name] = target
    return targets


def _window_title_in(targets: dict[str, dict[str, Any]]) -> str | None:
    """#40's rule: the window comes from a target's `windowTitle`, primary then fallback.

    Often `None` in practice, which is why `--window` exists: an object only carries a
    `windowTitle` if whoever captured it kept one, and none of the trial app's five objects on
    our own server does. The steps are not consulted, because at this point there are none —
    the test list has no document (see `suite_from_server`).
    """
    for target in targets.values():
        for properties in (target.get("properties"), target.get("fallback")):
            title = (properties or {}).get("windowTitle")
            if isinstance(title, str) and title:
                return title
    return None


def _say(test: TestOutcome, out: TextIO) -> None:
    mark = "pass" if test.passed else "FAIL"
    line = f"{mark}  {test.name}"
    if test.scenario:
        line = f"{line} ({test.scenario})"
    print(line, file=out)
    if test.error:
        print(f"      could not be played: {test.error}", file=out)
    elif not test.passed:
        step = test.failing_step
        if step:
            print(
                f"      step {step.get('stepIndex')}: {step.get('message') or step.get('status')}",
                file=out,
            )
    if test.delivery_error:
        print(f"      NOT STORED: {test.delivery_error}", file=out)


def _summarise(suite: Suite, outcome: SuiteOutcome, out: TextIO) -> None:
    passed = sum(1 for test in outcome.tests if test.passed)
    total = len(outcome.tests)
    print(f"\n{suite.name}: {passed}/{total} passed", file=out)
    undelivered = outcome.undelivered
    if undelivered:
        # Said last and said plainly: this is why a green suite can still exit 2, and a CI log
        # that buried it would be the whole problem FR-23's third code exists to prevent.
        names = ", ".join(test.name for test in undelivered)
        print(
            f"{len(undelivered)} of {total} were not stored on the server ({names}), "
            "so this run is not in the record",
            file=out,
        )
    if outcome.error:
        print(f"error: {outcome.error}", file=out)


#: The only command there is. `ayna run …` reads better in a CI file than `ayna …`, and FR-23
#: and UC-14 both write it that way, so the verb is required rather than optional — accepting
#: both spellings would make every future command ambiguous with an option.
COMMAND = "run"


def _speak_utf8() -> None:
    """Print UTF-8 whatever the console or the pipe is set to.

    Test names, window titles and the application's own messages are Turkish, and a CI job
    redirects stdout to a pipe or a file — where Python falls back to the locale encoding. On a
    Windows runner that is often cp1252, which has no ş or ı, and the command would then die
    with a `UnicodeEncodeError` *while reporting a test result*: a failed test would look like
    a crashed runner. `errors="replace"` keeps the worst case to a mangled character.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):  # a stream that cannot be reconfigured
                pass


def console_entry(argv: Sequence[str] | None = None) -> int:
    """The `ayna` script: strips the `run` verb and hands the rest to :func:`main`."""
    _speak_utf8()
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help"):
        print(
            f"usage: ayna {COMMAND} [--from-file SUITE.JSON | --server URL --suite NAME]"
        )
        print(
            f"The only command is `{COMMAND}`; `ayna {COMMAND} --help` has its options."
        )
        return OPERATIONAL_FAILURE if not argv else 0
    if argv[0] != COMMAND:
        print(f"error: unknown command {argv[0]!r}; the only command is `{COMMAND}`")
        return OPERATIONAL_FAILURE
    return main(argv[1:])


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(console_entry())
