"""The REST calls `ayna run` makes, over `urllib` (#61, FR-23).

**No HTTP library.** `requests` and `httpx` would each be a new dependency on a contract frozen
at #52 and one more wheel to carry onto a closed network; the standard library does what four
endpoints need. The same reasoning kept Pillow out of #54.

What it talks to (`docs/api/openapi.yaml`, 1.0):

| | |
|---|---|
| `GET /api/apps` · `GET /api/apps/{id}/tests` · `GET /api/apps/{id}/repo-objects` | what to run |
| `POST /api/runs` | start a run; the answer carries the run's **own copy** of the steps |
| `PUT /api/runs/{runId}/results/{stepIndex}` | one step's result; 201 stored, 200 identical repeat, 409 a different body |
| `POST /api/runs/{runId}/finish` | `passed`, `failed` or `aborted` |

Authentication is `AYNA_SERVER_TOKEN` as a Bearer token (FR-23, NFR-32), never on the command
line, where other processes could read it.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

#: Where the token comes from. Not an option: a command line is readable by other processes
#: (`docs/agent-rpc.md` makes the same point about the agent's session token).
TOKEN_VARIABLE = "AYNA_SERVER_TOKEN"

#: Seconds for one request. A run's own steps have their own, much longer, budgets; this
#: bounds only the HTTP call, so a server that accepted the connection and then went quiet
#: cannot hold a CI job open for ever.
REQUEST_TIMEOUT_S = 30.0


class ServerError(Exception):
    """The server could not be reached, refused us, or answered something unusable.

    Every one of these is FR-23's exit code **2**, including when the tests all passed: a
    result that was not delivered is an operational failure, not a test failure.
    """

    def __init__(self, message: str, *, status: int | None = None) -> None:
        self.status = status
        super().__init__(message)


class Unauthorized(ServerError):
    """401 or 403: no token, a rejected one, or one without the right role."""


class AynaServer:
    """One server, one token, for the length of a run."""

    def __init__(self, base_url: str, token: str, *, opener=None) -> None:
        if not token:
            raise Unauthorized(
                f"no API token: put the CI account's token in {TOKEN_VARIABLE}"
            )
        self.base_url = base_url.rstrip("/")
        self._token = token
        # Injected so the tests drive every status and failure without a socket.
        self._opener = opener or urllib.request.urlopen

    # --- the four calls a run makes ------------------------------------------------------

    def applications(self) -> list[dict[str, Any]]:
        return self._as_list(self._call("GET", "/api/apps"))

    def tests_of(self, app_id: str) -> list[dict[str, Any]]:
        return self._as_list(self._call("GET", f"/api/apps/{_q(app_id)}/tests"))

    def repo_objects_of(self, app_id: str) -> list[dict[str, Any]]:
        return self._as_list(self._call("GET", f"/api/apps/{_q(app_id)}/repo-objects"))

    def versions_of(self, app_id: str) -> list[dict[str, Any]]:
        return self._as_list(self._call("GET", f"/api/apps/{_q(app_id)}/versions"))

    def create_run(self, *, app_version_id: str, test_id: str) -> dict[str, Any]:
        """`POST /api/runs`. The answer carries the run's own copy of the steps.

        That copy, not the test as it stands now, is what the run plays: a test edited while a
        run is in flight must not change what the results mean (ADR *Runs API*).
        """
        body = {"appVersionId": app_version_id, "testId": test_id}
        answer = self._call("POST", "/api/runs", body)
        if not isinstance(answer, dict) or not answer.get("id"):
            raise ServerError(f"POST /api/runs answered no run id: {answer!r}")
        return answer

    def write_result(
        self, run_id: str, step_index: int, result: dict[str, Any]
    ) -> None:
        """`PUT …/results/{stepIndex}`. 201 stored, 200 the same body again.

        A **409** is not a transport hiccup and is never retried: it means a *different* result
        is already stored for this step, so one of the two is wrong and overwriting would hide
        that.
        """
        self._call("PUT", f"/api/runs/{_q(run_id)}/results/{step_index}", result)

    def upload_screenshot(self, run_id: str, step_index: int, png: bytes) -> None:
        """`PUT …/results/{stepIndex}/screenshot`, raw bytes, after the result (#51)."""
        self._call(
            "PUT",
            f"/api/runs/{_q(run_id)}/results/{step_index}/screenshot",
            png,
            content_type="image/png",
        )

    def finish_run(self, run_id: str, status: str) -> None:
        self._call("POST", f"/api/runs/{_q(run_id)}/finish", {"status": status})

    # --- the one place HTTP happens -------------------------------------------------------

    def _call(
        self,
        method: str,
        path: str,
        body: Any = None,
        *,
        content_type: str = "application/json",
    ) -> Any:
        data = None
        if body is not None:
            data = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}{path}", data=data, method=method
        )
        request.add_header("Authorization", f"Bearer {self._token}")
        request.add_header("Accept", "application/json")
        if data is not None:
            request.add_header("Content-Type", content_type)

        try:
            with self._opener(request, timeout=REQUEST_TIMEOUT_S) as answer:
                raw = answer.read()
        except urllib.error.HTTPError as exc:
            raise self._problem(method, path, exc) from exc
        except urllib.error.URLError as exc:
            raise ServerError(
                f"{method} {path}: the server could not be reached: {exc.reason}"
            ) from exc
        except OSError as exc:  # a socket timeout is not a URLError on every platform
            raise ServerError(f"{method} {path}: {exc}") from exc

        if not raw:
            return None
        try:
            return json.loads(raw)
        except ValueError as exc:
            raise ServerError(
                f"{method} {path}: the answer is not JSON: {exc}"
            ) from exc

    def _problem(
        self, method: str, path: str, exc: urllib.error.HTTPError
    ) -> ServerError:
        """Turn the server's RFC 9457 problem into one line worth printing.

        The server promises `detail` names the step, object or field (NFR-15), so it is far
        more use to a CI log than the status alone — but a proxy or a crash can answer
        something else, and then the status is all there is.
        """
        detail = ""
        try:
            problem = json.loads(exc.read())
            if isinstance(problem, dict):
                detail = str(problem.get("detail") or problem.get("title") or "")
        except Exception:  # noqa: BLE001 - any unreadable body leaves `detail` empty
            detail = ""
        message = f"{method} {path}: {exc.code} {exc.reason}"
        if detail:
            message = f"{message}: {detail}"
        if exc.code in (401, 403):
            return Unauthorized(
                f"{message} (is {TOKEN_VARIABLE} the CI account's token?)",
                status=exc.code,
            )
        return ServerError(message, status=exc.code)

    @staticmethod
    def _as_list(answer: Any) -> list[dict[str, Any]]:
        if isinstance(answer, list):
            return [item for item in answer if isinstance(item, dict)]
        # The list endpoints answer an array today; a wrapped page would be a contract change,
        # and guessing at one would hide it.
        raise ServerError(f"expected a list, got {type(answer).__name__}")


def _q(segment: str) -> str:
    """A path segment, escaped. Ids are server-made, but they still cross a URL."""
    return urllib.parse.quote(str(segment), safe="")
