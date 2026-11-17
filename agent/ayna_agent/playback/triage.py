"""Which of FR-35's categories a failed step belongs to (#63).

**One function, not a `category=` at each of the twenty-odd `done(FAILED, …)` sites.** This
rule decides what RQ2's flaky rate and RQ5's healing numbers are computed over, so it has to be
readable in one place; spread across the runner it would be a rule nobody could check.

The five values and their meanings are ADR `2026-11-15-failure-category` (#240) and TBD-5, and
they are already in `schemas/agent-rpc.schema.json` 1.1 and in the server, the WebSocket
messages and the HTML report. This module is the half that was missing: nothing filled them.

## What is deliberately not categorised

The contract says `category` is absent when the agent cannot tell, and the ADR left the hard
half to this issue:

> whether those two cases get a category of their own, or one of the five, is Hasan's call

**They stay out of the five.** A keyword this agent has not implemented, a step document it
refuses, a property set it cannot match on, a provider that refuses an action — none of them is
evidence *about the application under test*, and this field is not decoration: RQ2 and RQ5 are
computed from it. A `timeout` that was really "this agent has no `SelectRow` yet" would measure
AYNA's unfinished state and call it the application's flakiness, and once the two are in one
enum no later analysis can pull them apart.

So the contract keeps the five, and :func:`reason_for` gives the **decision log** a finer name
for every failure including those — which is where labelling happens anyway (#63's second
criterion). A sixth contract value (`notAttempted`) is proposed on the issue rather than taken
here: it is a minor version on two shared schemas and needs the other two.
"""

from __future__ import annotations

from ayna_agent.errors import SnapshotTimeout
from ayna_agent.playback.actions import ActionFailed
from ayna_agent.playback.checkpoint import CheckpointError, Unreadable
from ayna_agent.playback.items import ITEM_NOT_FOUND, SelectFailed
from ayna_agent.playback.resolve import Ambiguous, NotFound, NotReady, Unsupported
from ayna_agent.playback.rows import (
    ROW_NOT_FOUND,
    RowError,
    RowFailed,
    RowsUnavailable,
)

#: FR-35's five, as `schemas/agent-rpc.schema.json` `$defs/failureCategory` spells them.
ELEMENT_NOT_FOUND = "elementNotFound"
UNEXPECTED_WINDOW = "unexpectedWindow"
ASSERTION_FAILED = "assertionFailed"
TIMEOUT = "timeout"
SEARCH_INCOMPLETE = "searchIncomplete"

CATEGORIES: frozenset[str] = frozenset(
    {
        ELEMENT_NOT_FOUND,
        UNEXPECTED_WINDOW,
        ASSERTION_FAILED,
        TIMEOUT,
        SEARCH_INCOMPLETE,
    }
)

#: Finer than `CATEGORIES` and never absent: what the decision log records. The first five
#: mirror the contract; the rest are the failures that are **not** about the application, kept
#: apart so a later analysis can exclude them rather than guess.
REFUSED_STEP = "refusedStep"
"""The agent would not attempt the step: a keyword it has not implemented, or a step document
it cannot read (no target, no value, a bad timeout, a malformed checkpoint or row address)."""

REFUSED_PROPERTIES = "refusedProperties"
"""`Unsupported`: the repository object asks to be matched on a property playback cannot match
on. The element may well be there; nobody looked."""

ACTION_REFUSED = "actionRefused"
"""The element was found and ready and the provider refused the action anyway — no `Invoke`,
a `SetValue` that would not take, a list that would not select."""

UNREADABLE_PROPERTY = "unreadableProperty"
"""A checkpoint could not read the property it was asked about, so it neither held nor failed."""


def category_for(error: BaseException) -> str | None:
    """One of FR-35's five, or `None` when the failure is not about the application.

    `None` is a real answer here and not a gap: see the module docstring. The caller writes no
    `category` at all in that case, which is what the contract means by absent.
    """
    if isinstance(error, SnapshotTimeout):
        # The window could not be read inside its budget, so the search never finished. This
        # must not read as `elementNotFound`: nothing was searched, so "not found" would be a
        # claim the agent is in no position to make, and #73 refuses to heal after one.
        return SEARCH_INCOMPLETE
    if isinstance(error, (NotFound, Ambiguous)):
        # Ambiguous is `elementNotFound` by the ADR's own words: no *unique* element matched,
        # and playback never picks one.
        return ELEMENT_NOT_FOUND
    if isinstance(error, NotReady):
        # TBD-5's own wording for `timeout`: "an element matched but did not become visible
        # and enabled in time". Not `elementNotFound` -- it was found, which is the difference
        # a tester needs: one means the locator is wrong, the other means the app was busy.
        return TIMEOUT
    if isinstance(error, RowFailed) and error.kind == ROW_NOT_FOUND:
        # A row the step asked for is not in the grid: the same shape of failure as an element
        # that is not there, one level down. A row the application *refused to select* is a
        # different finding and falls through to `actionRefused`, which is why `RowFailed`
        # carries a `kind` at all.
        return ELEMENT_NOT_FOUND
    if isinstance(error, SelectFailed) and error.kind == ITEM_NOT_FOUND:
        return ELEMENT_NOT_FOUND
    return None


def reason_for(error: BaseException) -> str:
    """The decision log's finer name. Never `None`, so every failed step *is* classified."""
    category = category_for(error)
    if category is not None:
        return category
    if isinstance(error, Unsupported):
        return REFUSED_PROPERTIES
    if isinstance(error, Unreadable):
        return UNREADABLE_PROPERTY
    if isinstance(error, (ActionFailed, SelectFailed, RowFailed)):
        # Whatever is left of these two is the refusal half: the item or row is there and the
        # provider would not act on it.
        return ACTION_REFUSED
    if isinstance(error, (CheckpointError, RowError, RowsUnavailable)):
        # **Not `assertionFailed`.** `CheckpointError` is "the checkpoint itself is wrong,
        # whatever the application is doing" (its own docstring), `RowError` is "the step says
        # something impossible", and `RowsUnavailable` is "the target is not something whose
        # rows playback can address". All three are the agent refusing a step, and calling any
        # of them an assertion failure would put a broken test in the application's column —
        # the exact mix this module exists to prevent.
        return REFUSED_STEP
    return REFUSED_STEP
