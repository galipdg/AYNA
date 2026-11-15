"""Tests for the pieces `Select` is built from: the tree of one read, and the item ladder (#40).

The rules worth a test of their own here, rather than through the runner:

- **an item is any descendant**, not a direct child, because WPF and Qt both nest the
  `ListItem`s under an inner `List`;
- **`id`, not position, is the parent link** -- the walk numbers them alike today and a tree
  that did not would otherwise report the wrong children silently;
- **a cell's or an item's text is one rule** (ValuePattern when non-empty, else Name), stated
  once in the step schema and implemented once here, so `Select` and the row checks cannot
  drift apart;
- **the ladders**: `SelectionItem` before `Invoke`, and the editable-combo `SetValue` only
  after a read-back confirms the box took the text.

Everything is injected, so none of it needs Windows (`agent/AGENTS.md`).
"""

from __future__ import annotations

from ayna_agent.model import Element
from ayna_agent.playback import items, tree


def node(id_, parent, control_type, name=None, **extra):
    return {
        "id": id_,
        "parent": parent,
        "control_type": control_type,
        "name": name,
        "enabled": True,
        "offscreen": False,
        **extra,
    }


def read(nodes):
    """A `Tree` whose live elements name themselves, so a test can assert on what was acted on."""
    return tree.of(nodes, [f"{n['control_type']}:{n.get('name')}" for n in nodes])


#: A combo box as WPF and Qt expose an open one: the items are under an inner `List`.
OPEN_COMBO = [
    node(0, None, "Window", "Liste"),
    node(1, 0, "ComboBox", "Adana", automation_id="cityCombo"),
    node(2, 1, "List", "cityCombo list"),
    node(3, 2, "ListItem", "Adana"),
    node(4, 2, "ListItem", "Ankara"),
    node(5, 0, "Button", "Tamam"),
]


# --- the tree of one read ------------------------------------------------------------------


def test_descendants_are_pre_order_and_exclude_the_element_itself():
    """Pre-order is the order the application shows things in, which is what makes "the first
    item with that text" mean the same thing here as on screen."""
    assert read(OPEN_COMBO).descendants(0) == [1, 2, 3, 4, 5]
    assert read(OPEN_COMBO).descendants(1) == [2, 3, 4]
    assert read(OPEN_COMBO).descendants(3) == []


def test_the_parent_link_is_the_node_id_not_its_position():
    """`describe_tree` already treats `id` as the link. A tree whose ids are not its positions
    would otherwise give the wrong children -- the worst failure a selector can have, because
    it reports success on the wrong element."""
    shifted = [
        node(100, None, "Window", "Liste"),
        node(101, 100, "List", "cities"),
        node(102, 101, "ListItem", "Ankara"),
    ]
    assert read(shifted).children(0) == (1,)
    assert read(shifted).descendants(0) == [1, 2]


def test_a_node_whose_parent_is_outside_the_read_is_a_root():
    """A walk truncated by its budget (#226) can hand over a child whose parent it never
    reached, and that child still has to be reachable -- `descendants` of the window would
    otherwise skip a whole subtree while reporting success on the rest."""
    orphaned = [
        node(0, None, "Window", "Liste"),
        node(1, 99, "ListItem", "Ankara"),
    ]
    assert read(orphaned).descendants(0) == []
    assert items.items_of(read(orphaned), 0) == []


# --- the text a cell or an item shows ------------------------------------------------------


class Value:
    """Patterns where every element answers `Value` with `text`."""

    def __init__(self, text):
        self.text = text

    def __call__(self, element, name):
        if name != "Value":
            return None
        recorder = self

        class V:
            CurrentIsReadOnly = False

            @property
            def CurrentValue(self):
                # A property, not a snapshot: the real `CurrentValue` is read from the
                # provider each time, which is what makes the read-back in `items.write`
                # mean anything.
                return recorder.text

            def SetValue(self, value):
                recorder.text = value

        return V()


def test_a_non_empty_value_pattern_wins_over_the_name():
    """A WinForms `DataGridView` cell's Name is its column header plus row index and its text
    is the Value, so reading the Name would address rows by the wrong string entirely."""
    descriptor = Element(name="Soyad Row 2")
    assert tree.displayed_text(descriptor, "cell", Value("Yılmaz")) == "Yılmaz"


