"""Tests for Click and Type through UI Automation patterns (#26).

The pattern lookup is injected, so what is tested here is the part that matters and the part
that is easy to get wrong: **which pattern is tried, in which order, and what happens when one
is present but refuses**. A pattern that exists and raises is not the same as a missing one --
a disabled button has `Invoke` and will not run it -- and both have to fall through.

No pywinauto, no Windows. The real lookup (`uia_patterns`) is one `get_elem_interface` call and
is covered by the `@pytest.mark.windows` run on the trial app.
"""

from __future__ import annotations

import pytest

from ayna_agent.playback.actions import ActionFailed, click, type_text


class Recorder:
    """A fake element: the patterns it supports, and what was called on it."""

    def __init__(self, supported: dict[str, object] | None = None) -> None:
        self.supported = supported or {}
        self.calls: list[str] = []
        self.focused = False

    def patterns(self, element: object, name: str) -> object | None:
        assert element is self, (
            "the action must look patterns up on the element it was given"
        )
        return self.supported.get(name)

    def SetFocus(self) -> None:
        self.focused = True
        self.calls.append("SetFocus")


class Pattern:
    """One pattern. `fails` makes the call raise, as a provider that refuses does."""

    def __init__(self, owner: Recorder, name: str, *, fails: bool = False) -> None:
        self._owner = owner
        self._name = name
        self._fails = fails
        self.value: str | None = None
        self.CurrentIsReadOnly = False

    def _do(self, what: str) -> None:
        self._owner.calls.append(f"{self._name}.{what}")
        if self._fails:
            raise RuntimeError(f"{self._name} refused")

    def Invoke(self) -> None:
        self._do("Invoke")

    def Toggle(self) -> None:
        self._do("Toggle")

    def Select(self) -> None:
        self._do("Select")

    def DoDefaultAction(self) -> None:
        self._do("DoDefaultAction")

    def SetValue(self, value: str) -> None:
        self._do("SetValue")
        self.value = value


def element(*names: str, failing: tuple[str, ...] = ()) -> Recorder:
    recorder = Recorder()
    recorder.supported = {
        name: Pattern(recorder, name, fails=name in failing) for name in names
    }
    return recorder


# --- Click ---------------------------------------------------------------------------------


def test_click_prefers_invoke():
    button = element("Invoke", "Toggle", "SelectionItem", "LegacyIAccessible")
    assert click(button, button.patterns) == "Invoke"
    assert button.calls == ["Invoke.Invoke"]


def test_click_toggles_a_check_box_that_has_no_invoke():
    box = element("Toggle", "SelectionItem")
    assert click(box, box.patterns) == "Toggle"
    assert box.calls == ["Toggle.Toggle"]


def test_click_selects_a_list_item():
    item = element("SelectionItem")
    assert click(item, item.patterns) == "SelectionItem"


def test_click_falls_back_to_the_msaa_bridge_last():
    legacy = element("LegacyIAccessible")
    assert click(legacy, legacy.patterns) == "LegacyIAccessible"
    assert legacy.calls == ["LegacyIAccessible.DoDefaultAction"]


def test_a_pattern_that_is_present_but_refuses_falls_through():
    """A disabled button has `Invoke` and will not run it; the next pattern gets a turn."""
    button = element("Invoke", "LegacyIAccessible", failing=("Invoke",))
    assert click(button, button.patterns) == "LegacyIAccessible"
    assert button.calls == ["Invoke.Invoke", "LegacyIAccessible.DoDefaultAction"]


def test_click_tries_every_pattern_in_order_before_giving_up():
    nothing = element(
        "Invoke",
        "Toggle",
        "SelectionItem",
        "LegacyIAccessible",
        failing=("Invoke", "Toggle", "SelectionItem", "LegacyIAccessible"),
    )
    with pytest.raises(ActionFailed) as caught:
        click(nothing, nothing.patterns)
    assert nothing.calls == [
        "Invoke.Invoke",
        "Toggle.Toggle",
        "SelectionItem.Select",
        "LegacyIAccessible.DoDefaultAction",
    ]
    assert caught.value.keyword == "Click"
    assert "without coordinates" in str(caught.value)


def test_click_on_an_element_with_no_usable_pattern_says_so():
    bare = element()
    with pytest.raises(ActionFailed) as caught:
        click(bare, bare.patterns)
    assert bare.calls == []
    assert "Invoke" in str(caught.value)


def test_the_element_behind_a_pywinauto_info_is_used():
    """`recognition/uia.py` walks `UIAElementInfo`; the action needs its `.element`."""
    inner = element("Invoke")

    class Info:
        element = inner

    assert click(Info(), inner.patterns) == "Invoke"
    assert inner.calls == ["Invoke.Invoke"]


# --- Type ----------------------------------------------------------------------------------


def test_type_replaces_the_text_through_set_value():
    box = element("Value")
    assert type_text(box, "admin", box.patterns) == "SetValue"
    assert box.supported["Value"].value == "admin"


def test_type_with_an_empty_value_clears_the_field():
    """Step schema v0: Type replaces the text and an empty value clears it."""
    box = element("Value")
    assert type_text(box, "", box.patterns) == "SetValue"
    assert box.supported["Value"].value == ""


def test_a_read_only_value_is_reported_rather_than_worked_around():
    box = element("Value")
    box.supported["Value"].CurrentIsReadOnly = True
    with pytest.raises(ActionFailed) as caught:
        type_text(box, "admin", box.patterns)
    assert "read-only" in str(caught.value)
    assert box.calls == [], "nothing should be typed into a read-only field"


def test_type_falls_back_to_the_keyboard_when_there_is_no_value_pattern(monkeypatch):
    typed: list[str] = []
    monkeypatch.setattr(
        "ayna_agent.playback.actions._send_keys", lambda value: typed.append(value)
    )
    box = element()
    assert type_text(box, "admin", box.patterns) == "keys"
    assert box.focused
    assert typed == ["admin"]


def test_type_falls_back_to_the_keyboard_when_set_value_refuses(monkeypatch):
    typed: list[str] = []
    monkeypatch.setattr(
        "ayna_agent.playback.actions._send_keys", lambda value: typed.append(value)
    )
    box = element("Value", failing=("Value",))
    assert type_text(box, "admin", box.patterns) == "keys"
    assert box.calls == ["Value.SetValue", "SetFocus"]
    assert typed == ["admin"]


def test_type_fails_when_the_element_will_not_take_focus():
    class Stubborn(Recorder):
        def SetFocus(self) -> None:
            raise RuntimeError("no focus here")

    box = Stubborn()
    with pytest.raises(ActionFailed) as caught:
        type_text(box, "admin", box.patterns)
    assert "keyboard focus" in str(caught.value)


def test_a_provider_that_does_not_answer_is_read_only_is_treated_as_writable():
    """A missing `CurrentIsReadOnly` must not stop a field that would accept the text."""

    class Odd:
        """A ValuePattern whose `CurrentIsReadOnly` raises, as a thin provider's does."""

        def __init__(self) -> None:
            self.value: str | None = None

        @property
        def CurrentIsReadOnly(self) -> bool:
            raise RuntimeError("not implemented by this provider")

        def SetValue(self, value: str) -> None:
            self.value = value

    pattern = Odd()
    box = Recorder({"Value": pattern})
    assert type_text(box, "admin", box.patterns) == "SetValue"
    assert pattern.value == "admin"
