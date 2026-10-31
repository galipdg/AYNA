"""OllamaClient: loopback only, no proxies or redirects, typed failures."""

import socket

import pytest

from ayna_ai.ollama import (
    ModelServerError,
    ModelTimeout,
    OllamaClient,
    is_loopback,
    loopback_address,
)


@pytest.mark.parametrize(
    ("url", "pinned"),
    [
        ("http://127.0.0.1:11434", "http://127.0.0.1:11434"),
        ("http://localhost:11434", "http://127.0.0.1:11434"),
        ("http://[::1]:11434", "http://[::1]:11434"),
        ("http://ip6-localhost:11434", "http://[::1]:11434"),
        ("http://127.0.0.2:8080/", "http://127.0.0.2:8080"),
        ("https://127.0.0.1", "https://127.0.0.1"),
        # A name is judged by its addresses, not by how it looks.
        ("http://127.0.0.1.nip.io:11434", "http://127.0.0.1:11434"),
    ],
)
def test_loopback_hosts_are_allowed_and_pinned(resolver, url, pinned):
    resolver["ip6-localhost"] = ["::1"]
    resolver["127.0.0.1.nip.io"] = ["127.0.0.1"]
    assert is_loopback(url)
    assert OllamaClient(url).host == pinned


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com:11434",
        "http://10.0.0.5:11434",
        "http://192.168.1.20:11434",
        "http://localhost.example.com:11434",
        "http://user@example.com",
        "http://127.0.0.1:port",
        "ftp://127.0.0.1",
        "127.0.0.1:11434",
        "",
    ],
)
def test_other_hosts_are_refused(resolver, url):
    assert not is_loopback(url)
    with pytest.raises(ValueError, match="closed network"):
        OllamaClient(url)


@pytest.mark.parametrize(
    "addresses",
    [["10.0.0.5"], ["127.0.0.1", "192.168.1.20"], ["::1", "2001:db8::5"]],
)
def test_localhost_that_resolves_off_the_machine_is_refused(resolver, addresses):
    """#142 review: a hosts file can remap `localhost`; the name is not trusted."""
    resolver["localhost"] = addresses
    assert not is_loopback("http://localhost:11434")
    with pytest.raises(ValueError, match="not only to loopback") as caught:
        OllamaClient("http://localhost:11434")
    assert addresses[-1] in str(caught.value)


@pytest.mark.parametrize(
    ("host", "address"),
    [
        ("127.0.0.1", "127.0.0.1"),
        ("127.0.0.2", "127.0.0.2"),
        ("::1", "::1"),
        ("localhost", "127.0.0.1"),  # IPv4 first, whatever the resolver's order
        ("ip6-localhost", "::1"),
    ],
)
def test_loopback_address(resolver, host, address):
    resolver["localhost"] = ["::1", "127.0.0.1"]
    resolver["ip6-localhost"] = ["::1"]
    assert loopback_address(host) == address


@pytest.mark.parametrize(
    ("host", "message"),
    [
        ("", "no host"),
        ("0.0.0.0", "not a loopback address"),
        ("::", "not a loopback address"),
        ("192.168.1.20", "not a loopback address"),
        ("localhost.example.com", "cannot resolve"),
        ("remapped", "10.0.0.5"),
    ],
)
def test_loopback_address_refuses_everything_else(resolver, host, message):
    resolver["remapped"] = ["10.0.0.5"]
    with pytest.raises(ValueError, match=message):
        loopback_address(host)


def test_the_name_is_resolved_once_and_the_checked_address_is_used(
    fake_ollama, resolver
):
    """A name that later resolves elsewhere (DNS rebinding) does not move the client."""
    port = fake_ollama.url.rsplit(":", 1)[1]
    client = OllamaClient(f"http://localhost:{port}", timeout_s=2)
    resolver["localhost"] = ["192.0.2.1"]
    fake_ollama.respond = lambda path, body: (200, {"version": "0.0.0"}, 0, {})
    assert client.version() == "0.0.0"
    assert client.host == fake_ollama.url


def test_chat_posts_json_and_returns_the_answer(fake_ollama):
    fake_ollama.respond = lambda path, body: (
        200,
        {"message": {"content": "{}"}},
        0,
        {},
    )
    answer = OllamaClient(fake_ollama.url).chat({"model": "m", "messages": []})
    assert answer == {"message": {"content": "{}"}}
    assert fake_ollama.requests == [("/api/chat", {"model": "m", "messages": []})]


def test_timeout_is_a_typed_failure(fake_ollama):
    fake_ollama.respond = lambda path, body: (200, {}, 0.5, {})
    with pytest.raises(ModelTimeout):
        OllamaClient(fake_ollama.url, timeout_s=0.1).chat({})


def test_http_error_carries_ollama_message(fake_ollama):
    fake_ollama.respond = lambda path, body: (
        404,
        {"error": "model 'x' not found"},
        0,
        {},
    )
    with pytest.raises(ModelServerError, match="404: model 'x' not found") as caught:
        OllamaClient(fake_ollama.url).chat({})
    assert not isinstance(caught.value, ModelTimeout)


def test_unreachable_server_is_a_server_error():
    with socket.socket() as sock:  # a free port that nobody listens on
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    with pytest.raises(ModelServerError, match="cannot reach"):
        OllamaClient(f"http://127.0.0.1:{port}", timeout_s=2).chat({})


def test_redirects_are_not_followed(fake_ollama):
    fake_ollama.respond = lambda path, body: (
        302,
        {},
        0,
        {"Location": "http://example.com/api/chat"},
    )
    with pytest.raises(ModelServerError, match="302"):
        OllamaClient(fake_ollama.url).chat({})
    assert len(fake_ollama.requests) == 1


def test_proxy_settings_are_ignored(fake_ollama, monkeypatch):
    for name in ("http_proxy", "HTTP_PROXY", "all_proxy", "ALL_PROXY"):
        monkeypatch.setenv(name, "http://192.0.2.1:3128")
    monkeypatch.delenv("no_proxy", raising=False)
    monkeypatch.delenv("NO_PROXY", raising=False)
    fake_ollama.respond = lambda path, body: (200, {"version": "0.0.0"}, 0, {})
    assert OllamaClient(fake_ollama.url, timeout_s=2).version() == "0.0.0"


def test_models_lists_the_pulled_model_names(fake_ollama):
    listing = {"models": [{"name": "qwen3:8b", "size": 1}, {"name": "gemma4:e4b"}]}
    fake_ollama.respond = lambda path, body: (200, listing, 0, {})
    assert OllamaClient(fake_ollama.url).models() == ["qwen3:8b", "gemma4:e4b"]
    assert fake_ollama.requests == [("/api/tags", None)]


@pytest.mark.parametrize("answer", [{}, {"models": "x"}, ["qwen3:8b"]])
def test_models_without_a_list_is_a_server_error(fake_ollama, answer):
    fake_ollama.respond = lambda path, body: (200, answer, 0, {})
    with pytest.raises(ModelServerError, match="model list"):
        OllamaClient(fake_ollama.url).models()
