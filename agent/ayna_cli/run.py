"""Playing a suite and deciding what the process exits with (#61, FR-23).

Two seams, so that neither Windows nor a server is needed to test the rules:

- a **player** plays one test and answers one result per step, exactly as
  `UiaDesktop.run_steps` does (`ayna_cli.playback` builds the real one);
- a **sink** is where results go — :class:`ServerSink` for `--server`, :class:`NoSink` for
  `--from-file`.

The rule the whole module exists for is FR-23's third exit code. A test's outcome and a
delivery failure are **different** facts and are kept apart all the way to the end: a suite can
pass while the server refuses its results, and that is a 2.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Protocol

from ayna_cli.exits import exit_code
from ayna_cli.server import AynaServer, ServerError
from ayna_cli.suite import Suite, SuiteTest

#: A step's status that means the test did not pass. `repairProposed` is #73's and is already
#: here, because FR-23 says a proposed repair exits 1 just as a failure does.
NOT_PASSED = frozenset({"failed", "repairProposed"})

PASSED, FAILED, ABORTED = "passed", "failed", "aborted"

log = logging.getLogger(__name__)


class Player(Protocol):
    """Plays one test against the application and answers one result per step."""

    def play(self, test: SuiteTest) -> list[dict[str, Any]]: ...


@dataclass(frozen=True)
class StartedRun:
    """What starting a run gives back: where results go, and what to play.

    The **document** matters as much as the id. `POST /api/runs` answers with the run's *own
    copy* of the steps, and that copy — not the test as it stands now — is what the run plays
    (ADR *Runs API and live run updates*): a test edited while a run is in flight must not
    change what its results mean. The test list does not carry a document at all
    (`GET /api/apps/{id}/tests` is `{id, name, stepCount}`), so without this the CLI would
    play nothing. Found by running against a real server.
    """

    run_id: str | None = None
    document: Mapping[str, Any] | None = None


class Sink(Protocol):
    """Where a test's results go. Every method may raise `ServerError`."""

    def start(self, test: SuiteTest) -> StartedRun: ...

    def result(
        self, run_id: str | None, index: int, result: Mapping[str, Any]
    ) -> None: ...

    def finish(self, run_id: str | None, status: str) -> None: ...


@dataclass
class TestOutcome:
    #: Not a pytest test class, despite the name. Without this, any test module that imports it
    #: gets a `PytestCollectionWarning` — pytest collects anything called `Test*`.
    __test__ = False

    name: str
    scenario: str | None
    status: str
    results: list[dict[str, Any]] = field(default_factory=list)
    #: Why the test could not be played at all, as opposed to a step of it failing.
    error: str | None = None
    #: What went wrong delivering this test's results. Separate from `error` on purpose: it
    #: says nothing about the application and everything about the job.
    delivery_error: str | None = None

    @property
    def passed(self) -> bool:
        return self.status == PASSED

    @property
    def failing_step(self) -> dict[str, Any] | None:
        return next((r for r in self.results if r.get("status") in NOT_PASSED), None)


@dataclass
class SuiteOutcome:
    tests: list[TestOutcome] = field(default_factory=list)
    #: Something that stopped the whole command rather than one test.
    error: str | None = None

    @property
    def any_test_failed(self) -> bool:
        return any(not test.passed for test in self.tests)

    @property
    def undelivered(self) -> list[TestOutcome]:
        return [test for test in self.tests if test.delivery_error]

    @property
    def operational_failure(self) -> bool:
        return bool(self.error) or bool(self.undelivered)

    @property
    def code(self) -> int:
        return exit_code(
            any_test_failed=self.any_test_failed,
            operational_failure=self.operational_failure,
        )


class NoSink:
    """`--from-file` with no server: results are played and reported, never stored."""

    def start(self, test: SuiteTest) -> StartedRun:
        return StartedRun()

    def result(self, run_id: str | None, index: int, result: Mapping[str, Any]) -> None:
        return None

    def finish(self, run_id: str | None, status: str) -> None:
        return None


