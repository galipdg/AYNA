"""ci_suite.py and smoke.json without Windows (#67)."""

from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent))

import ci_suite

HERE = Path(__file__).parent
REPO = HERE.parents[1]
SMOKE = HERE / "smoke.json"
LOGIN, DETAIL = "Login succeeds", "Detail form refuses an empty name"


def junit_doc(outcomes: dict[str, str]) -> bytes:
    """What `ayna run --junit` writes for these outcomes, made by the CLI's own writer.

    `outcomes` maps a test name to "passed", "failed" or "error".
    """
    from ayna_cli.junit import junit_bytes
    from ayna_cli.run import SuiteOutcome, TestOutcome

    tests = []
    for name, how in outcomes.items():
        status = "passed" if how == "passed" else "failed"
        results = [{"stepIndex": 0, "status": status, "message": "x"}]
        error = "no window" if how == "error" else None
        tests.append(
            TestOutcome(name, "SC-14", status, [] if error else results, error)
        )
    return junit_bytes("smoke", SuiteOutcome(tests), hostname="runner")


def fake_cli(code: int, outcomes: dict[str, str] | None, output: str = "log\n"):
    """A `run_cli` that writes the XML where it is told to, as the real CLI does."""

    def run(_suite: Path, junit: Path) -> tuple[int, str]:
        if outcomes is not None:
            junit.write_bytes(junit_doc(outcomes))
        return code, output

    return run


