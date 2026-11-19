"""Fixtures every agent test gets."""

from __future__ import annotations

import pytest

from ayna_agent.playback import runner


@pytest.fixture(autouse=True)
def _fresh_invoke_spacing():
    """Start each test with no recent `Invoke` on record (#264).

    The runner keeps one process-wide record so it survives between the client's one-step
    runs. Tests inject a fake clock per run, so a mark left by one test would make an
    unrelated later test wait, or not, depending on the order they ran in.
    """
    runner.INVOKE_SPACING.clear()
    yield
    runner.INVOKE_SPACING.clear()
