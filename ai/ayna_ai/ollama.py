"""Minimal client for a local Ollama server.

AYNA runs on a closed network, so the client talks only to a loopback address,
ignores proxy settings and refuses redirects: a request can never leave the
machine. A host name is not trusted as such: it is resolved once, every
address it resolves to must be loopback, and the client then connects to the
checked address, never to the name.
"""

from __future__ import annotations

import ipaddress
import json
import socket
import urllib.error
import urllib.request
from urllib.parse import urlparse, urlunparse

DEFAULT_HOST = "http://127.0.0.1:11434"


class ModelServerError(Exception):
    """The model server could not be reached or answered with an error."""


class ModelTimeout(ModelServerError):
    """The model server did not answer within the request timeout."""


def loopback_address(host: str) -> str:
    """The loopback address to use for `host`; ValueError if it is not on this machine.

    A literal IP must be a loopback address (127.0.0.0/8, ::1). A name,
    `localhost` included, is resolved with the system resolver, and every
    address it resolves to must be loopback: a hosts file or DNS entry can map
    any name off the machine (#142 review). Of several addresses the first IPv4
    one is chosen: Ollama and the AYNA server use IPv4 loopback by default.
    Also used for the AI service's own listen address.
    """
    if not host:
        raise ValueError("no host given")
    try:
        found = [ipaddress.ip_address(host)]
    except ValueError:
        found = _resolve(host)
        outside = [str(a) for a in found if not a.is_loopback]
        if outside:
            raise ValueError(
                f"{host!r} resolves to {', '.join(outside)}, not only to loopback "
                "addresses"
            ) from None
    if not found[0].is_loopback:
        raise ValueError(f"{host!r} is not a loopback address")
    return str(next((a for a in found if a.version == 4), found[0]))


def _resolve(host: str) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    try:
        infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"cannot resolve {host!r}: {exc}") from None
    found = list(dict.fromkeys(ipaddress.ip_address(info[4][0]) for info in infos))
    if not found:
        raise ValueError(f"{host!r} resolves to no address")
    return found


def loopback_url(url: str) -> str:
    """`url` with its host replaced by `loopback_address(host)`; ValueError otherwise.

    Only an http(s) URL with a host is accepted.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("not an http(s) URL with a host")
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError(f"invalid port: {exc}") from None
    address = loopback_address(parsed.hostname)
    netloc = f"[{address}]" if ":" in address else address
    if port is not None:
        netloc += f":{port}"
    if "@" in parsed.netloc:
        netloc = parsed.netloc.rsplit("@", 1)[0] + "@" + netloc
    return urlunparse(parsed._replace(netloc=netloc))


def is_loopback(url: str) -> bool:
    """True if `url` is an http(s) URL whose host is only ever this machine."""
    try:
        loopback_url(url)
    except ValueError:
        return False
    return True


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Turn every redirect into an HTTPError: it could point off the machine."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class OllamaClient:
    """Posts JSON to a loopback Ollama server and returns the parsed answer.

    `host` is checked and pinned once, here (`loopback_url`): `self.host` is the
    URL with the checked address, so a name is never looked up again.

    `timeout_s` bounds each blocking socket operation. With `stream: false`
    Ollama sends nothing until the answer is complete, so it bounds the whole
    generation in practice.
    """

    def __init__(self, host: str = DEFAULT_HOST, timeout_s: float = 120.0) -> None:
        try:
            pinned = loopback_url(host)
        except ValueError as exc:
            raise ValueError(
                "only a model server on this machine is allowed (closed network): "
                f"{host!r}: {exc}"
            ) from None
        self.host = pinned.rstrip("/")
        self.timeout_s = timeout_s
        self._opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}), _NoRedirect()
        )

    def chat(self, body: dict, timeout_s: float | None = None) -> dict:
        """POST /api/chat. An empty `messages` list only loads the model.

        `timeout_s` replaces the client's timeout for this call (the service
        passes what is left of its per-request deadline).
        """
        return self._request("/api/chat", body, timeout_s)

    def version(self) -> str | None:
        return self._request("/api/version").get("version")

    def models(self) -> list[str]:
        """Names of the models pulled on the server (GET /api/tags)."""
        answer = self._request("/api/tags")
        listing = answer.get("models") if isinstance(answer, dict) else None
        if not isinstance(listing, list):
            raise ModelServerError("/api/tags answered without a model list")
        return [m["name"] for m in listing if isinstance(m, dict) and "name" in m]

    def _request(
        self, path: str, body: dict | None = None, timeout_s: float | None = None
    ) -> dict:
        timeout = self.timeout_s if timeout_s is None else timeout_s
        data = None if body is None else json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            self.host + path, data=data, headers={"Content-Type": "application/json"}
        )
        try:
            with self._opener.open(request, timeout=timeout) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            raise ModelServerError(f"HTTP {exc.code}: {_error_text(exc)}") from exc
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, TimeoutError):
                raise ModelTimeout(f"no answer within {timeout:g} s") from exc
            raise ModelServerError(f"cannot reach {self.host}: {exc.reason}") from exc
        except TimeoutError as exc:
            raise ModelTimeout(f"no answer within {timeout:g} s") from exc
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
