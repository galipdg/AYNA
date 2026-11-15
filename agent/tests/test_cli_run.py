"""#61's rules: what a suite outcome means, and what the process exits with (FR-23).

No Windows and no server. The player and the sink are both seams, so every path — a failing
test, a server that refuses a result, a run that could not be created — is driven with fakes.

The case these tests exist for is FR-23's third exit code: **a suite can pass and still exit
2**, because results nobody stored are not a run anybody can point at later. It is the one
rule a reader would not guess, and the one a CI pipeline is harmed most by getting wrong.
"""

from __future__ import annotations

import pytest

from ayna_cli.exits import ALL_GOOD, OPERATIONAL_FAILURE, TEST_FAILED, exit_code
from ayna_cli.run import (
    ABORTED,
    FAILED,
    PASSED,
    NoSink,
    ServerSink,
    play_suite,
)
from ayna_cli.server import ServerError
from ayna_cli.suite import Suite, SuiteTest


def a_test(name: str = "Login succeeds", test_id: str | None = "t1") -> SuiteTest:
    return SuiteTest(
        name=name,
        document={"version": "0.2", "steps": [{"keyword": "Click", "target": "a"}]},
        targets={"a": {"properties": {"automationId": "a"}}},
        scenario="SC-14",
        test_id=test_id,
        window_title="Giriş",
    )


def results(*statuses: str) -> list[dict]:
    return [
        {"stepIndex": index, "status": status, "durationMs": 1}
        for index, status in enumerate(statuses)
    ]


class FakePlayer:
    """Answers canned results per test name, or raises what it was told to raise."""

    def __init__(self, answers=None, raises=None):
        self.answers = answers or {}
        self.raises = raises or {}
        self.played: list[str] = []

    def play(self, test):
        self.played.append(test.name)
        if test.name in self.raises:
            raise self.raises[test.name]
        return self.answers.get(test.name, results("passed"))


class FakeSink:
    """Records what was delivered; can be told to fail at any of the three moments."""

    def __init__(self, fail_start=(), fail_result=(), fail_finish=()):
        self.fail_start = set(fail_start)
        self.fail_result = set(fail_result)
        self.fail_finish = set(fail_finish)
        self.started: list[str] = []
        self.results: list[tuple[str | None, int]] = []
        self.finished: list[tuple[str | None, str]] = []

    def start(self, test):
        if test.name in self.fail_start:
            raise ServerError(f"could not create a run for {test.name}")
        self.started.append(test.name)
        return f"run-{test.name}"

    def result(self, run_id, index, result):
        if run_id in {f"run-{name}" for name in self.fail_result}:
            raise ServerError("the server refused the result")
        self.results.append((run_id, index))

    def finish(self, run_id, status):
        if run_id in {f"run-{name}" for name in self.fail_finish}:
            raise ServerError("the server refused the finish")
        self.finished.append((run_id, status))


# --- the exit-code rule on its own ---------------------------------------------------------


@pytest.mark.parametrize(
    ("failed", "operational", "expected"),
    [
        (False, False, ALL_GOOD),
        (True, False, TEST_FAILED),
        (False, True, OPERATIONAL_FAILURE),
        (True, True, OPERATIONAL_FAILURE),
    ],
)
def test_the_exit_code_precedence_is_fr_23s(failed, operational, expected):
    assert (
        exit_code(any_test_failed=failed, operational_failure=operational) == expected
    )


def test_an_operational_failure_beats_a_green_suite():
    """Spelled out because it is the rule a reader would guess wrong."""
    assert (
        exit_code(any_test_failed=False, operational_failure=True)
        == OPERATIONAL_FAILURE
    )
    assert OPERATIONAL_FAILURE != ALL_GOOD


# --- playing a suite -----------------------------------------------------------------------


def test_a_suite_where_everything_passes_exits_zero():
    suite = Suite("smoke", [a_test("one"), a_test("two")])
    sink = FakeSink()
    outcome = play_suite(suite, FakePlayer(), sink)

    assert [t.status for t in outcome.tests] == [PASSED, PASSED]
    assert outcome.code == ALL_GOOD
    assert sink.finished == [("run-one", PASSED), ("run-two", PASSED)]


