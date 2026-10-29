"""Minimal client for a local Ollama server.

AYNA runs on a closed network, so the client talks only to a loopback address,
ignores proxy settings and refuses redirects: a request can never leave the
machine.
"""

from __future__ import annotations

import ipaddress
import json
import urllib.error
import urllib.request
from urllib.parse import urlparse

DEFAULT_HOST = "http://127.0.0.1:11434"


class ModelServerError(Exception):
    """The model server could not be reached or answered with an error."""


class ModelTimeout(ModelServerError):
    """The model server did not answer within the request timeout."""


def is_loopback(url: str) -> bool:
    """True if `url` is an http(s) URL on this machine (127.0.0.0/8, ::1, localhost)."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return False
    if parsed.hostname == "localhost":
        return True
    try:
        return ipaddress.ip_address(parsed.hostname).is_loopback
    except ValueError:
        return False


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Turn every redirect into an HTTPError: it could point off the machine."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class OllamaClient:
    """Posts JSON to a loopback Ollama server and returns the parsed answer.

    `timeout_s` bounds each blocking socket operation. With `stream: false`
    Ollama sends nothing until the answer is complete, so it bounds the whole
    generation in practice.
    """

    def __init__(self, host: str = DEFAULT_HOST, timeout_s: float = 120.0) -> None:
        if not is_loopback(host):
            raise ValueError(
                f"only a model server on this machine is allowed (closed network): {host!r}"
            )
        self.host = host.rstrip("/")
        self.timeout_s = timeout_s
        self._opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}), _NoRedirect()
        )

    def chat(self, body: dict) -> dict:
        """POST /api/chat. An empty `messages` list only loads the model."""
        return self._request("/api/chat", body)

    def version(self) -> str | None:
        return self._request("/api/version").get("version")

    def _request(self, path: str, body: dict | None = None) -> dict:
        data = None if body is None else json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            self.host + path, data=data, headers={"Content-Type": "application/json"}
        )
        try:
            with self._opener.open(request, timeout=self.timeout_s) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            raise ModelServerError(f"HTTP {exc.code}: {_error_text(exc)}") from exc
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, TimeoutError):
                raise ModelTimeout(f"no answer within {self.timeout_s:g} s") from exc
            raise ModelServerError(f"cannot reach {self.host}: {exc.reason}") from exc
        except TimeoutError as exc:
            raise ModelTimeout(f"no answer within {self.timeout_s:g} s") from exc
        except OSError as exc:
            raise ModelServerError(f"connection to {self.host} failed: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise ModelServerError(f"{path} answered with invalid JSON") from exc


def _error_text(exc: urllib.error.HTTPError) -> str:
    """Ollama puts the reason in {"error": ...}; fall back to the HTTP reason."""
    try:
        return json.load(exc).get("error") or exc.reason
    except (json.JSONDecodeError, OSError, AttributeError):
        return str(exc.reason)