class SmokeSuite(unittest.TestCase):
    def setUp(self):
        self.suite = json.loads(SMOKE.read_text("utf-8"))

    def test_the_cli_reads_it(self):
        try:
            from ayna_cli.suite import read_suite_file
        except ImportError:
            self.skipTest("the agent is not installed here")
        suite = read_suite_file(SMOKE)
        self.assertEqual([t.name for t in suite.tests], [LOGIN, DETAIL])
        self.assertEqual(
            [t.window_class for t in suite.tests], ["LoginWindow", "DetailWindow"]
        )

    def test_every_step_document_is_valid_against_the_step_schema(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema is not installed here")
        schema = json.loads((REPO / "schemas" / "step.schema.json").read_text("utf-8"))
        for test in self.suite["tests"]:
            jsonschema.validate(test["steps"], schema)

    def test_the_ids_and_texts_are_the_sample_apps_own(self):
        """A renamed objectName or text in the sample app fails here, not only on Windows."""
        source = (REPO / "eval" / "apps" / "sample" / "windows.py").read_text("utf-8")
        for test in self.suite["tests"]:
            for target in test["targets"].values():
                last = target["properties"]["automationId"].rsplit(".", 1)[-1]
                self.assertIn(f'"{last}"', source, last)
        texts = (REPO / "eval" / "apps" / "sample" / "texts.py").read_text("utf-8")
        self.assertIn('LOGIN_WELCOME = "Hoş geldiniz, {user}!"', texts)
        self.assertIn('DETAIL_NAME_REQUIRED = "Ad alanı zorunlu"', texts)

    def test_each_screen_is_started_once(self):
        self.assertEqual(
            ci_suite.launches_of(self.suite),
            [["--screen", "login"], ["--screen", "detail"]],
        )


class Verdict(unittest.TestCase):
    def setUp(self):
        try:
            import ayna_cli  # noqa: F401
        except ImportError:
            self.skipTest("the agent is not installed here")

    def test_reads_the_clis_own_xml(self):
        self.assertEqual(
            ci_suite.results_of(
                junit_doc({LOGIN: "passed", DETAIL: "failed", "Other": "error"})
            ),
            {LOGIN: "passed", DETAIL: "failure", "Other": "error"},
        )

    def test_no_or_broken_xml_gives_no_results(self):
        self.assertEqual(ci_suite.results_of(None), {})
        self.assertEqual(ci_suite.results_of(b"<testsuite"), {})

    def test_without_expectations_the_clis_code_is_the_jobs(self):
        for code in (0, 1, 2):
            self.assertEqual(ci_suite.verdict(code, {}, [LOGIN], [])[0], code)

    def test_the_expected_test_failing_alone_passes_the_job(self):
        res = {LOGIN: "passed", DETAIL: "failure"}
        self.assertEqual(ci_suite.verdict(1, res, [LOGIN, DETAIL], [DETAIL])[0], 0)

    def test_a_bug_that_slips_through_fails_the_job(self):
        res = {LOGIN: "passed", DETAIL: "passed"}
        code, line = ci_suite.verdict(0, res, [LOGIN, DETAIL], [DETAIL])
        self.assertEqual(code, 1)
        self.assertIn(DETAIL, line)

    def test_another_test_failing_too_fails_the_job(self):
        res = {LOGIN: "failure", DETAIL: "failure"}
        self.assertEqual(ci_suite.verdict(1, res, [LOGIN, DETAIL], [DETAIL])[0], 1)

    def test_an_error_is_not_a_caught_bug(self):
        res = {LOGIN: "passed", DETAIL: "error"}
        code, line = ci_suite.verdict(1, res, [LOGIN, DETAIL], [DETAIL])
        self.assertEqual(code, 1)
        self.assertIn("error", line)

    def test_a_broken_run_is_not_an_expected_failure(self):
        self.assertEqual(ci_suite.verdict(2, {}, [DETAIL], [DETAIL])[0], 2)

    def test_a_run_without_xml_is_not_an_expected_failure(self):
        self.assertEqual(ci_suite.verdict(1, {}, [DETAIL], [DETAIL])[0], 2)


class Main(unittest.TestCase):
    def run_main(self, run_cli, *extra):
        started, stopped = [], []
        with (
            tempfile.TemporaryDirectory() as tmp,
            redirect_stdout(io.StringIO()) as out,
            redirect_stderr(io.StringIO()) as err,
            mock.patch.dict(
                "os.environ", {"GITHUB_STEP_SUMMARY": str(Path(tmp) / "s.md")}
            ),
        ):
            code = ci_suite.main(
                [
                    str(SMOKE),
                    "--app",
                    "app.py",
                    "--app-arg=--bug",
                    "--app-arg=bug4",
                    "--out",
                    tmp,
                    *extra,
                ],
                launch=lambda a: started.append(a) or len(started),
                stop=stopped.append,
                run_cli=run_cli,
            )
            summary = (
                Path(tmp, "s.md").read_text("utf-8")
                if Path(tmp, "s.md").exists()
                else ""
            )
            kept = sorted(f.name for f in Path(tmp).iterdir())
        return code, started, stopped, summary, out.getvalue() + err.getvalue(), kept

    def test_starts_each_screen_with_the_build_runs_and_stops_them(self):
        code, started, stopped, summary, _, kept = self.run_main(
            fake_cli(0, {LOGIN: "passed", DETAIL: "passed"}, "pass  Login succeeds\n")
        )
        self.assertEqual(code, 0)
        self.assertEqual(kept, ["ayna-run.txt", "junit.xml", "s.md"])
        self.assertEqual(
            started,
            [
                ["--screen", "login", "--bug", "bug4"],
                ["--screen", "detail", "--bug", "bug4"],
            ],
        )
        self.assertEqual(stopped, [1, 2])
        self.assertIn(f"| {LOGIN} | ✅ passed |", summary)
        self.assertIn(
            "pass  Login succeeds", summary
        )  # the log, folded under the table

    def test_a_bug_build_is_judged_from_the_xml(self):
        code, *_, summary, text, _ = self.run_main(
            fake_cli(1, {LOGIN: "passed", DETAIL: "failed"}), "--expect-failed", DETAIL
        )
        self.assertEqual(code, 0, text)
        self.assertIn(f"| {DETAIL} | ❌ failure |", summary)

    def test_an_old_xml_does_not_stand_in_for_a_run_that_wrote_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "junit.xml").write_bytes(
                junit_doc({LOGIN: "passed", DETAIL: "failed"})
            )
            with redirect_stdout(io.StringIO()):
                code = ci_suite.main(
                    [
                        str(SMOKE),
                        "--app",
                        "a.py",
                        "--out",
                        tmp,
                        "--expect-failed",
                        DETAIL,
                    ],
                    launch=lambda a: 1,
                    stop=lambda p: None,
                    run_cli=fake_cli(1, None),
                )
        self.assertEqual(code, 2)

    def test_the_apps_are_stopped_when_the_cli_cannot_be_run(self):
        started, stopped = [], []

        def boom(_suite, _junit):
            raise OSError("no python")

        with self.assertRaises(OSError), redirect_stdout(io.StringIO()):
            ci_suite.main(
                [str(SMOKE), "--app", "a.py"],
                launch=lambda a: started.append(a) or 7,
                stop=stopped.append,
                run_cli=boom,
            )
        self.assertEqual(stopped, [7, 7])

    def test_an_unknown_expected_test_is_a_usage_error_before_anything_starts(self):
        code, started, _, _, text, _ = self.run_main(
            fake_cli(0, None), "--expect-failed", "Nope"
        )
        self.assertEqual((code, started), (2, []))
        self.assertIn("Nope", text)


if __name__ == "__main__":
    unittest.main()