def test_a_failing_step_fails_its_test_and_exits_one():
    suite = Suite("smoke", [a_test("one")])
    player = FakePlayer({"one": results("passed", "failed", "notRun")})
    outcome = play_suite(suite, player, FakeSink())

    assert outcome.tests[0].status == FAILED
    assert outcome.tests[0].failing_step["stepIndex"] == 1
    assert outcome.code == TEST_FAILED


def test_a_proposed_repair_counts_as_not_passing():
    """FR-23: exit 1 'when a test fails **or proposes a repair**' (#73)."""
    player = FakePlayer({"one": results("passed", "repairProposed")})
    outcome = play_suite(Suite("s", [a_test("one")]), player, FakeSink())
    assert outcome.tests[0].status == FAILED
    assert outcome.code == TEST_FAILED


def test_one_test_that_cannot_be_played_does_not_stop_the_others():
    """Five outcomes are more use to a CI log than the first one and a stack trace."""
    suite = Suite("smoke", [a_test("one"), a_test("two"), a_test("three")])
    player = FakePlayer(raises={"two": RuntimeError("no window titled 'Giriş'")})
    outcome = play_suite(suite, player, FakeSink())

    assert player.played == ["one", "two", "three"]
    assert [t.status for t in outcome.tests] == [PASSED, FAILED, PASSED]
    assert "no window" in outcome.tests[1].error
    assert outcome.code == TEST_FAILED


def test_a_test_that_could_not_be_played_finishes_its_run_as_aborted():
    suite = Suite("smoke", [a_test("one")])
    sink = FakeSink()
    play_suite(suite, FakePlayer(raises={"one": RuntimeError("boom")}), sink)
    assert sink.finished == [("run-one", ABORTED)]


# --- delivery, which is a different fact from the outcome ------------------------------------


def test_a_green_suite_whose_results_were_refused_exits_two():
    """The whole reason FR-23 has a third code."""
    suite = Suite("smoke", [a_test("one")])
    outcome = play_suite(suite, FakePlayer(), FakeSink(fail_result={"one"}))

    assert outcome.tests[0].passed, "the application was fine"
    assert outcome.tests[0].delivery_error
    assert outcome.any_test_failed is False
    assert outcome.code == OPERATIONAL_FAILURE


def test_a_run_that_could_not_be_created_is_still_played():
    """Throwing away the evidence because the record failed would be the wrong trade."""
    suite = Suite("smoke", [a_test("one")])
    player = FakePlayer()
    outcome = play_suite(suite, player, FakeSink(fail_start={"one"}))

    assert player.played == ["one"], "the test ran"
    assert outcome.tests[0].passed
    assert "could not create a run" in outcome.tests[0].delivery_error
    assert outcome.code == OPERATIONAL_FAILURE


def test_a_refused_finish_is_also_a_delivery_failure():
    outcome = play_suite(
        Suite("smoke", [a_test("one")]), FakePlayer(), FakeSink(fail_finish={"one"})
    )
    assert outcome.tests[0].passed
    assert outcome.code == OPERATIONAL_FAILURE


def test_delivery_stops_at_the_first_refusal_rather_than_repeating_it():
    sink = FakeSink(fail_result={"one"})
    player = FakePlayer({"one": results("passed", "passed", "passed")})
    play_suite(Suite("smoke", [a_test("one")]), player, sink)
    assert sink.results == [], "it did not keep trying the rest"


def test_a_failing_test_and_a_failing_server_both_show_but_two_wins():
    suite = Suite("smoke", [a_test("one"), a_test("two")])
    player = FakePlayer({"two": results("failed")})
    outcome = play_suite(suite, player, FakeSink(fail_result={"one"}))

    assert outcome.any_test_failed is True
    assert len(outcome.undelivered) == 1
    assert outcome.code == OPERATIONAL_FAILURE


def test_every_result_is_delivered_under_its_own_step_index():
    sink = FakeSink()
    player = FakePlayer({"one": results("passed", "passed", "failed")})
    play_suite(Suite("smoke", [a_test("one")]), player, sink)
    assert sink.results == [("run-one", 0), ("run-one", 1), ("run-one", 2)]


def test_a_result_without_a_step_index_cannot_be_stored():
    sink = FakeSink()
    player = FakePlayer({"one": [{"status": "passed", "durationMs": 1}]})
    outcome = play_suite(Suite("smoke", [a_test("one")]), player, sink)
    assert "stepIndex" in outcome.tests[0].delivery_error
    assert outcome.code == OPERATIONAL_FAILURE


