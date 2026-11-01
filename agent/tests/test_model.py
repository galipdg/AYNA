"""Tests for the element descriptor (#11).

The computed properties (`parent_path`, `sibling_index`, `nearest_label`) are the ones
healing has to reproduce from a stored snapshot (#43), so each rule is pinned here with
hand-checked values rather than with a round trip.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ayna_agent.model import (
    NEVER_MATCH,
    PRIMARY_PRIORITY,
    VERSION,
    Element,
    describe_tree,
    is_generated_id,
    nearest_label,
    parent_path,
)

SCHEMA = Path(__file__).resolve().parents[2] / "schemas" / "element.schema.json"


def node(**values):
    """A raw node with the fields the rules read; everything else absent."""
    return values


# --- parent_path -------------------------------------------------------------------------


def test_parent_path_is_root_first_and_excludes_the_element():
    assert parent_path(["Window", "Pane", "Group"]) == "Window/Pane/Group"


def test_parent_path_of_a_root_element_is_none():
    assert parent_path([]) is None


def test_an_unreadable_ancestor_keeps_the_depth():
    assert parent_path(["Window", None, "Group"]) == "Window/?/Group"
    assert parent_path(["Window", "  ", "Group"]) == "Window/?/Group"


def test_parent_path_strips_but_does_not_localise():
    assert parent_path([" Window ", "Pane"]) == "Window/Pane"


# --- generated ids -----------------------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    [
        "1001",
        "65535",
        "3f2504e0-4f89-11d3-9a0c-0305e82c3301",
        "QApplication.mainWindow.QPushButton2",
        "QWidget",
    ],
)
def test_generated_ids_are_recognised(value):
    assert is_generated_id(value) is True


@pytest.mark.parametrize(
    "value",
    [
        "m_tbPassword",
        "QApplication.loginWindow.usernameInput",
        "loginButton",
        None,
        "",
        "   ",
    ],
)
def test_developer_chosen_ids_are_not_generated(value):
    assert is_generated_id(value) is False


def test_only_the_leaf_of_a_dotted_id_decides():
    # Qt builds the id from the object chain; an unnamed widget contributes its class name.
    assert is_generated_id("QApplication.form.QLineEdit3") is True
    assert is_generated_id("QApplication.QWidget2.passwordInput") is False


# --- nearest_label -----------------------------------------------------------------------


LABEL_LEFT = node(
    control_type="Text", name="Username", bounds=(0, 10, 90, 30), sibling_index=0
)
LABEL_ABOVE = node(
    control_type="Text", name="Credentials", bounds=(100, 0, 300, 8), sibling_index=1
)
FIELD = node(control_type="Edit", bounds=(100, 10, 300, 30), sibling_index=2)


def test_labeled_by_wins_over_everything():
    element = dict(FIELD, labeled_by="  Kullanıcı adı  ")
    assert nearest_label(element, [LABEL_LEFT, LABEL_ABOVE]) == (
        "Kullanıcı adı",
        "labeledBy",
    )


def test_only_a_label_to_the_left_counts():
    # Measured: every LabeledBy-confirmed pair in the #6 dumps and the trial app is to the
    # left, and accepting one above mislabels check boxes and buttons (see the ADR).
    assert nearest_label(FIELD, [LABEL_LEFT, LABEL_ABOVE]) == ("Username", "geometric")
    assert nearest_label(FIELD, [LABEL_ABOVE]) == (None, None)


def test_the_closer_label_wins():
    far = node(control_type="Text", name="Far", bounds=(0, 10, 20, 30), sibling_index=0)
    near = node(
        control_type="Text", name="Near", bounds=(0, 10, 95, 30), sibling_index=1
    )
    assert nearest_label(FIELD, [far, near]) == ("Near", "geometric")


def test_a_label_further_than_the_ceiling_is_not_a_label():
    # 48 DIP; the nearest wrong pairing measured in five applications is 261 DIP away.
    far = node(
        control_type="Text",
        name="Other column",
        bounds=(0, 10, 40, 30),
        sibling_index=0,
    )
    assert nearest_label(FIELD, [far]) == (None, None)


def test_the_ceiling_is_measured_in_device_independent_pixels():
    # The same layout at 150 % scaling: 60 physical pixels is 40 DIP, still a label.
    field = node(
        control_type="Edit", bounds=(150, 15, 450, 45), dpi=144, sibling_index=1
    )
    label = node(
        control_type="Text", name="Username", bounds=(0, 15, 90, 45), sibling_index=0
    )
    assert nearest_label(field, [label]) == ("Username", "geometric")
    assert nearest_label(dict(field, dpi=96), [label]) == (None, None)


def test_equal_distance_is_broken_by_sibling_index_so_the_result_is_stable():
    first = node(
        control_type="Text", name="First", bounds=(0, 10, 90, 30), sibling_index=3
    )
    second = node(
        control_type="Text", name="Second", bounds=(0, 10, 90, 30), sibling_index=1
    )
    assert nearest_label(FIELD, [first, second]) == ("Second", "geometric")


def test_a_label_without_vertical_overlap_does_not_count_as_left():
    elsewhere = node(
        control_type="Text", name="Other row", bounds=(0, 100, 90, 120), sibling_index=0
    )
    assert nearest_label(FIELD, [elsewhere]) == (None, None)


def test_only_label_like_control_types_count():
    button = node(
        control_type="Button", name="Save", bounds=(0, 10, 90, 30), sibling_index=0
    )
    assert nearest_label(FIELD, [button]) == (None, None)


def test_a_blank_label_is_ignored():
    empty = node(
        control_type="Text", name="   ", bounds=(0, 10, 90, 30), sibling_index=0
    )
    assert nearest_label(FIELD, [empty]) == (None, None)


def test_the_parent_row_is_searched_exactly_one_level_up():
    assert nearest_label(FIELD, [], [LABEL_LEFT]) == ("Username", "parentRow")


def test_the_element_s_own_siblings_win_over_the_parent_row():
    own = node(control_type="Text", name="Own", bounds=(0, 10, 90, 30), sibling_index=0)
    assert nearest_label(FIELD, [own], [LABEL_LEFT]) == ("Own", "geometric")


def test_without_bounds_only_labeled_by_can_answer():
    unplaced = node(control_type="Edit")
    assert nearest_label(unplaced, [LABEL_LEFT]) == (None, None)
    assert nearest_label(dict(unplaced, labeled_by="X"), [LABEL_LEFT]) == (
        "X",
        "labeledBy",
    )


def test_a_degenerate_rectangle_is_not_a_position():
    collapsed = node(control_type="Edit", bounds=(100, 10, 100, 10))
    assert nearest_label(collapsed, [LABEL_LEFT]) == (None, None)


# --- describe_tree -----------------------------------------------------------------------


TREE = [
    node(
        id=0, parent=None, control_type="Window", name="Login", bounds=(0, 0, 400, 200)
    ),
    node(id=1, parent=0, control_type="Pane", bounds=(0, 0, 400, 200)),
    node(id=2, parent=1, control_type="Text", name="Username", bounds=(0, 10, 90, 30)),
    node(
        id=3,
        parent=1,
        control_type="Edit",
        automation_id="usernameInput",
        bounds=(100, 10, 300, 30),
    ),
    node(
        id=4,
        parent=1,
        control_type="Button",
        automation_id="1001",
        name="OK",
        bounds=(100, 50, 200, 80),
    ),
]


def test_describe_tree_computes_path_index_and_label():
    elements = describe_tree(TREE)
    field = elements[3]
    assert field.parent_path == "Window/Pane"
    assert field.sibling_index == 1  # after the Text, among the Pane's children
    assert field.nearest_label == "Username"
    assert field.nearest_label_source == "geometric"


def test_the_root_has_no_parent_path_and_index_zero():
    root = describe_tree(TREE)[0]
    assert root.parent_path is None
    assert root.sibling_index == 0


def test_describe_tree_keeps_read_properties_and_drops_blanks():
    button = describe_tree(TREE)[4]
    assert button.automation_id == "1001"
    assert button.name == "OK"
    assert button.help_text is None


def test_an_explicit_sibling_index_is_kept():
    nodes = [
        node(id=0, parent=None, control_type="Window"),
        node(id=1, parent=0, control_type="Edit", sibling_index=7),
    ]
    assert describe_tree(nodes)[1].sibling_index == 7


# --- the JSON form -----------------------------------------------------------------------


def test_to_json_is_camel_case_and_leaves_out_what_is_missing():
    element = Element(
        automation_id="loginButton",
        control_type="Button",
        name="  ",
        bounds=(1, 2, 3, 4),
        sibling_index=0,
        enabled=True,
    )
    assert element.to_json() == {
        "automationId": "loginButton",
        "controlType": "Button",
        "bounds": [1, 2, 3, 4],
        "siblingIndex": 0,
        "enabled": True,
    }


def test_false_and_zero_survive_the_blank_filter():
    element = Element(enabled=False, offscreen=False, sibling_index=0)
    assert element.to_json() == {
        "enabled": False,
        "offscreen": False,
        "siblingIndex": 0,
    }


def test_json_round_trip():
    element = Element(
        automation_id="a",
        name="b",
        control_type="Edit",
        class_name="QLineEdit",
        framework_id="Qt",
        bounds=(1, 2, 3, 4),
        dpi=120,
        parent_path="Window/Pane",
        sibling_index=2,
        nearest_label="Username",
        nearest_label_source="geometric",
        window_title="Login",
        enabled=True,
        offscreen=False,
        help_text="help",
        access_key="Alt+U",
        native_window_handle=12345,
    )
    assert Element.from_json(element.to_json()) == element


def test_a_document_carries_the_version():
    document = Element(name="x").to_document()
    assert document["version"] == VERSION
    assert Element.from_document(document) == Element(name="x")


def test_a_document_of_another_version_is_refused():
    with pytest.raises(ValueError, match="0.9"):
        Element.from_document({"version": "0.9", "element": {}})


def test_an_unknown_property_is_refused_like_the_schema_refuses_it():
    with pytest.raises(ValueError, match="runtimeId"):
        Element.from_json({"name": "x", "runtimeId": [7, 1, 2]})


# --- the matching rules ------------------------------------------------------------------


def test_the_primary_property_follows_the_priority():
    assert (
        Element(automation_id="loginButton", name="OK").primary_property()
        == "automation_id"
    )
    assert Element(name="OK", nearest_label="Username").primary_property() == "name"
    assert Element(nearest_label="Username").primary_property() == "nearest_label"
    assert Element(bounds=(0, 0, 1, 1)).primary_property() is None


def test_a_generated_id_is_never_primary():
    element = Element(automation_id="1001", name="OK")
    assert element.primary_property() == "name"


def test_never_match_and_priority_do_not_overlap():
    assert not set(PRIMARY_PRIORITY) & set(NEVER_MATCH)


# --- the schema and the descriptor agree --------------------------------------------------


def schema_properties() -> set[str]:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    return set(schema["$defs"]["element"]["properties"])


def test_every_descriptor_property_is_in_the_schema():
    from ayna_agent.model import JSON_NAMES

    assert set(JSON_NAMES.values()) == schema_properties()


def test_the_schema_version_matches_the_module():
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert schema["properties"]["version"]["const"] == VERSION


def test_the_descriptor_is_a_superset_of_the_healing_proposal_s_scored_element():
    # The scorer's input must stay valid as a descriptor, or a proposal cannot be rebuilt
    # from a stored element (#149, #166).
    proposal = json.loads(
        (SCHEMA.parent / "healing-proposal.schema.json").read_text(encoding="utf-8")
    )
    scored = set(proposal["$defs"]["scoredElement"]["properties"])
    assert scored <= schema_properties()


# --- the real trial app ------------------------------------------------------------------

TRIAL_TREE = Path(__file__).resolve().parent / "data" / "trial-app-tree.json"


def trial_elements():
    """Descriptors for the PySide6 trial app, from a tree captured on Windows (#9, #11).

    Captured with UI Automation on 2026-10-31 at 125 % scaling (`dpi: 120`), so the rules
    are exercised against a real Qt tree — including the window frame, whose controls carry
    no AutomationId in any toolkit.
    """
    nodes = json.loads(TRIAL_TREE.read_text(encoding="utf-8"))
    return nodes, describe_tree(nodes)


def test_every_element_of_the_trial_app_gets_a_descriptor():
    nodes, elements = trial_elements()
    assert len(elements) == len(nodes) == 14
    assert all(e.control_type for e in elements)


def test_the_trial_app_s_inputs_are_labelled_and_nothing_else_is():
    _nodes, elements = trial_elements()
    labelled = {e.automation_id: e.nearest_label for e in elements if e.nearest_label}
    assert labelled == {
        "QApplication.loginWindow.usernameInput": "Username",
        "QApplication.loginWindow.passwordInput": "Password",
    }
    # The check box and the button sit under the password label but are not labelled by it.
    for element in elements:
        if element.automation_id in {
            "QApplication.loginWindow.rememberMeCheckBox",
            "QApplication.loginWindow.loginButton",
        }:
            assert element.nearest_label is None


def test_the_trial_app_s_frame_buttons_have_no_automation_id():
    # Measured in #9: Minimize/Maximize/Close belong to the window frame, not to the app,
    # and carry no AutomationId in any toolkit. The frame's MenuBar does have one.
    _nodes, elements = trial_elements()
    buttons = [
        e
        for e in elements
        if e.control_type == "Button" and (e.parent_path or "").endswith("TitleBar")
    ]
    assert len(buttons) == 3
    assert all(e.automation_id is None for e in buttons)
    assert {e.name for e in buttons} == {"Minimize", "Maximize", "Close"}


def test_the_trial_app_s_paths_and_indices_are_computed():
    _nodes, elements = trial_elements()
    login = next(
        e
        for e in elements
        if e.automation_id and e.automation_id.endswith("loginButton")
    )
    assert login.parent_path == "Window"
    assert login.sibling_index == 6
    assert login.dpi == 120
    assert login.window_title == "AYNA Trial - Login"


def test_every_trial_descriptor_round_trips_through_json():
    _nodes, elements = trial_elements()
    assert [Element.from_json(e.to_json()) for e in elements] == elements


# --- the schema itself -------------------------------------------------------------------

CASES = SCHEMA.parent / "examples" / "element" / "cases.json"


def validator():
    """A Draft 2020-12 validator, or skip: `jsonschema` is not an agent dependency yet (#11)."""
    jsonschema = pytest.importorskip(
        "jsonschema",
        reason="add jsonschema to agent's dev dependencies to run the schema tests",
    )
    return jsonschema.Draft202012Validator(
        json.loads(SCHEMA.read_text(encoding="utf-8"))
    )


def as_document(case):
    if "document" in case:
        return case["document"]
    return {"version": VERSION, "element": case["element"]}


def test_the_named_valid_cases_pass_the_schema():
    check = validator()
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    for case in cases["valid"]:
        errors = list(check.iter_errors(as_document(case)))
        assert not errors, f"{case['name']}: {errors[0].message if errors else ''}"


def test_the_named_invalid_cases_are_refused_by_the_rule_they_name():
    check = validator()
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    for case in cases["invalid"]:
        rules = {error.validator for error in check.iter_errors(as_document(case))}
        assert case["rule"] in rules, f"{case['name']}: refused by {rules or 'nothing'}"


def test_every_trial_app_descriptor_validates():
    check = validator()
    _nodes, elements = trial_elements()
    for element in elements:
        errors = list(check.iter_errors(element.to_document()))
        assert not errors, f"{element.to_json()}: {errors[0].message if errors else ''}"
