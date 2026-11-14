"""Local pytest configuration for the sample app.

Puts the app folder on `sys.path` and skips `@pytest.mark.windows` tests off Windows; this
affects only tests under `eval/apps/sample/`.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make `import model`, `import texts`, `import windows` and `import uia_check` work without
# installing the sample app as a package, exactly as `sample_app.py` itself does. This
# insert lasts for the whole pytest process and the trial app's conftest does the same, so
# every module name under `eval/` has to be unique -- see `eval/AGENTS.md`.
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
