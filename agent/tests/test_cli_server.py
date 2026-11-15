"""#61's REST client and the `ayna run` command line, with no socket and no desktop.

`AynaServer` takes its opener as a seam, so every status the contract allows — 201, 200, 401,
409, a connection that never opens — is driven here. The point of most of these is not the happy
path but the message: a CI log that says "409" and nothing else costs someone an afternoon.
"""

from __future__ import annotations

import io
import json
import urllib.error

import pytest

from ayna_cli.cli import _targets_from, _window_title_in, console_entry, main
from ayna_cli.exits import OPERATIONAL_FAILURE
from ayna_cli.server import (
    TOKEN_VARIABLE,
    AynaServer,
    ServerError,
    Unauthorized,
)


class FakeAnswer(io.BytesIO):
    """What `urlopen` yields: a context manager you can `.read()`."""

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False


def opener(answers):
    """An opener that records requests and replies from `answers`, in order."""
    sent = []

    def open_it(request, timeout=None):
        sent.append(request)
        answer = answers.pop(0) if answers else b""
        if isinstance(answer, Exception):
            raise answer
        return FakeAnswer(
            answer if isinstance(answer, bytes) else json.dumps(answer).encode()
        )

    open_it.sent = sent
    return open_it


def http_error(code, detail=None):
    body = json.dumps({"detail": detail}).encode() if detail else b""
    return urllib.error.HTTPError(
        "http://ayna/api/runs", code, "Problem", {}, io.BytesIO(body)
    )


def server(answers, token="tok"):
    return AynaServer("http://ayna:8080/", token, opener=opener(answers))


# --- the token ------------------------------------------------------------------------------


def test_a_server_without_a_token_is_refused_before_any_request():
    with pytest.raises(Unauthorized, match=TOKEN_VARIABLE):
        AynaServer("http://ayna:8080", "")


def test_every_request_carries_the_bearer_token():
    s = server([[{"id": "a1", "name": "AYNA Trial"}]])
    s.applications()
    assert s._opener.sent[0].get_header("Authorization") == "Bearer tok"


def test_the_base_urls_trailing_slash_does_not_double_up():
    s = server([[]])
    s.applications()
    assert s._opener.sent[0].full_url == "http://ayna:8080/api/apps"


# --- the calls a run makes --------------------------------------------------------------------


def test_creating_a_run_sends_the_version_and_the_test():
    s = server([{"id": "r1", "status": "running"}])
    run = s.create_run(app_version_id="v1", test_id="t1")

    assert run["id"] == "r1"
    request = s._opener.sent[0]
    assert request.method == "POST"
    assert json.loads(request.data) == {"appVersionId": "v1", "testId": "t1"}


def test_a_run_without_an_id_is_an_error_rather_than_a_crash_later():
    s = server([{"status": "running"}])
    with pytest.raises(ServerError, match="no run id"):
        s.create_run(app_version_id="v1", test_id="t1")


def test_a_result_goes_to_its_own_step_index():
    s = server([{"stored": True}])
    s.write_result("r1", 3, {"stepIndex": 3, "status": "passed", "durationMs": 1})
    request = s._opener.sent[0]
    assert request.full_url.endswith("/api/runs/r1/results/3")
    assert request.method == "PUT"


def test_a_screenshot_goes_as_raw_png_not_json():
    s = server([b""])
    s.upload_screenshot("r1", 2, b"\x89PNG\r\n\x1a\n...")
    request = s._opener.sent[0]
    assert request.full_url.endswith("/api/runs/r1/results/2/screenshot")
    assert request.get_header("Content-type") == "image/png"
    assert request.data.startswith(b"\x89PNG")


def test_an_id_with_a_slash_in_it_cannot_escape_its_path_segment():
    s = server([b""])
    s.finish_run("../../apps", "passed")
    assert "/api/runs/..%2F..%2Fapps/finish" in s._opener.sent[0].full_url


# --- what goes wrong --------------------------------------------------------------------------


def test_a_401_says_which_variable_to_look_at():
    s = server([http_error(401)])
    with pytest.raises(Unauthorized, match=TOKEN_VARIABLE):
        s.applications()


def test_a_403_is_also_unauthorized():
    s = server([http_error(403, "the CI account may not write runs")])
    with pytest.raises(Unauthorized, match="may not write runs"):
        s.applications()


