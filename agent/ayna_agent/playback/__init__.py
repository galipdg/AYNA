"""Playing steps against a real window: resolution, actions and the step runner (#26, #40).

The split mirrors the three questions a step asks:

- :mod:`ayna_agent.playback.resolve` -- *which element is this?* Finds every element whose
  descriptor matches a repository object's property set, so that "more than one" is a
  distinguishable answer rather than a silent first match.
- :mod:`ayna_agent.playback.actions` -- *do the thing.* Click and Type through UI Automation
  patterns only. Never coordinates (`agent/AGENTS.md`), so a test stays valid when the window
  moves or the display scaling changes.
- :mod:`ayna_agent.playback.runner` -- *in order, with a deadline.* Walks a step document,
  waits for each target instead of sleeping, and produces one result per step.

Nothing here imports pywinauto at module import, and only two functions need it at all:
`actions.uia_patterns`, which looks a pattern up, and `actions._send_keys`. The first is
injected and both import lazily, and a live element is opaque everywhere else -- so
resolution, the pattern fallback order, the waiting and the stop-on-failure rule are tested
with fakes on macOS, and only the thin UIA layer needs Windows (`agent/AGENTS.md`).
"""

from ayna_agent.playback.actions import ActionFailed, click, type_text
from ayna_agent.playback.resolve import (
    Ambiguous,
    NotFound,
    Resolution,
    Unsupported,
    find_matches,
    resolve,
)
from ayna_agent.playback.runner import StepResult, run_steps

__all__ = [
    "ActionFailed",
    "Ambiguous",
    "NotFound",
    "Resolution",
    "StepResult",
    "Unsupported",
    "click",
    "find_matches",
    "resolve",
    "run_steps",
    "type_text",
]
