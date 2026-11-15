"""The real player: the agent's own playback, with no Electron and no RPC (#61).

This is the only module of `ayna_cli` that needs Windows, and it is deliberately thin — if a
rule lives here rather than in `ayna_agent.playback`, the CLI and the client would disagree
about what a step does, which is the one thing a CI runner must never introduce.

**One thread.** `UiaDesktop.setup()` makes *the calling thread* able to read UI Automation (it
does the `CoInitializeEx` there), so set-up, every call and `close()` all happen on the thread
that built this object. The RPC server satisfies the same rule with a dedicated `ayna-uia`
thread; here it is simply the main thread. Confirmed against `.github/suite/run_suite.py`
(#67), which this command replaces.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from ayna_cli.suite import SuiteTest

#: How long to wait for the application's window to appear before a test gives up. A cold
#: PySide6 or WPF start on a loaded CI runner is seconds, not milliseconds.
WINDOW_TIMEOUT_S = 60.0

#: How often to look for it while waiting. The same 250 ms playback re-reads a window with, so
#: the command has one polling interval rather than two.
POLL_S = 0.25


class PlaybackUnavailable(Exception):
    """There is no agent here to play with: exit code 2, before any test runs."""


class AgentPlayer:
    """Plays a test against a window of a running application."""

    def __init__(
        self,
        desktop: Any,
        *,
        now: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._desktop = desktop
        self._now = now
        self._sleep = sleep

    @classmethod
    def start(cls) -> AgentPlayer:
        """Build the real backend, or say why this host cannot play anything."""
        try:
            from ayna_agent.recognition.uia import UiaDesktop
        except ImportError as exc:  # pragma: no cover - needs a broken install
            raise PlaybackUnavailable(
                f"the agent could not be imported (pip install -e ./agent): {exc}"
            ) from exc

        desktop = UiaDesktop()
        desktop.setup()
        if not desktop._ready:
            # `setup()` never raises on purpose (a client must still run on macOS); for a CI
            # runner whose whole job is to play steps, it is the end of the command.
            raise PlaybackUnavailable(f"no UI Automation here: {desktop._unavailable}")
        return cls(desktop)

    def close(self) -> None:
        self._desktop.close()

    def play(self, test: SuiteTest) -> list[dict[str, Any]]:
        handle = self._window_for(test)
        # One call for the whole test, which is also why `run_id` is not passed: #54 opens one
        # screenshot directory per `run_steps` call, so one call per test already gives one
        # directory per test. The run id only matters to a caller that sends a step at a time,
        # as #44's client does -- and that parameter is still on #248's branch, so asking for
        # it here would couple this command to an unmerged PR for no gain.
        return self._desktop.run_steps(handle, dict(test.document), dict(test.targets))

    def _window_for(self, test: SuiteTest) -> int:
        """The window the test plays against, waited for until it is there.

        Matched on the Name or the ClassName the suite gives. A value that matches **more than
        one** window is refused rather than guessed at, for the same reason playback refuses an
        ambiguous element: Windows does not promise an order between them, so a guess would act
        on a different window on a different day.
        """
        if test.window_title:
            key, wanted = "title", test.window_title
        elif test.window_class:
            key, wanted = "className", test.window_class
        else:
            raise RuntimeError(
                f"{test.name}: the suite names no window, so there is nothing to play against"
            )

        deadline = self._now() + WINDOW_TIMEOUT_S
        while True:
            matches = [
                window
                for window in self._desktop.list_windows()
                if window.get(key) == wanted
            ]
            if len(matches) == 1:
                return int(matches[0]["handle"])
            if len(matches) > 1:
                raise RuntimeError(
                    f"{test.name}: {len(matches)} windows have {key} {wanted!r}; "
                    "playback never picks one"
                )
            if self._now() >= deadline:
                raise RuntimeError(
                    f"{test.name}: no window with {key} {wanted!r} within "
                    f"{WINDOW_TIMEOUT_S:.0f} s"
                )
            self._sleep(POLL_S)
