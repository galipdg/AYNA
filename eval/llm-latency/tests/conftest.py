"""Local pytest configuration for the NFR-12 latency harness (#162).

Puts `eval/llm-latency/` and `ai/` on `sys.path` so `import run` and `import ayna_ai` work
without installing anything; this only affects tests under `eval/llm-latency/`. The folder
name has a hyphen, so it is a script directory and never an importable package -- which is
also why `run.py` cannot simply be imported by path from the test module.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
for path in (HERE, HERE.parents[1] / "ai"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
