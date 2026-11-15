"""Fakes shared by #63's triage and decision-log tests.

A module of its own rather than one test file importing another: pytest puts `tests/` on
`sys.path` (which is why `import grids` works next door), but `tests` is not a package, so
`from tests.x import y` collects locally and fails in CI, where the rootdir is `agent/`.
Found exactly that way on PR #251.
"""

from __future__ import annotations

import json
from pathlib import Path

TRIAL_TREE = Path(__file__).resolve().parent / "data" / "trial-app-tree.json"

USERNAME = "QApplication.loginWindow.usernameInput"
LOGIN = "QApplication.loginWindow.loginButton"

#: Targets that reach each failure the triage has to tell apart.
TARGETS = {
    "login.userNameInput": {"properties": {"automationId": USERNAME}},
    "login.loginButton": {"properties": {"automationId": LOGIN}},
    "login.gone": {"properties": {"automationId": "no-such-element"}},
    "login.ambiguous": {"properties": {"controlType": "Edit"}},
    "login.unmatchable": {"properties": {"patternSalad": "nope"}},
}


class Window:
    """The same fake #26's tests use: the real trial-app tree from #11."""

    def __init__(self) -> None:
        self.content = json.loads(TRIAL_TREE.read_text(encoding="utf-8"))
        self.reads = 0

    def read_tree(self):
        self.reads += 1
        return self.content, [f"element-{i}" for i in range(len(self.content))]


class Clock:
    """Time the fake `sleep` advances, so a wait is tested without waiting."""

    def __init__(self) -> None:
        self.t = 0.0

    def now(self) -> float:
        return self.t

    def sleep(self, seconds: float) -> None:
        self.t += seconds
