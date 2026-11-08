"""Tests for resolving a repository object to one element (#26).

Everything runs against the **real** trial-app tree captured on Windows for #11
(`tests/data/trial-app-tree.json`), the same fixture the descriptor and snapshot tests use, so
the cases are the application's own shapes rather than invented ones. Two of them matter:

- `usernameLabel` (Text) and `usernameInput` (Edit) both have the UIA Name `"Username"`, so
  `{name: "Username"}` is genuinely ambiguous in this window;
- the Edit elements get `nearestLabel` from the geometric rule, so matching on a computed
  property is exercised against a value the derivation produced, not one a test made up.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ayna_agent.model import describe_tree
from ayna_agent.playback.resolve import (
    MATCHABLE,
    Ambiguous,
    NotFound,
    Unsupported,
    check_properties,
    find_matches,
    matches,
    resolve,
)

TRIAL_TREE = Path(__file__).resolve().parent / "data" / "trial-app-tree.json"

LOGIN_BUTTON = "QApplication.loginWindow.loginButton"
USERNAME_INPUT = "QApplication.loginWindow.usernameInput"


@pytest.fixture
def tree() -> tuple[list, list[str]]:
    """Descriptors for the trial app's login window, and a stand-in per live element.

    The "live element" is just its automation id here: resolution never touches it, which is
    the property that lets these tests run anywhere.
    """
    nodes = json.loads(TRIAL_TREE.read_text(encoding="utf-8"))
    descriptors = describe_tree(nodes)
    infos = [f"element-{index}" for index in range(len(descriptors))]
    return descriptors, infos


# --- what may be matched on ----------------------------------------------------------------


def test_matchable_is_the_descriptor_minus_never_match():
    assert "automationId" in MATCHABLE
    assert "name" in MATCHABLE
    assert "nearestLabel" in MATCHABLE
    assert "parentPath" in MATCHABLE
    # model.NEVER_MATCH, which the server refuses in a property set too.
    for never in (
        "bounds",
        "dpi",
        "nativeWindowHandle",
        "frameworkId",
        "enabled",
        "offscreen",
        "nearestLabelSource",
    ):
        assert never not in MATCHABLE


@pytest.mark.parametrize(
    "properties",
    [
        {"bounds": [1, 2, 3, 4]},
        {"dpi": 120},
        {"enabled": True},
        {"nearestLabelSource": "geometric"},
        {"automationId": "x", "offscreen": False},
        {"somethingElse": 1},
    ],
)
def test_a_property_that_cannot_identify_an_element_is_refused(properties):
    """Never silently ignored: dropping a key *widens* the match, which can act elsewhere."""
    with pytest.raises(Unsupported):
        check_properties(properties)


def test_an_empty_property_set_is_refused():
    """It matches every element, which would be reported as ambiguity rather than as a bug."""
    with pytest.raises(Unsupported) as caught:
        check_properties({})
    assert "empty property set" in str(caught.value)


def test_the_unsupported_message_lists_what_is_allowed():
    with pytest.raises(Unsupported) as caught:
        check_properties({"bounds": None})
    assert "automationId" in str(caught.value)


# --- matching one descriptor ---------------------------------------------------------------


def test_every_property_must_match(tree):
    descriptors, _ = tree
    button = descriptors[12]
    assert matches(button, {"automationId": LOGIN_BUTTON})
    assert matches(button, {"automationId": LOGIN_BUTTON, "controlType": "Button"})
    assert not matches(button, {"automationId": LOGIN_BUTTON, "controlType": "Edit"})


def test_text_is_compared_case_sensitively(tree):
    descriptors, _ = tree
    button = descriptors[12]
    assert matches(button, {"name": "Login"})
    assert not matches(button, {"name": "login"})
    assert not matches(button, {"name": "Login "})


def test_a_property_the_element_does_not_have_never_matches(tree):
    """`statusLabel` has no Name at all, so no expected Name can match it."""
    descriptors, _ = tree
    status = descriptors[13]
    assert status.name is None
    assert not matches(status, {"name": ""})
    assert not matches(status, {"name": "anything"})


def test_a_computed_property_matches_the_derived_value(tree):
    """`nearestLabel` comes from the same derivation a snapshot stored, so it lines up."""
    descriptors, _ = tree
    username = descriptors[8]
    assert matches(username, {"nearestLabel": "Username", "controlType": "Edit"})
    assert matches(username, {"parentPath": "Window", "siblingIndex": 2})


# --- finding every match -------------------------------------------------------------------


def test_find_matches_returns_all_of_them_in_tree_order(tree):
    descriptors, infos = tree
    found = find_matches(descriptors, infos, {"name": "Username"})
    assert [one.index for one in found] == [7, 8]
    assert [one.element for one in found] == ["element-7", "element-8"]


def test_find_matches_is_empty_when_nothing_matches(tree):
    descriptors, infos = tree
    assert find_matches(descriptors, infos, {"automationId": "gone"}) == []


# --- resolving a target --------------------------------------------------------------------


def test_a_unique_primary_match_resolves(tree):
    descriptors, infos = tree
    found = resolve(
        descriptors, infos, "login.loginButton", {"automationId": LOGIN_BUTTON}
    )
    assert found.index == 12
    assert found.element == "element-12"
    assert found.which == "primary"
    assert found.descriptor.name == "Login"


def test_two_matching_elements_are_ambiguous_and_nothing_is_picked(tree):
    """The real case: the username label and the username box share the Name "Username"."""
    descriptors, infos = tree
    with pytest.raises(Ambiguous) as caught:
        resolve(descriptors, infos, "login.userNameInput", {"name": "Username"})
    assert caught.value.count == 2
    assert caught.value.which == "primary"
    assert "2 elements match" in str(caught.value)
    # The message says what to do, in the words the Spy uses for a primary set.
    assert "Find by" in str(caught.value)


def test_the_ambiguity_message_names_the_backup_set_when_the_fallback_is_ambiguous(
    tree,
):
    descriptors, infos = tree
    with pytest.raises(Ambiguous) as caught:
        resolve(
            descriptors,
            infos,
            "login.userNameInput",
            {"automationId": "gone"},
            {"name": "Username"},
        )
    assert caught.value.which == "fallback"
    assert "Backup" in str(caught.value)


def test_no_match_at_all_reports_both_sets_that_were_tried(tree):
    descriptors, infos = tree
    with pytest.raises(NotFound) as caught:
        resolve(
            descriptors,
            infos,
            "login.loginButton",
            {"automationId": "renamed"},
            {"name": "Oturum Aç"},
        )
    assert caught.value.name == "login.loginButton"
    assert caught.value.tried == [{"automationId": "renamed"}, {"name": "Oturum Aç"}]
    assert "renamed" in str(caught.value)
    assert "Oturum Aç" in str(caught.value)


def test_the_fallback_is_used_when_the_primary_set_matches_nothing(tree):
    """What FR-29 and #73 are about: the Find-by properties have stopped matching."""
    descriptors, infos = tree
    found = resolve(
        descriptors,
        infos,
        "login.loginButton",
        {"automationId": "QApplication.loginWindow.signInButton"},
        {"name": "Login", "controlType": "Button"},
    )
    assert found.index == 12
    assert found.which == "fallback"


def test_the_fallback_is_not_tried_when_the_primary_set_is_ambiguous(tree):
    """A fallback replaces a primary set; it cannot narrow one, so it has nothing to add."""
    descriptors, infos = tree
    with pytest.raises(Ambiguous) as caught:
        resolve(
            descriptors,
            infos,
            "login.userNameInput",
            {"name": "Username"},
            {"automationId": USERNAME_INPUT},
        )
    assert caught.value.which == "primary"


def test_a_target_with_no_fallback_resolves_or_raises_not_found(tree):
    descriptors, infos = tree
    with pytest.raises(NotFound) as caught:
        resolve(descriptors, infos, "login.loginButton", {"automationId": "renamed"})
    assert len(caught.value.tried) == 1


def test_an_unsupported_primary_set_is_refused_before_anything_is_searched(tree):
    descriptors, infos = tree
    with pytest.raises(Unsupported):
        resolve(descriptors, infos, "login.loginButton", {"bounds": [0, 0, 1, 1]})


def test_an_empty_window_finds_nothing_rather_than_failing(tree):
    _descriptors, _infos = tree
    with pytest.raises(NotFound):
        resolve([], [], "login.loginButton", {"automationId": LOGIN_BUTTON})