def test_an_empty_value_pattern_falls_back_to_the_name():
    """Qt cells and list items carry their text in Name and answer ValuePattern with ""."""
    descriptor = Element(name="Ankara")
    assert tree.displayed_text(descriptor, "item", Value("")) == "Ankara"
    assert tree.displayed_text(descriptor, "item", lambda e, n: None) == "Ankara"


def test_the_text_is_compared_in_the_form_a_descriptor_stores_it():
    """Stripped, and blank is nothing -- so the value a tester reads in the Spy is the value
    their step can write."""
    assert (
        tree.displayed_text(Element(name="  Ankara  "), "item", Value(None)) == "Ankara"
    )
    assert tree.displayed_text(Element(name=None), "item", Value("  ")) is None


def test_a_provider_that_raises_on_the_value_is_read_as_having_none():
    class Raising:
        def __call__(self, element, name):
            class V:
                @property
                def CurrentValue(self):
                    raise OSError("the provider died mid-call")

            return V() if name == "Value" else None

    assert tree.displayed_text(Element(name="Ankara"), "item", Raising()) == "Ankara"


# --- which elements are items --------------------------------------------------------------


def test_items_are_descendants_not_only_children():
    """WPF keeps a combo box's `ListItem`s under an inner `List`, so "the children of the
    combo box" would find nothing at all."""
    assert items.items_of(read(OPEN_COMBO), 1) == [3, 4]


def test_a_label_inside_a_list_is_not_an_item():
    """Choosing one would act on the wrong element while reporting success."""
    nodes = [
        node(0, None, "List", "cities"),
        node(1, 0, "Text", "Ankara"),
        node(2, 0, "ListItem", "Ankara"),
    ]
    assert items.items_of(read(nodes), 0) == [2]


def test_find_answers_with_the_item_and_how_many_the_target_has():
    position, count = items.find(read(OPEN_COMBO), 1, "Ankara", lambda e, n: None)
    assert (position, count) == (4, 2)


def test_find_says_how_many_items_there_are_even_when_none_matches():
    """The count is what separates "the list never filled" from "the text is wrong", and the
    message a tester reads is built from it."""
    assert items.find(read(OPEN_COMBO), 1, "Bursa", lambda e, n: None) == (None, 2)


def test_the_first_item_with_that_text_wins():
    """The schema's own rule for a row ("the first row from the top"), applied to an item: a
    list's order is what the user sees, unlike the child order `resolve` refuses to trust."""
    nodes = [
        node(0, None, "List", "cities"),
        node(1, 0, "ListItem", "Ankara"),
        node(2, 0, "ListItem", "Ankara"),
    ]
    position, count = items.find(read(nodes), 0, "Ankara", lambda e, n: None)
    assert (position, count) == (1, 2)


# --- the ladders ---------------------------------------------------------------------------


class Item:
    """One item, with switchable support for each pattern."""

    def __init__(self, *, selection_item=True, invoke=True, legacy=True, refuses=()):
        self.selection_item = selection_item
        self.invoke = invoke
        self.legacy = legacy
        self.refuses = refuses
        self.tried: list[str] = []

    def __call__(self, element, name):
        recorder = self
        if name == "SelectionItem" and self.selection_item:

            class S:
                def Select(self):
                    recorder.tried.append("SelectionItem")
                    if "SelectionItem" in recorder.refuses:
                        raise OSError("the provider refused")

            return S()
        if name == "Invoke" and self.invoke:

            class I:
                def Invoke(self):
                    recorder.tried.append("Invoke")
                    if "Invoke" in recorder.refuses:
                        raise OSError("the provider refused")

            return I()
        if name == "LegacyIAccessible" and self.legacy:

            class L:
                def DoDefaultAction(self):
                    recorder.tried.append("LegacyIAccessible")
                    if "LegacyIAccessible" in recorder.refuses:
                        raise OSError("the provider refused")

            return L()
        return None


def took():
    """A `confirm` that says the choice reached the control."""
    return True


def did_not_take():
    """A `confirm` that says it did not -- the Qt no-op."""
    return False


def test_choose_prefers_selection_item_because_that_is_what_choosing_means():
    patterns = Item()
    assert items.choose("item", patterns, confirm=took) == "SelectionItem"
    assert patterns.tried == ["SelectionItem"]


def test_choose_falls_back_to_invoke_for_a_menu_item():
    """A menu item is activated rather than selected, and has no SelectionItem."""
    patterns = Item(selection_item=False)
    assert items.choose("item", patterns, confirm=took) == "Invoke"


