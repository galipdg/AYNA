"""OllamaClient: loopback only, no proxies or redirects, typed failures."""

import socket

import pytest

from ayna_ai.ollama import ModelServerError, ModelTimeout, OllamaClient, is_loopback


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:11434",
        "http://localhost:11434",
        "http://[::1]:11434",
        "http://127.0.0.2:8080/",
        "https://127.0.0.1",
    ],
)
def test_loopback_hosts_are_allowed(url):
    assert is_loopback(url)
    OllamaClient(url)


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com:11434",
        "http://10.0.0.5:11434",
        "http://192.168.1.20:11434",
        "http://127.0.0.1.nip.io:11434",
        "http://localhost.example.com:11434",
        "http://user@example.com",
        "ftp://127.0.0.1",
        "127.0.0.1:11434",
        "",
    ],
)
def test_other_hosts_are_refused(url):
    assert not is_loopback(url)
    with pytest.raises(ValueError, match="closed network"):
        OllamaClient(url)


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
