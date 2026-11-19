"""Performing Click and Type on an element, through UI Automation patterns only (#26).

The two keywords that act on *one* element and nothing around it. Select needs the target's
items (`playback.items`) and SelectRow its rows (`playback.rows`), so those live apart; what
they share with this module is :data:`Patterns` and the rule that a pattern which refuses falls
through to the next one.

**Never coordinates** (`agent/AGENTS.md`). A click at a remembered point breaks when the window
moves, when the display scaling changes, or when a list scrolls -- which is most of what makes
recorded tests brittle, and the thing AYNA exists to avoid. So an action asks the provider to
do it: `Invoke` a button, `Toggle` a check box, `Select` a list item, `SetValue` an edit box.

Which pattern to try, and in which order, is the whole content of this module, because no
framework supports them all:

- **Click** -- `Invoke`, then `Toggle`, then `SelectionItem.Select`, then
  `LegacyIAccessible.DoDefaultAction`. `Invoke` first because it is what a button means by
  "clicked". `Toggle` before `Select` because a check box has `Toggle` and a radio button has
  `SelectionItem`, and a control with both (some WinForms check boxes) should toggle rather
  than merely become selected. `DoDefaultAction` last: it is the MSAA bridge and does
  *something* on almost anything, which makes it a good floor and a bad first choice.
- **Type** -- `Value.SetValue`, then focus and send the keys. The step schema says Type
  *replaces* the text and an empty value clears it, which is `SetValue`'s own semantics.

The pattern lookup is injected, so the order and the fallbacks above are tested with fakes on
any OS and only :func:`uia_patterns` needs Windows (`agent/AGENTS.md`).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

#: `(element, pattern name) -> the pattern interface, or None when unsupported.`
Patterns = Callable[[Any, str], Any]


class ActionFailed(Exception):
    """The element is there, but the action could not be performed on it."""

    def __init__(self, keyword: str, reason: str) -> None:
        self.keyword = keyword
        self.reason = reason
        super().__init__(f"{keyword} failed: {reason}")


#: The least time between two `Invoke`s on the same target (#264). Qt performs UIA `Invoke` on a
#: button through `QAbstractButton::animateClick()`: the button is pressed at once and released
#: 100 ms later, and a second call before the release only restarts that timer. The second
#: click is lost, and `Invoke` still returns without error, so the step would report `passed`
#: and the run would fail one step later on the wrong control. Measured on the sample app's
#: wizard Next button (2026-11-19): two `Invoke`s 0, 50 and 90 ms apart turned one page, 120
#: and 200 ms apart turned two. 200 ms leaves room for a busy event loop.
INVOKE_GAP_S = 0.2


class InvokeSpacing:
    """When each target was last clicked through `Invoke`, so the next one waits out the gap.

    Only a second `Invoke` on the **same** target within :data:`INVOKE_GAP_S` waits, and only
    for what is left of it: a Qt button keeps its own release timer, so two different buttons
    never collide, and a fixed sleep after every step would cost every run to fix two clicks.
    Keyed by logical name, which within one run names one element. Kept between runs on
    purpose: the client sends each step as its own one-step run (#44), and the two clicks
    #264 found were 77 ms apart across exactly such a boundary.
    """

    def __init__(self) -> None:
        self._last: dict[str, float] = {}

    def wait(
        self, name: str, now: Callable[[], float], sleep: Callable[[float], None]
    ) -> float:
        """Sleep out the rest of the gap if `name` was invoked too recently; return the wait."""
        last = self._last.get(name)
        if last is None:
            return 0.0
        remaining = INVOKE_GAP_S - (now() - last)
        # A negative elapsed time means another clock wrote the mark (tests inject one per
        # run); never wait longer than the gap itself because of it.
        if 0 < remaining <= INVOKE_GAP_S:
            sleep(remaining)
            return remaining
        return 0.0

    def invoked(self, name: str, at: float) -> None:
        self._last[name] = at

    def clear(self) -> None:
        self._last.clear()


def uia_patterns(element: Any, name: str) -> Any:
    """The real pattern lookup. Windows only; imported lazily so this module loads anywhere.

    The unwrapping is **here** rather than at the call sites: `get_elem_interface` needs the
    raw `IUIAutomationElement`, while the walk hands every caller a `UIAElementInfo`, and a
    lookup given the wrapper raises `AttributeError` -- which this function turns into `None`,
    so every pattern silently reads as unsupported. Measured on the sample app's Qt combo box
    (#40 Windows check): it offers `ExpandCollapse`, `Invoke` and `Value`, and `Select` still
    reported "this element shows no items". Doing it once at the seam is what keeps the next
    module from having to remember.
    """
    from pywinauto.uia_defines import get_elem_interface

    try:
        return get_elem_interface(_element_of(element), name)
    except Exception:  # noqa: BLE001 - see below; both failures mean the same to the caller
        # pywinauto raises NoPatternInterfaceError for "not supported"; a provider that died
        # mid-call raises a COMError. Both mean "not available through this pattern", and the
        # caller's next fallback is the useful response to either.
        return None


def _element_of(target: Any) -> Any:
    """The IUIAutomation element behind a pywinauto `UIAElementInfo`, or the object itself.

    `recognition/uia.py` walks `UIAElementInfo` objects and reads `info.element`; a fake in the
    tests is the element already. Accepting both keeps the runner free of that detail.
    """
    return getattr(target, "element", target)


def click(target: Any, patterns: Patterns = uia_patterns) -> str:
    """Click the element. Returns the name of the pattern that did it.

    Raises `ActionFailed` when the element supports none of the four, which means the provider
    offers no way to activate it without coordinates -- worth reporting as such rather than
    silently falling back to a mouse event at its centre.
    """
    element = _element_of(target)

    invoke = patterns(element, "Invoke")
    if invoke is not None and _try(lambda: invoke.Invoke(), "Click", "Invoke"):
        return "Invoke"

    toggle = patterns(element, "Toggle")
    if toggle is not None and _try(lambda: toggle.Toggle(), "Click", "Toggle"):
        return "Toggle"

    item = patterns(element, "SelectionItem")
    if item is not None and _try(lambda: item.Select(), "Click", "SelectionItem"):
        return "SelectionItem"

    legacy = patterns(element, "LegacyIAccessible")
    if legacy is not None and _try(
        lambda: legacy.DoDefaultAction(), "Click", "LegacyIAccessible"
    ):
        return "LegacyIAccessible"

    raise ActionFailed(
        "Click",
        "the element supports none of Invoke, Toggle, SelectionItem or "
        "LegacyIAccessible, so there is no way to click it without coordinates",
    )


def type_text(target: Any, value: str, patterns: Patterns = uia_patterns) -> str:
    """Replace the element's text with `value`; an empty value clears it (step schema v0).

    Returns `"SetValue"` or `"keys"`, whichever worked. Raises `ActionFailed` when the element
    has no ValuePattern and cannot take focus, and when a read-only ValuePattern is the only
    way in -- a read-only field is a real finding about the application, not a reason to try
    harder.
    """
    element = _element_of(target)

    pattern = patterns(element, "Value")
    if pattern is not None:
        if _read_only(pattern):
            raise ActionFailed("Type", "the element's value is read-only")
        if _try(lambda: pattern.SetValue(value), "Type", "Value"):
            return "SetValue"

    # No ValuePattern, or SetValue refused it: focus the element and type. Still no
    # coordinates -- focus comes from UI Automation and the keys go to whatever has it.
    if not _try(lambda: element.SetFocus(), "Type", "SetFocus"):
        raise ActionFailed(
            "Type",
            "the element has no usable ValuePattern and would not take keyboard focus",
        )
    _send_keys(value)
    return "keys"


def _read_only(pattern: Any) -> bool:
    try:
        return bool(pattern.CurrentIsReadOnly)
    except Exception:  # noqa: BLE001 - a provider that does not answer is treated as writable
        return False


def _send_keys(value: str) -> None:
    """Select everything in the focused field and type `value` over it.

    `^a` then the text, so Type replaces rather than appends even on a field that already has
    content; an empty value leaves the selection deleted, which is the "clears it" case.
    Imported lazily, like the pattern lookup.
    """
    from pywinauto import keyboard

    keyboard.send_keys("^a{BACKSPACE}")
    if value:
        keyboard.send_keys(value, with_spaces=True, with_tabs=True, with_newlines=True)


def _try(call: Callable[[], Any], keyword: str, what: str) -> bool:
    """`call()`, True when it returned. False when the provider refused it.

    A pattern can be present and still refuse -- a disabled button's `Invoke`, a `SetValue` on
    a field that validates -- so a refusal moves to the next fallback instead of ending the
    step. If every fallback refuses, the caller raises `ActionFailed` with all of them named.
    """
    try:
        call()
    except Exception:  # noqa: BLE001 - COMError and pywinauto both land here; same meaning
        return False
    return True