def test_a_pattern_that_is_there_and_refuses_moves_to_the_next():
    patterns = Item(refuses=("SelectionItem",))
    assert items.choose("item", patterns, confirm=took) == "Invoke"
    assert patterns.tried == ["SelectionItem", "Invoke"]


def test_choose_answers_none_when_every_rung_refuses_rather_than_raising():
    """The Qt case (#33): the caller turns it into a message about the application, after
    trying the editable-combo fallback."""
    patterns = Item(refuses=("SelectionItem", "Invoke", "LegacyIAccessible"))
    assert items.choose("item", patterns, confirm=took) is None


def test_an_element_with_no_pattern_at_all_cannot_be_chosen():
    patterns = Item(selection_item=False, invoke=False, legacy=False)
    assert items.choose("item", patterns, confirm=took) is None


def test_legacy_do_default_action_is_the_last_rung_and_the_one_qt_honours():
    """Measured on the sample app's Qt combo box (#40 Windows check): SelectionItem and Invoke
    return without complaint and change nothing, DoDefaultAction is the only route."""
    patterns = Item(selection_item=False, invoke=False)
    assert items.choose("item", patterns, confirm=took) == "LegacyIAccessible"
    assert patterns.tried == ["LegacyIAccessible"]


def test_a_rung_that_succeeds_but_changes_nothing_falls_through_to_the_next():
    """The whole reason `confirm` exists: Qt's SelectionItem.Select() accepts the call, does
    nothing, and the item then reports IsSelected true. Reporting that rung as the winner is a
    false `passed`, which is the one failure a tester cannot debug."""
    patterns = Item()
    confirmed = [False, True]
    performed = items.choose("item", patterns, confirm=lambda: confirmed.pop(0))
    assert performed == "Invoke"
    assert patterns.tried == ["SelectionItem", "Invoke"]


def test_a_ladder_whose_every_rung_is_unconfirmed_chose_nothing():
    patterns = Item()
    assert items.choose("item", patterns, confirm=did_not_take) is None
    assert patterns.tried == ["SelectionItem", "Invoke", "LegacyIAccessible"]


# --- the read-back that makes the ladder trustworthy ----------------------------------------

RAISES = object()
UNSET = object()


class ReadBack:
    """A target and an item, each with a readable, unreadable or absent property."""

    def __init__(self, *, shown=UNSET, selected=None):
        self.shown = shown
        self.selected = selected

    def __call__(self, element, name):
        outer = self
        if element == "target" and name == "Value" and self.shown is not UNSET:

            class V:
                @property
                def CurrentValue(self):
                    if outer.shown is RAISES:
                        raise OSError("the provider died mid-call")
                    return outer.shown

            return V()
        if element == "item" and name == "SelectionItem" and self.selected is not None:

            class S:
                @property
                def CurrentIsSelected(self):
                    return outer.selected

            return S()
        return None


def test_the_targets_value_decides_over_an_item_that_claims_to_be_selected():
    """The Qt measurement (#40 Windows check): after the no-op Select the item reports
    IsSelected true while the combo still shows its old value. That flag records the popup
    highlight, not the choice, so the box's own value is the authority."""
    patterns = ReadBack(shown="Tümü", selected=True)
    assert items.took_effect("target", "item", "Ankara", patterns) is False


def test_the_targets_value_confirms_the_choice_when_it_reads_as_the_item():
    patterns = ReadBack(shown="Ankara", selected=False)
    assert items.took_effect("target", "item", "Ankara", patterns) is True


def test_a_target_with_no_value_pattern_falls_back_to_the_items_own_flag():
    """A plain list has no Value of its own, and there the item's IsSelected is all there is."""
    assert (
        items.took_effect("target", "item", "Ankara", ReadBack(selected=True)) is True
    )
    assert (
        items.took_effect("target", "item", "Ankara", ReadBack(selected=False)) is False
    )


def test_a_value_that_cannot_be_read_falls_through_to_the_item_rather_than_failing():
    patterns = ReadBack(shown=RAISES, selected=True)
    assert items.took_effect("target", "item", "Ankara", patterns) is True


def test_nothing_readable_leaves_the_ladders_own_success_standing():
    """A menu item is gone the moment it is invoked: there is no evidence either way, and
    refusing it would make Select unplayable on a menu."""
    assert items.took_effect("target", "item", "Ankara", ReadBack()) is True


# --- the editable combo box, read back -----------------------------------------------------