def test_a_409_keeps_the_servers_own_explanation():
    """The server promises `detail` names the step or field (NFR-15); it is the useful part."""
    s = server([http_error(409, "step 2 already has a different result")])
    with pytest.raises(ServerError, match="already has a different result") as caught:
        s.write_result("r1", 2, {"stepIndex": 2})
    assert caught.value.status == 409


def test_a_problem_body_that_cannot_be_read_still_gives_the_status():
    s = server(
        [urllib.error.HTTPError("u", 500, "Server Error", {}, io.BytesIO(b"<html>"))]
    )
    with pytest.raises(ServerError, match="500"):
        s.applications()


def test_a_server_that_cannot_be_reached_says_so_in_one_line():
    s = server([urllib.error.URLError("connection refused")])
    with pytest.raises(ServerError, match="could not be reached"):
        s.applications()


def test_an_answer_that_is_not_json_is_an_error():
    s = server([b"<html>not json</html>"])
    with pytest.raises(ServerError, match="not JSON"):
        s.applications()


def test_a_list_endpoint_that_answers_an_object_is_an_error():
    """Guessing at a wrapped page would hide a contract change rather than report it."""
    s = server([{"items": []}])
    with pytest.raises(ServerError, match="expected a list"):
        s.applications()


# --- turning the server's answers into a suite ------------------------------------------------


def test_repository_objects_become_targets_with_their_fallbacks():
    targets = _targets_from(
        [
            {
                "name": "login.loginButton",
                "primary": {"automationId": "b"},
                "fallback": {"name": "Giriş"},
            },
            {"name": "login.userNameInput", "primary": {"automationId": "u"}},
            {"name": "broken", "primary": "not an object"},
            {"primary": {"automationId": "x"}},
        ]
    )
    assert targets["login.loginButton"] == {
        "properties": {"automationId": "b"},
        "fallback": {"name": "Giriş"},
    }
    assert targets["login.userNameInput"] == {"properties": {"automationId": "u"}}
    assert "broken" not in targets, "an object with no usable primary set is skipped"


def test_the_window_comes_from_a_targets_window_title():
    """#40's rule, and the reason a server suite can sometimes do without `--window`."""
    targets = {
        "login.userNameInput": {"properties": {"automationId": "u"}},
        "login.loginButton": {"properties": {"windowTitle": "Giriş"}},
    }
    assert _window_title_in(targets) == "Giriş"


def test_a_window_title_on_the_fallback_set_counts_too():
    targets = {
        "a": {
            "properties": {"automationId": "a"},
            "fallback": {"windowTitle": "Ayarlar"},
        }
    }
    assert _window_title_in(targets) == "Ayarlar"


def test_no_window_title_anywhere_is_none_rather_than_a_guess():
    """What the trial app's five seeded objects actually look like, so `--window` is needed."""
    targets = {
        "login.userNameInput": {
            "properties": {"automationId": "QApplication.loginWindow.usernameInput"}
        },
        "login.loginButton": {
            "properties": {"automationId": "QApplication.loginWindow.loginButton"}
        },
    }
    assert _window_title_in(targets) is None


# --- the command line -------------------------------------------------------------------------


def test_a_suite_file_that_cannot_be_read_exits_two(tmp_path, capsys):
    out = io.StringIO()
    assert (
        main(["--from-file", str(tmp_path / "nowhere.json")], out=out)
        == OPERATIONAL_FAILURE
    )
    assert "error:" in out.getvalue()


def test_a_server_without_a_suite_name_is_a_usage_error():
    with pytest.raises(SystemExit) as caught:
        main(["--server", "http://ayna:8080"])
    assert caught.value.code == 2, "argparse's usage exit, which is also FR-23's code 2"


def test_neither_source_is_a_usage_error():
    with pytest.raises(SystemExit):
        main([])


def test_a_server_run_without_a_token_exits_two(monkeypatch):
    monkeypatch.delenv(TOKEN_VARIABLE, raising=False)
    out = io.StringIO()
    code = main(["--server", "http://ayna:8080", "--suite", "AYNA Trial"], out=out)
    assert code == OPERATIONAL_FAILURE
    assert TOKEN_VARIABLE in out.getvalue()


def test_the_console_entry_wants_the_run_verb(capsys):
    assert console_entry(["sprint"]) == OPERATIONAL_FAILURE
    assert "only command is `run`" in capsys.readouterr().out


def test_the_console_entry_with_nothing_prints_usage(capsys):
    assert console_entry([]) == OPERATIONAL_FAILURE
    assert "usage: ayna run" in capsys.readouterr().out