class ServerSink:
    """Stores a test's results on the server as the run goes (#44's contract).

    A run is created per test, because the server's `Run` *is* one test's run
    (`POST /api/runs` takes a `testId`).

    A result that names a screenshot takes its bytes with it (#51, #54). The order is fixed by
    omer's ADR and not ours to choose: the image goes **after** its result, because the server
    answers 404 to a screenshot for a step it has no result for yet.
    """

    def __init__(
        self, server: AynaServer, app_version_id: str, *, screenshots: bool = True
    ) -> None:
        self.server = server
        self.app_version_id = app_version_id
        self.screenshots = screenshots

    def start(self, test: SuiteTest) -> StartedRun:
        if test.test_id is None:
            raise ServerError(
                f"{test.name}: no server id, so its run cannot be created"
            )
        run = self.server.create_run(
            app_version_id=self.app_version_id, test_id=test.test_id
        )
        document = run.get("document")
        return StartedRun(
            run_id=str(run["id"]),
            document=document if isinstance(document, Mapping) else None,
        )

    def result(self, run_id: str | None, index: int, result: Mapping[str, Any]) -> None:
        if run_id is None:
            raise ServerError("no run id")
        self.server.write_result(run_id, index, dict(result))
        if self.screenshots:
            self._upload_screenshot(run_id, index, result)

    def _upload_screenshot(
        self, run_id: str, index: int, result: Mapping[str, Any]
    ) -> None:
        """Send the step's PNG, if it has one and it is still on disk.

        **A missing image is not a delivery failure.** #54 leaves `screenshotPath` out whenever
        there is none -- a `notRun` step, or a capture that failed -- and says plainly that a
        reader must treat that as normal. A file named but gone is the same situation one step
        later (a tidy-up ran, a temp folder was swept), and failing the run over a lost picture
        would turn an operational nuisance into a red build. The *result* is the record; the
        image is evidence attached to it.
        """
        path = result.get("screenshotPath")
        if not isinstance(path, str) or not path:
            return
        try:
            png = Path(path).read_bytes()
        except OSError as exc:
            log.warning(
                "step %d: no screenshot to upload from %s: %s", index, path, exc
            )
            return
        self.server.upload_screenshot(run_id, index, png)

    def finish(self, run_id: str | None, status: str) -> None:
        if run_id is None:
            return
        self.server.finish_run(run_id, status)


def play_suite(
    suite: Suite,
    player: Player,
    sink: Sink,
    *,
    on_test: Callable[[TestOutcome], None] | None = None,
) -> SuiteOutcome:
    """Play every test in order, deliver as we go, and keep the two kinds of failure apart.

    **One test's trouble does not stop the suite.** A test that cannot be played at all is its
    own `error` and the next test still runs: a CI job is far more useful when it reports five
    outcomes than when it reports the first and stops. The one thing that does stop everything
    is the player itself being gone, which the caller raises before we get here.
    """
    outcome = SuiteOutcome()
    for test in suite.tests:
        result = _play_one(test, player, sink)
        outcome.tests.append(result)
        if on_test is not None:
            on_test(result)
    return outcome


def _play_one(test: SuiteTest, player: Player, sink: Sink) -> TestOutcome:
    try:
        started = sink.start(test)
    except ServerError as exc:
        # The run was never created, so there is nowhere to put results. Playing the test
        # anyway would throw away the evidence, so play it and record that it is undelivered.
        return _played_without_a_run(test, player, str(exc))

    run_id = started.run_id
    # The run's copy of the steps wins over the suite's, for the reason in `StartedRun`.
    if started.document is not None:
        test = replace(test, document=started.document)

    try:
        results = player.play(test)
    except Exception as exc:  # noqa: BLE001 - any failure to play is this test's error
        played = TestOutcome(
            name=test.name, scenario=test.scenario, status=FAILED, error=str(exc)
        )
        played.delivery_error = _finish(sink, run_id, ABORTED)
        return played

    status = _status_of(results)
    played = TestOutcome(
        name=test.name, scenario=test.scenario, status=status, results=list(results)
    )
    played.delivery_error = _deliver(sink, run_id, results) or _finish(
        sink, run_id, status
    )
    return played


def _played_without_a_run(test: SuiteTest, player: Player, why: str) -> TestOutcome:
    try:
        results = player.play(test)
    except Exception as exc:  # noqa: BLE001
        return TestOutcome(
            name=test.name,
            scenario=test.scenario,
            status=FAILED,
            error=str(exc),
            delivery_error=why,
        )
    return TestOutcome(
        name=test.name,
        scenario=test.scenario,
        status=_status_of(results),
        results=list(results),
        delivery_error=why,
    )


def _deliver(
    sink: Sink, run_id: str | None, results: Sequence[Mapping[str, Any]]
) -> str | None:
    for result in results:
        index = result.get("stepIndex")
        if not isinstance(index, int):
            return f"a result without a stepIndex cannot be stored: {result!r}"
        try:
            sink.result(run_id, index, result)
        except ServerError as exc:
            # Stop at the first one: the rest would almost certainly fail the same way, and a
            # CI log with one clear reason beats the same reason N times.
            return str(exc)
    return None


def _finish(sink: Sink, run_id: str | None, status: str) -> str | None:
    try:
        sink.finish(run_id, status)
    except ServerError as exc:
        return str(exc)
    return None


def _status_of(results: Sequence[Mapping[str, Any]]) -> str:
    if not results:
        # A document with no steps passes trivially; a player that answered nothing for a
        # document that had steps is the caller's bug, and `error` would already be set.
        return PASSED
    return FAILED if any(r.get("status") in NOT_PASSED for r in results) else PASSED
