"""Checking one property of one element: the `Verify` keyword (#40).

A checkpoint is `{property, operator, expected}` and it answers one question — does this hold
right now? The runner re-reads the window until it does or the step's time runs out, so a
property that is *about* to change is not a race; nothing here sleeps or reads twice.

**Where each property comes from.** Three are already in the descriptor the walk derived, so
checking them costs nothing beyond the read the runner already did:

* ``name`` — UI Automation Name, through :func:`ayna_agent.model.text_value` so it is compared
  in the form a descriptor stores it in (stripped, blank is nothing);
* ``enabled`` — ``IsEnabled``;
* ``visible`` — ``not IsOffscreen``, which is the step schema's own definition.

The other three are **not** in a descriptor and are read live through patterns, because they
are state rather than identity and the walk deliberately does not carry them:

* ``value`` — ``ValuePattern``, then ``LegacyIAccessible``, the same ladder ``Type`` goes down;
* ``checked`` — ``TogglePattern`` state is **On**, so an indeterminate check box is *not*
  checked (the schema says "TogglePattern state is On" and means it);
* ``selected`` — ``SelectionItemPattern.IsSelected``.

**A property that cannot be read is not a failed check.** `IsEnabled` absent, no
``TogglePattern`` on the target: there is no answer, so :class:`Unreadable` says which property
and why, and the step fails with that rather than with "expected true, got false" — which would
tell a tester their application is wrong when it is the check that does not apply.

**Operators follow the schema, not taste.** `name`, `value` and `cell` take all three; the
boolean properties and `rowCount` take `equals` only, and the schema enforces it with an
`if`/`then`. Playback enforces it too: a `contains` on a boolean is a client bug and reading it
as `equals` would quietly answer a different question.

The message wording is fixed and comes from the PR #231 review, because omer's run report and
its tests are written against it: lower case, the logical name first, no "Step failed:" prefix.

    login.message: name should contain "Invalid", it is "Welcome, admin!"
    login.okButton: enabled should be true, it is false

Everything here is pure: patterns arrive injected, so every rule is tested with fakes off
Windows (`agent/AGENTS.md`).
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from ayna_agent.model import Element, text_value
from ayna_agent.playback.actions import Patterns, uia_patterns

#: Properties of a single element. The grid ones (`cell`, `rowExists`, `rowCount`) are checked
#: against the target's rows instead and live in `playback.rows`.
ELEMENT_PROPERTIES: frozenset[str] = frozenset(
    {"name", "value", "enabled", "visible", "checked", "selected"}
)

#: Which checkpoint property takes `row` and which takes `column`, from the schema's own
#: `if`/`then` rules: `cell` needs both, `rowExists` needs the row and refuses the column
#: (a list has no columns), and every other property refuses both. A field on a property that
#: forbids it is refused rather than ignored, for the same reason the runner refuses one on a
#: keyword: a check that quietly read a different row would report `passed`.
NEEDS_ROW: frozenset[str] = frozenset({"cell", "rowExists"})
NEEDS_COLUMN: frozenset[str] = frozenset({"cell"})

#: Properties whose `expected` is text, and the only ones an operator other than `equals`
#: means anything for (step schema: `name`, `value` and `cell` take a string).
TEXT_PROPERTIES: frozenset[str] = frozenset({"name", "value", "cell"})

OPERATORS: frozenset[str] = frozenset({"equals", "notEquals", "contains"})

#: How each operator reads in a message.
_SAYS: dict[str, str] = {
    "equals": "should be",
    "notEquals": "should not be",
    "contains": "should contain",
}

#: `TogglePattern` states. 2 is indeterminate, which is not On and so not `checked`.
_TOGGLE_ON = 1


class CheckpointError(Exception):
    """The checkpoint itself is wrong, whatever the application is doing."""


class Unreadable(Exception):
    """The property cannot be read from this element, so the check has no answer."""

    def __init__(self, name: str, reason: str) -> None:
        self.reason = reason
        super().__init__(f"{name}: {reason}")


def says(operator: str) -> str:
    """How `operator` reads in a message. Public because the row checks word their own.

    One table, so `name should contain "Invalid"` and `the "Soyad" cell of row 2 should be
    "Yılmaz"` cannot drift apart -- the run report (#59) is written against both.
    """
    return _SAYS[operator]


def validate(checkpoint: Mapping[str, Any]) -> tuple[str, str, Any]:
    """`(property, operator, expected)`, or raise :class:`CheckpointError`.

    The schema already refuses all of this; a request that gets here carrying it is a client
    bug, and refusing beats guessing — reading a `contains` on a boolean as `equals` would
    answer a question nobody asked and report `passed`.
    """
    if not isinstance(checkpoint, Mapping):
        raise CheckpointError("a Verify step needs a checkpoint object")
    prop = checkpoint.get("property")
    operator = checkpoint.get("operator")
    if "expected" not in checkpoint:
        raise CheckpointError("the checkpoint says no expected value")
    expected = checkpoint["expected"]
    if not isinstance(prop, str) or not prop:
        raise CheckpointError("the checkpoint names no property")
    if operator not in OPERATORS:
        allowed = ", ".join(sorted(OPERATORS))
        raise CheckpointError(f"operator {operator!r} is not one of {allowed}")
    if prop not in TEXT_PROPERTIES and operator != "equals":
        raise CheckpointError(f"{prop} can only be checked with equals, not {operator}")
    if prop in TEXT_PROPERTIES and not isinstance(expected, str):
        raise CheckpointError(f"{prop} is checked against text, not {expected!r}")
    if prop == "rowCount":
        if not isinstance(expected, int) or isinstance(expected, bool) or expected < 0:
            raise CheckpointError(
                f"rowCount is checked against a whole number of rows, not {expected!r}"
            )
    elif prop not in TEXT_PROPERTIES and not isinstance(expected, bool):
        raise CheckpointError(f"{prop} is checked against true or false")
    for field, needed in (("row", NEEDS_ROW), ("column", NEEDS_COLUMN)):
        if field in checkpoint and prop not in needed:
            allowed = " and ".join(sorted(needed))
            raise CheckpointError(
                f"a {prop} check carries {field!r}, which only {allowed} takes"
            )
        if field not in checkpoint and prop in needed:
            raise CheckpointError(f"a {prop} check says no {field}")
    return prop, operator, expected


def read(
    prop: str,
    descriptor: Element,
    element: Any,
    patterns: Patterns = uia_patterns,
) -> Any:
    """The element's current `prop`. Raises :class:`Unreadable` when there is no answer."""
    if prop == "name":
        return text_value(descriptor.name)
    if prop == "enabled":
        if descriptor.enabled is None:
            raise Unreadable(prop, "the provider does not report whether it is enabled")
        return descriptor.enabled
    if prop == "visible":
        if descriptor.offscreen is None:
            raise Unreadable(
                prop, "the provider does not report whether it is on screen"
            )
        return not descriptor.offscreen
    if prop == "value":
        return _value_of(element, patterns)
    if prop == "checked":
        toggle = patterns(element, "Toggle")
        if toggle is None:
            raise Unreadable(
                prop, "the element has no TogglePattern, so it cannot be checked"
            )
        state = _read(lambda: toggle.CurrentToggleState)
        if state is None:
            raise Unreadable(prop, "the element's TogglePattern did not answer")
        return int(state) == _TOGGLE_ON
    if prop == "selected":
        item = patterns(element, "SelectionItem")
        if item is None:
            raise Unreadable(
                prop,
                "the element has no SelectionItemPattern, so it cannot be selected",
            )
        state = _read(lambda: item.CurrentIsSelected)
        if state is None:
            raise Unreadable(prop, "the element's SelectionItemPattern did not answer")
        return bool(state)
    raise CheckpointError(f"property {prop!r} is not one this agent checks")


def _value_of(element: Any, patterns: Patterns) -> str | None:
    """The target's text, down the same ladder `Type` writes it with."""
    pattern = patterns(element, "Value")
    if pattern is not None:
        text = _read(lambda: pattern.CurrentValue)
        if text is not None:
            return text_value(text)
    legacy = patterns(element, "LegacyIAccessible")
    if legacy is not None:
        text = _read(lambda: legacy.CurrentValue)
        if text is not None:
            return text_value(text)
    raise Unreadable(
        "value", "the element has neither a ValuePattern nor a LegacyIAccessible value"
    )


def _read(call: Any) -> Any:
    try:
        return call()
    except Exception:  # noqa: BLE001 - a provider that does not answer means "no value"
        return None


def holds(operator: str, actual: Any, expected: Any) -> bool:
    """Whether `actual` satisfies `expected` under `operator`."""
    if operator == "contains":
        return expected in (actual or "")
    if operator == "notEquals":
        return not _same(actual, expected)
    return _same(actual, expected)


def _same(actual: Any, expected: Any) -> bool:
    """Equality for a checkpoint: text compares as text, and nothing equals "".

    A target with no name reads as `None`, and `expected: ""` is a real check a tester writes
    ("the error label is empty"), so the two have to compare equal — otherwise an empty label
    could never be verified.
    """
    if isinstance(expected, str):
        return (actual or "") == expected
    return actual == expected


def describe(name: str, prop: str, operator: str, expected: Any, actual: Any) -> str:
    """The failure message, in the wording promised in the PR #231 review."""
    return f"{name}: {prop} {_SAYS[operator]} {show(expected)}, it is {show(actual)}"


def show(value: Any) -> str:
    """A value as a message writes it: text quoted, booleans lower case, numbers bare."""
    if value is None:
        return "not set"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    return str(value)
