"""Local pytest configuration for the trial app.

Kept here instead of a repo-wide pytest.ini because `eval/AGENTS.md` has no
agreed tooling yet; this only affects tests under `eval/apps/trial/`.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make `import app` work without installing the trial app as a package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "windows: needs a real Windows UI session (UI Automation, visible window)",
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Skip windows-only tests elsewhere, so the suite still runs on macOS."""
    if sys.platform == "win32":
        return
    skip_windows = pytest.mark.skip(reason="windows-only test, not running on win32")
    for item in items:
        if "windows" in item.keywords:
            item.add_marker(skip_windows)
