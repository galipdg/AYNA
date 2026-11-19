"""Fixtures every agent test gets."""

from __future__ import annotations

import pytest

from ayna_agent.playback import rows


class FakeKeyboard:
    """Takes the focus and records the keys, so no unit test presses a real key (#265)."""

    def __init__(self) -> None:
        self.focused: list[object] = []
        self.sent: list[str] = []

    def focus(self, element: object) -> bool:
        self.focused.append(element)
        return True

    def send(self, keys: str) -> None:
        self.sent.append(keys)


@pytest.fixture(autouse=True)
def fake_keyboard(monkeypatch, request):
    """`rows.keyboard` replaced for every test except those marked `windows`."""
    if request.node.get_closest_marker("windows") is not None:
        yield rows.keyboard
        return
    fake = FakeKeyboard()
    monkeypatch.setattr(rows, "keyboard", fake)
    yield fake
