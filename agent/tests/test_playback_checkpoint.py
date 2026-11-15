"""Tests for the Verify checkpoint (#40).

All of it runs off Windows: the patterns are injected, so what is tested here is where each
property comes from, what "cannot be read" means, and the message wording -- which is fixed by
the PR #231 review because the run report (#59) is written against it.
"""

from __future__ import annotations

import pytest

from ayna_agent.model import Element
from ayna_agent.playback import checkpoint as cp


class Fake:
    """An element whose patterns and their values are stated per test."""

    def __init__(self, **patterns: object) -> None:
        self.patterns = patterns

    def __call__(self, element: object, name: str) -> object | None:
        return self.patterns.get(name)


class Value:
    def __init__(self, text: object) -> None:
        self.CurrentValue = text


class Toggle:
    def __init__(self, state: object) -> None:
        self.CurrentToggleState = state


class Selected:
    def __init__(self, state: object) -> None:
        self.CurrentIsSelected = state


class Dead:
    """A provider that raises on every read, as one that died mid-step does."""

    @property
    def CurrentValue(self) -> str:
        raise OSError("the provider is gone")

    @property
    def CurrentToggleState(self) -> int:
        raise OSError("the provider is gone")

    @property
    def CurrentIsSelected(self) -> bool:
        raise OSError("the provider is gone")


def element(**fields: object) -> Element:
    return Element(**fields)  # type: ignore[arg-type]


# --- where each property comes from --------------------------------------------------------


def test_name_comes_from_the_descriptor_in_the_form_it_is_stored_in():
    """`text_value`'s rule: stripped, and blank is nothing. A property read after a capture
    has to pass the same rule as the stored one or the two can never compare."""
    assert cp.read("name", element(name="  Login  "), None, Fake()) == "Login"
    assert cp.read("name", element(name="   "), None, Fake()) is None


@pytest.mark.parametrize(
    ("prop", "fields", "expected"),
    [
        ("enabled", {"enabled": True}, True),
        ("enabled", {"enabled": False}, False),
        ("visible", {"offscreen": False}, True),
        ("visible", {"offscreen": True}, False),
    ],
)
def test_enabled_and_visible_come_from_the_descriptor(prop, fields, expected):
    """`visible` is `not IsOffscreen`, which is the step schema's own definition."""
    assert cp.read(prop, element(**fields), None, Fake()) is expected


def test_value_comes_from_the_value_pattern():
    patterns = Fake(Value=Value("admin"))
    assert cp.read("value", element(), object(), patterns) == "admin"


def test_value_falls_back_to_legacy_the_way_type_does():
    patterns = Fake(LegacyIAccessible=Value("admin"))
    assert cp.read("value", element(), object(), patterns) == "admin"


@pytest.mark.parametrize(("state", "expected"), [(1, True), (0, False), (2, False)])
def test_checked_is_toggle_state_on_and_indeterminate_is_not_checked(state, expected):
    """The schema says "TogglePattern state is On" and means it: an indeterminate box is not
    checked, which is a different answer from "the check does not apply"."""
    patterns = Fake(Toggle=Toggle(state))
    assert cp.read("checked", element(), object(), patterns) is expected


@pytest.mark.parametrize("state", [True, False])
def test_selected_is_the_selection_item_pattern(state):
    patterns = Fake(SelectionItem=Selected(state))
    assert cp.read("selected", element(), object(), patterns) is state


# --- a property that cannot be read is not a failed check ----------------------------------


def test_a_state_the_provider_does_not_report_is_unreadable_not_false():
    """Otherwise the step would tell a tester their application is wrong when it is the check
    that does not apply."""
    with pytest.raises(cp.Unreadable, match="whether it is enabled"):
        cp.read("enabled", element(enabled=None), None, Fake())
    with pytest.raises(cp.Unreadable, match="whether it is on screen"):
        cp.read("visible", element(offscreen=None), None, Fake())


def test_checked_on_an_element_with_no_toggle_pattern_is_unreadable():
    with pytest.raises(cp.Unreadable, match="no TogglePattern"):
        cp.read("checked", element(), object(), Fake())


def test_selected_on_an_element_with_no_selection_pattern_is_unreadable():
    with pytest.raises(cp.Unreadable, match="no SelectionItemPattern"):
        cp.read("selected", element(), object(), Fake())


