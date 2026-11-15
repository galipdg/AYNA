"""The exceptions a recognition or playback backend raises for the RPC server to map.

They live here, with no imports, so a backend can raise them without pulling in the
WebSocket server (`websockets`): RQ1's capture (#29) imports the UI Automation backend on
its own. `ayna_agent.rpc` re-exports all four, so `ayna_agent.rpc.WindowNotFound` and the
others keep working. Which error code each one becomes: `docs/agent-rpc.md`, "Errors".
"""

from __future__ import annotations


class WindowNotFound(Exception):
    """No top-level window has the requested handle (it may have closed)."""


class UiaUnavailable(Exception):
    """UI Automation cannot run here: not Windows, or no backend yet."""


class SnapshotTimeout(Exception):
    """The snapshot walk ran out of its time budget before it finished."""


class BadStepDocument(Exception):
    """`runSteps` was given something that is not a step document it can read (#26).

    Only for a document that cannot be read *at all* -- an unknown version, a missing `steps`.
    Everything a single step can get wrong is that step's `failed` result instead."""