# --- the two sinks --------------------------------------------------------------------------


def test_without_a_server_nothing_is_delivered_and_nothing_fails():
    suite = Suite("smoke", [a_test("one", test_id=None)])
    outcome = play_suite(suite, FakePlayer(), NoSink())
    assert outcome.tests[0].passed
    assert outcome.undelivered == []
    assert outcome.code == ALL_GOOD


def test_the_server_sink_refuses_a_test_with_no_server_id():
    """A file suite's test has no id, so it cannot be posted to a server."""
    sink = ServerSink(server=object(), app_version_id="v1")
    with pytest.raises(ServerError, match="no server id"):
        sink.start(a_test("one", test_id=None))


# --- #51's screenshots, which ride along with their results ---------------------------------


class FakeServer:
    """Records the three calls `ServerSink` makes, and can refuse any of them."""

    def __init__(self, refuse_screenshot=False):
        self.refuse_screenshot = refuse_screenshot
        self.results: list[tuple[str, int]] = []
        self.screenshots: list[tuple[str, int, bytes]] = []
        self.order: list[str] = []

    def create_run(self, *, app_version_id, test_id):
        return {"id": f"run-{test_id}"}

    def write_result(self, run_id, index, result):
        self.order.append(f"result {index}")
        self.results.append((run_id, index))

    def upload_screenshot(self, run_id, index, png):
        if self.refuse_screenshot:
            raise ServerError("the server refused the image")
        self.order.append(f"png {index}")
        self.screenshots.append((run_id, index, png))

    def finish_run(self, run_id, status):
        self.order.append(f"finish {status}")


def test_a_result_that_names_a_png_sends_it_after_the_result(tmp_path):
    """The order is the server's rule: a screenshot before its result is a 404 (#51)."""
    image = tmp_path / "step-0000.png"
    image.write_bytes(b"\x89PNG\r\n\x1a\nbytes")
    server = FakeServer()
    sink = ServerSink(server, "v1")

    sink.result(
        "run-t1", 0, {"stepIndex": 0, "status": "passed", "screenshotPath": str(image)}
    )

    assert server.order == ["result 0", "png 0"]
    assert server.screenshots == [("run-t1", 0, b"\x89PNG\r\n\x1a\nbytes")]


def test_a_result_with_no_screenshot_sends_none(tmp_path):
    """#54 leaves the field out for a notRun step and for a capture that failed."""
    server = FakeServer()
    ServerSink(server, "v1").result("run-t1", 1, {"stepIndex": 1, "status": "notRun"})
    assert server.results == [("run-t1", 1)]
    assert server.screenshots == []


def test_a_named_png_that_is_gone_is_logged_not_fatal(tmp_path, caplog):
    """A swept temp folder must not turn a recorded result into a red build."""
    server = FakeServer()
    sink = ServerSink(server, "v1")

    with caplog.at_level("WARNING"):
        sink.result(
            "run-t1",
            2,
            {
                "stepIndex": 2,
                "status": "passed",
                "screenshotPath": str(tmp_path / "gone.png"),
            },
        )

    assert server.results == [("run-t1", 2)], "the result itself was still stored"
    assert server.screenshots == []
    assert "no screenshot to upload" in caplog.text


def test_a_server_that_refuses_the_image_is_a_delivery_failure(tmp_path):
    """Unlike a missing file: the server saying no is the job's problem, and exits 2."""
    image = tmp_path / "step-0000.png"
    image.write_bytes(b"png")
    suite = Suite("smoke", [a_test("one")])
    server = FakeServer(refuse_screenshot=True)

    outcome = play_suite(
        suite,
        FakePlayer(
            {
                "one": [
                    {"stepIndex": 0, "status": "passed", "screenshotPath": str(image)}
                ]
            }
        ),
        ServerSink(server, "v1"),
    )

    assert outcome.tests[0].passed
    assert "refused the image" in outcome.tests[0].delivery_error
    assert outcome.code == OPERATIONAL_FAILURE


def test_screenshots_can_be_turned_off(tmp_path):
    image = tmp_path / "step-0000.png"
    image.write_bytes(b"png")
    server = FakeServer()
    sink = ServerSink(server, "v1", screenshots=False)
    sink.result(
        "run-t1", 0, {"stepIndex": 0, "status": "passed", "screenshotPath": str(image)}
    )
    assert server.screenshots == []
