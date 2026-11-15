"""#61's suite file: what it accepts, and what it refuses rather than half-runs.

Every rejection here is exit code **2**, not 1. A suite file with a typo is a misconfigured
job, not a broken application, and running four tests of five would blur exactly the
distinction the two codes exist to draw — so the reader raises instead of skipping.
"""

from __future__ import annotations

import json

import pytest

from ayna_cli.suite import SuiteError, read_suite_file

GOOD = {
    "suite": "smoke",
    "tests": [
        {
            "name": "Login succeeds",
            "scenario": "SC-14",
            "window": {"title": "Giriş"},
            "targets": {
                "login.loginButton": {
                    "properties": {"automationId": "loginButton"},
                    "fallback": {"name": "Giriş", "controlType": "Button"},
                }
            },
            "steps": {
                "version": "0.2",
                "steps": [{"keyword": "Click", "target": "login.loginButton"}],
            },
        }
    ],
}


def write(tmp_path, suite, name="suite.json"):
    path = tmp_path / name
    path.write_text(json.dumps(suite), encoding="utf-8")
    return path


def test_a_good_suite_reads_into_the_shape_playback_wants(tmp_path):
    suite = read_suite_file(write(tmp_path, GOOD))

    assert suite.name == "smoke"
    assert len(suite.tests) == 1
    test = suite.tests[0]
    assert test.name == "Login succeeds"
    assert test.scenario == "SC-14"
    assert test.window_title == "Giriş"
    assert test.test_id is None, (
        "a file suite has no server ids, so it cannot post results"
    )
    assert test.targets["login.loginButton"]["properties"] == {
        "automationId": "loginButton"
    }
    assert test.document["steps"][0]["keyword"] == "Click"


def test_the_suite_name_falls_back_to_the_file_name(tmp_path):
    without = {k: v for k, v in GOOD.items() if k != "suite"}
    assert read_suite_file(write(tmp_path, without, "nightly.json")).name == "nightly"


def test_turkish_text_survives_the_read(tmp_path):
    """UTF-8 everywhere (NFR-16); a window titled Giriş must not come back mangled."""
    suite = read_suite_file(write(tmp_path, GOOD))
    assert suite.tests[0].window_title == "Giriş"
    assert suite.tests[0].targets["login.loginButton"]["fallback"]["name"] == "Giriş"


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"tests": []}, "non-empty 'tests'"),
        ({"tests": "nope"}, "non-empty 'tests'"),
        ({"tests": ["not an object"]}, "is not an object"),
    ],
)
def test_a_suite_without_runnable_tests_is_refused(tmp_path, change, message):
    with pytest.raises(SuiteError, match=message):
        read_suite_file(write(tmp_path, {**GOOD, **change}))


def test_a_test_without_a_name_is_refused(tmp_path):
    bad = {"tests": [{k: v for k, v in GOOD["tests"][0].items() if k != "name"}]}
    with pytest.raises(SuiteError, match="has no 'name'"):
        read_suite_file(write(tmp_path, bad))


def test_two_tests_of_one_name_are_refused(tmp_path):
    """The name is how a result is reported, so two of them make both ambiguous."""
    bad = {"tests": [GOOD["tests"][0], GOOD["tests"][0]]}
    with pytest.raises(SuiteError, match="two tests are named"):
        read_suite_file(write(tmp_path, bad))


def test_a_test_without_a_step_document_is_refused(tmp_path):
    bad = {"tests": [{k: v for k, v in GOOD["tests"][0].items() if k != "steps"}]}
    with pytest.raises(SuiteError, match="no 'steps' document"):
        read_suite_file(write(tmp_path, bad))


def test_a_step_whose_target_the_suite_never_defines_is_refused(tmp_path):
    """Without a server there is no repository, so that step could only ever fail."""
    bad = json.loads(json.dumps(GOOD))
    bad["tests"][0]["steps"]["steps"].append(
        {"keyword": "Click", "target": "login.ghost"}
    )
    with pytest.raises(SuiteError, match="no target for 'login.ghost'"):
        read_suite_file(write(tmp_path, bad))


def test_a_file_that_is_not_json_is_refused(tmp_path):
    path = tmp_path / "suite.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(SuiteError, match="not JSON"):
        read_suite_file(path)


def test_a_file_that_is_not_there_is_refused(tmp_path):
    with pytest.raises(SuiteError):
        read_suite_file(tmp_path / "nowhere.json")


def test_the_projects_own_smoke_suite_reads():
    """`.github/suite/smoke.json` is the shape I told omer this command would keep (PR #249).

    If #67's stand-in and this reader ever disagree, the nightly job and `ayna run` would run
    different things, which is the one thing replacing the stand-in must not do.
    """
    from pathlib import Path

    smoke = Path(__file__).resolve().parents[2] / ".github" / "suite" / "smoke.json"
    if not smoke.exists():  # pragma: no cover - only before #249 merges
        pytest.skip("#249 has not merged yet")
    suite = read_suite_file(smoke)
    assert [test.name for test in suite.tests] == [
        "Login succeeds",
        "Detail form refuses an empty name",
    ]
    assert all(test.targets for test in suite.tests)


#: The exact shape `.github/suite/smoke.json` uses (#67's stand-in, PR #249), inline so the
#: compatibility is tested whether or not that PR has merged into this branch.
SMOKE_SHAPE = {
    "suite": "smoke",
    "tests": [
        {
            "name": "Login succeeds",
            "scenario": "SC-14",
            "launch": ["--screen", "login"],
            "window": {"className": "LoginWindow"},
            "targets": {
                "login.userNameInput": {
                    "properties": {"automationId": "QApplication.login.userNameInput"},
                    "fallback": {
                        "nearestLabel": "Kullanıcı adı",
                        "controlType": "Edit",
                    },
                }
            },
            "steps": {
                "version": "0.2",
                "steps": [
                    {
                        "keyword": "Type",
                        "target": "login.userNameInput",
                        "value": "admin",
                    }
                ],
            },
        }
    ],
}


def test_the_stand_ins_suite_shape_reads_unchanged(tmp_path):
    """I told omer on PR #249 that `ayna run` would keep this shape, so it is pinned here."""
    suite = read_suite_file(write(tmp_path, SMOKE_SHAPE))
    test = suite.tests[0]
    assert test.name == "Login succeeds"
    assert test.window_class == "LoginWindow", "the stand-in names windows by ClassName"
    assert test.window_title is None
    assert (
        test.targets["login.userNameInput"]["fallback"]["nearestLabel"]
        == "Kullanıcı adı"
    )


def test_launch_is_read_without_complaint_even_though_this_command_ignores_it(tmp_path):
    """`launch` is the stand-in starting the app itself; `ayna run` attaches to a window.

    Accepting and ignoring it is deliberate: one suite file should work with both while #67's
    job still calls the stand-in.
    """
    suite = read_suite_file(write(tmp_path, SMOKE_SHAPE))
    assert suite.tests[0].name == "Login succeeds"


def test_a_window_named_two_ways_is_refused(tmp_path):
    bad = json.loads(json.dumps(SMOKE_SHAPE))
    bad["tests"][0]["window"] = {"title": "Giriş", "className": "LoginWindow"}
    with pytest.raises(SuiteError, match="not both"):
        read_suite_file(write(tmp_path, bad))
