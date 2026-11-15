"""run_suite.py without Windows: a fake player stands in for the app (#67)."""

from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent))

import run_suite  # noqa: E402

HERE = Path(__file__).parent
REPO = HERE.parents[1]
SMOKE = HERE / "smoke.json"


def passed(index: int) -> dict:
    return {"stepIndex": index, "status": "passed", "durationMs": 5}


def fake_player(results_by_test: dict):
    def factory(_app, _args):
        def play(test):
            outcome = results_by_test[test["name"]]
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

        return play, lambda: None

    return factory


def all_pass(suite: dict) -> dict:
    return {
        t["name"]: [passed(i) for i in range(len(t["steps"]["steps"]))] for t in suite["tests"]
    }


class SmokeSuite(unittest.TestCase):
    def setUp(self):
        self.suite = run_suite.load_suite(SMOKE)

    def test_every_step_document_is_valid_against_the_step_schema(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema is not installed here")
        schema = json.loads((REPO / "schemas" / "step.schema.json").read_text("utf-8"))
        for test in self.suite["tests"]:
            jsonschema.validate(test["steps"], schema)

    def test_every_target_of_a_step_is_defined_and_has_no_coordinates(self):
        for test in self.suite["tests"]:
            for step in test["steps"]["steps"]:
                self.assertIn(step["target"], test["targets"], test["name"])
            text = json.dumps(test["targets"])
            for forbidden in ('"bounds"', '"dpi"', '"x"', '"y"'):
                self.assertNotIn(forbidden, text)

    def test_the_ids_are_the_sample_apps_own(self):
        """A renamed objectName in the sample app must fail here, not only on Windows."""
        source = (REPO / "eval" / "apps" / "sample" / "windows.py").read_text("utf-8")
        for test in self.suite["tests"]:
            for target in test["targets"].values():
                last = target["properties"]["automationId"].rsplit(".", 1)[-1]
                self.assertIn(f'"{last}"', source, last)

    def test_the_expected_texts_are_the_sample_apps_own(self):
        texts = (REPO / "eval" / "apps" / "sample" / "texts.py").read_text("utf-8")
        self.assertIn('LOGIN_WELCOME = "Hoş geldiniz, {user}!"', texts)
        self.assertIn('DETAIL_NAME_REQUIRED = "Ad alanı zorunlu"', texts)


class Main(unittest.TestCase):
    def run_main(self, results, *extra):
        with tempfile.TemporaryDirectory() as tmp:
            junit = Path(tmp) / "out" / "junit.xml"
            stdout, stderr = io.StringIO(), io.StringIO()
            with (
                redirect_stdout(stdout),
                redirect_stderr(stderr),
                mock.patch.dict("os.environ", {"GITHUB_STEP_SUMMARY": ""}),
            ):
                code = run_suite.main(
                    [str(SMOKE), "--app", "app.py", "--junit", str(junit), *extra],
                    player_factory=fake_player(results),
                )
            xml = ET.fromstring(junit.read_bytes()) if junit.exists() else None
            return code, xml, stdout.getvalue(), stderr.getvalue()

    def setUp(self):
        self.suite = run_suite.load_suite(SMOKE)
        self.results = all_pass(self.suite)

    def test_all_passed_exits_0_with_one_testcase_each(self):
        code, xml, out, _ = self.run_main(self.results)
        self.assertEqual(code, 0)
        suite = xml.find("testsuite")
        self.assertEqual(suite.get("tests"), "2")
        self.assertEqual(suite.get("failures"), "0")
        self.assertEqual(len(suite.findall("testcase")), 2)
        self.assertIsNone(suite.find("testcase/failure"))
        self.assertIn("Login succeeds", out)

    def test_a_failed_step_fails_the_job_and_names_the_step(self):
        self.results["Login succeeds"][3] = {
            "stepIndex": 3,
            "status": "failed",
            "durationMs": 10,
            "message": "name should contain 'Hoş geldiniz', it is 'Oturum kapatıldı, admin'",
        }
        code, xml, _, _ = self.run_main(self.results)
        self.assertEqual(code, 1)
        failure = xml.find("testsuite/testcase[@name='Login succeeds']/failure")
        self.assertIn("Oturum kapatıldı", failure.get("message"))
        self.assertIn("step 3 Verify login.statusLabel: failed", failure.text)
        self.assertEqual(xml.find("testsuite").get("failures"), "1")

    def test_an_expected_failure_passes_the_job_but_stays_failed_in_the_xml(self):
        name = "Detail form refuses an empty name"
        self.results[name][2] = {"stepIndex": 2, "status": "failed", "durationMs": 1}
        code, xml, out, _ = self.run_main(self.results, "--expect-failed", name)
        self.assertEqual(code, 0)
        self.assertIsNotNone(xml.find(f"testsuite/testcase[@name='{name}']/failure"))
        self.assertIn("| failed |", out)

    def test_an_expected_failure_that_passes_fails_the_job(self):
        """A bug build the suite does not catch is exactly what this job must report."""
        code, _, _, _ = self.run_main(self.results, "--expect-failed", "Login succeeds")
        self.assertEqual(code, 1)

    def test_an_error_starting_the_app_is_not_an_expected_failure(self):
        self.results["Login succeeds"] = RuntimeError("no LoginWindow window within 60 s")
        code, xml, _, _ = self.run_main(self.results, "--expect-failed", "Login succeeds")
        self.assertEqual(code, 1)
        error = xml.find("testsuite/testcase[@name='Login succeeds']/error")
        self.assertIn("no LoginWindow", error.get("message"))
        self.assertEqual(xml.find("testsuite").get("errors"), "1")

    def test_an_unknown_expected_failure_is_a_usage_error(self):
        code, xml, _, err = self.run_main(self.results, "--expect-failed", "No such test")
        self.assertEqual(code, 2)
        self.assertIsNone(xml)
        self.assertIn("No such test", err)

    def test_no_step_results_is_not_a_pass(self):
        self.results["Login succeeds"] = []
        code, _, _, _ = self.run_main(self.results)
        self.assertEqual(code, 1)


class LoadSuite(unittest.TestCase):
    def load(self, content) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "suite.json"
            path.write_text(content if isinstance(content, str) else json.dumps(content))
            run_suite.load_suite(path)

    def test_refuses_bad_files(self):
        test = json.loads(SMOKE.read_text("utf-8"))["tests"][0]
        for content in ("not json", {"tests": []}, {"tests": [{"name": "x"}]}, {"tests": [test, test]}):
            with self.subTest(content=str(content)[:40]), self.assertRaises(run_suite.SuiteError):
                self.load(content)


if __name__ == "__main__":
    unittest.main()