def test_write_takes_the_text_and_confirms_it():
    patterns = Value("Adana")
    assert items.write("combo", "Ankara", patterns) is True
    assert patterns.text == "Ankara"


def test_write_refuses_a_box_that_did_not_take_the_text():
    """`SetValue` returns without complaint on a provider that then ignores or normalises the
    text, and "AYNA says it chose Ankara" while the box still reads "Adana" is the one outcome
    a tester cannot debug."""

    class Ignoring(Value):
        def __call__(self, element, name):
            pattern = super().__call__(element, name)
            if pattern is not None:
                pattern.SetValue = lambda value: None
            return pattern

    assert items.write("combo", "Ankara", Ignoring("Adana")) is False


def test_write_refuses_a_read_only_box():
    class ReadOnly(Value):
        def __call__(self, element, name):
            pattern = super().__call__(element, name)
            if pattern is not None:
                pattern.CurrentIsReadOnly = True
            return pattern

    assert items.write("combo", "Ankara", ReadOnly("Adana")) is False


def test_write_refuses_an_element_with_no_value_pattern():
    assert items.write("combo", "Ankara", lambda e, n: None) is False


# --- what the target offers ----------------------------------------------------------------


class Offers:
    def __init__(self, *names):
        self.names = names

    def __call__(self, element, name):
        return object() if name in self.names else None


def test_a_selection_pattern_makes_an_element_a_possible_list():
    """Asked only when the target shows no items, to tell "not a list" from "a list that is
    empty or still filling"."""
    assert items.selectable("list", Offers("Selection")) is True
    assert items.selectable("combo", Offers("ExpandCollapse")) is True
    assert items.selectable("button", Offers("Invoke")) is False


def test_expand_and_collapse_report_whether_the_provider_did_it():
    class Box:
        def __init__(self):
            self.done: list[str] = []

        def __call__(self, element, name):
            recorder = self
            if name != "ExpandCollapse":
                return None

            class E:
                def Expand(self):
                    recorder.done.append("Expand")

                def Collapse(self):
                    recorder.done.append("Collapse")

            return E()

    box = Box()
    assert items.expand("combo", box) is True
    assert items.collapse("combo", box) is True
    assert box.done == ["Expand", "Collapse"]
    assert items.expand("combo", lambda e, n: None) is False
    assert items.collapse("combo", lambda e, n: None) is False


# --- the three failures, each worded for the tester who fixes it ---------------------------


def test_not_a_list_names_what_select_needs():
    message = items.not_a_list("login.okButton")
    assert message.startswith("login.okButton: ")
    assert "Select needs a list or a combo box" in message


def test_no_such_item_says_how_many_items_there_are_and_how_long_it_waited():
    message = items.no_such_item("list.city", "Bursa", 3, 5000)
    assert message == (
        'list.city: no item has the text "Bursa" after 5000 ms; the target offers 3 items'
    )


def test_no_such_item_says_nothing_about_waiting_when_it_did_not_wait():
    assert items.no_such_item("list.city", "Bursa", 1, 0) == (
        'list.city: no item has the text "Bursa"; the target offers 1 item'
    )


def test_a_list_with_no_items_at_all_is_worded_as_its_own_case():
    """0 items and 12 items send a tester in different directions: a list that never filled,
    or a popup window of its own, against a value that is simply wrong."""
    message = items.no_such_item("list.city", "Bursa", 0, 1000)
    assert "shows no items at all" in message
    assert "popup window of its own" in message


def test_refused_blames_the_application_not_the_test():
    message = items.refused("list.city", "Ankara", ("SelectionItem", "Invoke"))
    assert message == (
        'list.city: the item "Ankara" is there, but the application refused to select it '
        "(SelectionItem and Invoke were tried)"
    )


def test_refused_names_the_whole_ladder_the_runner_actually_tried():
    """Pinned against `CHOOSE_PATTERNS` rather than a tuple of its own, so the message a
    tester reads cannot drift from the rungs `choose` really walks."""
    message = items.refused("list.city", "Ankara", items.CHOOSE_PATTERNS)
    assert message == (
        'list.city: the item "Ankara" is there, but the application refused to select it '
        "(SelectionItem, Invoke and LegacyIAccessible were tried)"
    )


def test_vanished_reads_like_the_checkpoint_s_own_wording():
    message = items.vanished(RuntimeError("no element matches list.city"), "Ankara")
    assert message == 'no element matches list.city while choosing "Ankara"'