def test_value_with_neither_pattern_is_unreadable():
    with pytest.raises(cp.Unreadable, match="neither a ValuePattern"):
        cp.read("value", element(), object(), Fake())


@pytest.mark.parametrize("prop", ["value", "checked", "selected"])
def test_a_provider_that_died_mid_step_is_unreadable_rather_than_a_crash(prop):
    patterns = Fake(Value=Dead(), Toggle=Dead(), SelectionItem=Dead())
    with pytest.raises(cp.Unreadable):
        cp.read(prop, element(), object(), patterns)


def test_a_property_this_agent_does_not_check_says_so():
    with pytest.raises(cp.CheckpointError, match="rowCount"):
        cp.read("rowCount", element(), object(), Fake())


# --- the operators -------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("operator", "actual", "expected", "holds"),
    [
        ("equals", "Welcome", "Welcome", True),
        ("equals", "Welcome", "welcome", False),
        ("notEquals", "Welcome", "Hata", True),
        ("notEquals", "Welcome", "Welcome", False),
        ("contains", "Welcome, admin!", "admin", True),
        ("contains", "Welcome, admin!", "Invalid", False),
        ("equals", True, True, True),
        ("equals", False, True, False),
        ("notEquals", False, True, True),
        ("equals", 3, 3, True),
        ("equals", 5, 3, False),
    ],
)
def test_the_operators(operator, actual, expected, holds):
    assert cp.holds(operator, actual, expected) is holds


def test_an_empty_expectation_matches_an_element_with_no_text():
    """ "The error label is empty" is a real check a tester writes, and a target with no name
    reads as None, so the two have to compare equal or it could never be verified."""
    assert cp.holds("equals", None, "")
    assert not cp.holds("notEquals", None, "")


def test_contains_on_an_element_with_no_text_does_not_crash():
    assert not cp.holds("contains", None, "Invalid")


# --- what the checkpoint itself may say ----------------------------------------------------


def test_a_well_formed_checkpoint_is_accepted():
    assert cp.validate(
        {"property": "name", "operator": "contains", "expected": "Invalid"}
    ) == ("name", "contains", "Invalid")


@pytest.mark.parametrize(
    ("checkpoint", "message"),
    [
        ({"operator": "equals", "expected": True}, "names no property"),
        ({"property": "enabled", "operator": "equals"}, "no expected value"),
        (
            {"property": "name", "operator": "sounds-like", "expected": "x"},
            "is not one of",
        ),
        (
            {"property": "enabled", "operator": "contains", "expected": True},
            "only be checked with equals",
        ),
        ({"property": "name", "operator": "equals", "expected": 3}, "against text"),
        (
            {"property": "enabled", "operator": "equals", "expected": "true"},
            "true or false",
        ),
    ],
)
def test_a_checkpoint_the_schema_forbids_is_refused_rather_than_guessed(
    checkpoint, message
):
    """Reading a `contains` on a boolean as `equals` would answer a question nobody asked and
    report `passed`."""
    with pytest.raises(cp.CheckpointError, match=message):
        cp.validate(checkpoint)


def test_a_checkpoint_that_is_not_an_object_is_refused():
    with pytest.raises(cp.CheckpointError, match="needs a checkpoint object"):
        cp.validate(None)  # type: ignore[arg-type]


# --- the message ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("prop", "operator", "expected", "actual", "message"),
    [
        (
            "name",
            "contains",
            "Invalid",
            "Welcome, admin!",
            'login.message: name should contain "Invalid", it is "Welcome, admin!"',
        ),
        (
            "enabled",
            "equals",
            True,
            False,
            "login.message: enabled should be true, it is false",
        ),
        (
            "value",
            "notEquals",
            "admin",
            "admin",
            'login.message: value should not be "admin", it is "admin"',
        ),
        (
            "name",
            "equals",
            "Hata",
            None,
            'login.message: name should be "Hata", it is not set',
        ),
    ],
)
def test_the_message_is_the_wording_promised_in_the_231_review(
    prop, operator, expected, actual, message
):
    """The run report (#59) and its tests are written against these exact strings."""
    assert cp.describe("login.message", prop, operator, expected, actual) == message


def test_turkish_text_is_not_escaped_in_a_message():
    assert cp.show("Kayıt başarılı") == '"Kayıt başarılı"'
