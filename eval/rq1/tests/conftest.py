"""Local pytest configuration for the RQ1 harness.

Puts `eval/rq1/` and `agent/` on `sys.path` so `import measure` and `import ayna_agent` work
without installing anything; this only affects tests under `eval/rq1/`. `measure.py` adds
`agent/` itself when it is run as a script, but a test module's own imports are sorted by the
linter and may come before `import measure`, so the path cannot depend on that order.
"""

from __future__ import annotations

import sys
from pathlib import Path

RQ1 = Path(__file__).resolve().parents[1]
for path in (RQ1, RQ1.parents[1] / "agent"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
