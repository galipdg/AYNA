"""Tests for the OS-independent parts of uia_probe.py (#161).

The measurement itself needs Windows and a running application; everything that decides
what is measured and how it is reported is pure and tested here. The walk is included: it
only asks its nodes for `element`, `children()` and `handle`, so fake nodes exercise the
deduplication that #12 depends on without UI Automation.
"""

from __future__ import annotations

import unittest

from uia_probe import (
    MODES,
    Probe,
    nesting_order,
    percentiles,
    selected_modes,
    share,
    slowest_table,
    summary_table,
)


class PercentilesTest(unittest.TestCase):

    def test_empty_input_has_no_percentiles(self):
        self.assertEqual(percentiles([]), {})

    def test_single_value_is_every_percentile(self):
        self.assertEqual(percentiles([4.0]), {"min": 4.0, "max": 4.0, "p50": 4.0, "p90": 4.0,
                                              "p99": 4.0})

    def test_nearest_rank_picks_an_observed_value(self):
        values = [float(v) for v in range(1, 101)]      # 1..100
        result = percentiles(values)
        self.assertEqual(result["min"], 1.0)
        self.assertEqual(result["max"], 100.0)
        self.assertEqual(result["p50"], 50.0)
        self.assertEqual(result["p90"], 90.0)
        self.assertEqual(result["p99"], 99.0)

    def test_input_order_does_not_matter(self):
        self.assertEqual(percentiles([9.0, 1.0, 5.0]), percentiles([1.0, 5.0, 9.0]))

    def test_one_outlier_moves_the_max_but_not_the_median(self):
        flat = [1.0] * 99
        result = percentiles(flat + [1000.0])
        self.assertEqual(result["p50"], 1.0)
        self.assertEqual(result["max"], 1000.0)

    def test_requested_points_are_configurable(self):
        result = percentiles([1.0, 2.0, 3.0, 4.0], points=(25,))
        self.assertEqual(result["p25"], 1.0)
        self.assertNotIn("p50", result)


class ShareTest(unittest.TestCase):

    def test_zero_whole_is_not_a_division_error(self):
        self.assertEqual(share(3.0, 0.0), "—")

    def test_share_is_rounded_to_whole_percent(self):
        self.assertEqual(share(1.0, 4.0), "25%")
        self.assertEqual(share(2.0, 3.0), "67%")


class SelectedModesTest(unittest.TestCase):

    def test_no_selection_means_every_mode(self):
        self.assertEqual(selected_modes(None), list(MODES))
        self.assertEqual(selected_modes(""), list(MODES))

    def test_subset_keeps_the_given_order(self):
        self.assertEqual(selected_modes("full,navigate"), ["full", "navigate"])

    def test_whitespace_and_empty_items_are_ignored(self):
        self.assertEqual(selected_modes(" navigate , , properties "), ["navigate", "properties"])

    def test_unknown_mode_is_refused_by_name(self):
        with self.assertRaises(ValueError) as caught:
            selected_modes("navigate,sideways")
        self.assertIn("sideways", str(caught.exception))


def result_with(modes: list[dict]) -> dict:
    return {"modes": modes}


def mode(name: str, elements: int, total: float, stats: dict | None = None) -> dict:
    return {"mode": name, "elements": elements, "total_s": total,
            "per_element_ms": stats if stats is not None else {"p50": 1.0, "p90": 2.0,
                                                               "p99": 3.0, "max": 4.0},
            "slowest": []}


class SummaryTableTest(unittest.TestCase):

    def test_every_mode_gets_a_row(self):
        table = summary_table(result_with([mode("navigate", 10, 1.0), mode("full", 10, 4.0)]))
        lines = table.splitlines()
        self.assertEqual(len(lines), 4)                 # header, rule, two modes
        self.assertIn("navigate", lines[2])
        self.assertIn("full", lines[3])

    def test_share_is_measured_against_the_full_walk(self):
        table = summary_table(result_with([mode("navigate", 10, 1.0), mode("full", 10, 4.0)]))
        self.assertIn("25%", table)
        self.assertIn("100%", table)

    def test_missing_full_mode_leaves_the_share_empty(self):
        table = summary_table(result_with([mode("navigate", 10, 1.0)]))
        self.assertIn("—", table)

    def test_mean_is_per_element_in_milliseconds(self):
        table = summary_table(result_with([mode("full", 100, 10.0)]))
        self.assertIn("100.00", table)                  # 10 s / 100 elements = 100 ms

    def test_zero_elements_does_not_divide(self):
        table = summary_table(result_with([mode("full", 0, 0.0, {})]))
        self.assertIn("—", table)


class SlowestTableTest(unittest.TestCase):

    def test_rows_are_limited_and_fields_are_clipped(self):
        slow = [{"ms": 1000.0 - i, "control_type": "Button", "name": "x" * 50,
                 "automation_id": "a" * 40, "class_name": "c" * 40, "depth": i}
                for i in range(5)]
        table = slowest_table({"slowest": slow}, limit=2)
        lines = table.splitlines()
        self.assertEqual(len(lines), 4)                 # header, rule, two rows
        self.assertNotIn("x" * 29, table)

    def test_missing_text_is_rendered_as_empty(self):
        slow = [{"ms": 5.0, "control_type": "Pane", "name": None, "automation_id": None,
                 "class_name": None, "depth": 0}]
        table = slowest_table({"slowest": slow})
        self.assertIn("Pane", table)


class NestingOrderTest(unittest.TestCase):

    def test_an_owner_comes_before_the_dialog_nested_in_it(self):
        self.assertEqual(nesting_order([7, 5], {7: {5}, 5: set()}), [5, 7])

    def test_unrelated_windows_keep_the_given_order(self):
        self.assertEqual(nesting_order([7, 5], {7: set(), 5: set()}), [7, 5])

    def test_ancestors_that_are_not_roots_do_not_count(self):
        self.assertEqual(nesting_order([7, 5], {7: {999}, 5: {999}}), [7, 5])

    def test_three_levels_are_ordered_outermost_first(self):
        order = nesting_order([3, 2, 1], {3: {1, 2}, 2: {1}, 1: set()})
        self.assertEqual(order, [1, 2, 3])

    def test_a_missing_entry_is_treated_as_no_ancestors(self):
        self.assertEqual(nesting_order([7, 5], {5: {7}}), [7, 5])


class FakeElement:
    """Answers only the four identity properties `Probe.identity` reads."""

    def __init__(self, name: str) -> None:
        self.CurrentControlType = 50000
        self.CurrentName = name
        self.CurrentAutomationId = ""
        self.CurrentClassName = ""


class FakeInfo:
    """A node of a fake UIA tree: an element, its children and its window handle (0 = none)."""

    def __init__(self, name: str, handle: int = 0, children: list | None = None) -> None:
        self.element = FakeElement(name)
        self.handle = handle
        self._children = children or []

    def children(self) -> list:
        return list(self._children)


def names(result: dict) -> list[str]:
    return sorted(el["name"] for el in result["slowest"])


class WalkTest(unittest.TestCase):
    """`navigate` does no property read, so the walk itself is what is under test."""

    def probe(self) -> Probe:
        return Probe(pattern_ids=[], type_names={})

    def test_every_element_is_walked_once(self):
        tree = FakeInfo("main", 5, [FakeInfo("button"), FakeInfo("edit")])
        result = self.probe().run([tree], "navigate")
        self.assertEqual(result["elements"], 3)
        self.assertEqual(result["duplicates_skipped"], 0)
        self.assertEqual(result["read_errors"], 0)

    def test_a_window_that_is_also_a_child_is_walked_once(self):
        dialog = FakeInfo("dialog", 7, [FakeInfo("ok")])
        main = FakeInfo("main", 5, [FakeInfo("toolbar"), dialog])
        result = self.probe().run([main, dialog], "navigate")
        self.assertEqual(result["elements"], 4)          # not 6: the dialog subtree once
        self.assertEqual(result["duplicates_skipped"], 1)
        self.assertEqual(names(result), ["dialog", "main", "ok", "toolbar"])

    def test_the_skipped_duplicate_takes_its_subtree_with_it(self):
        dialog = FakeInfo("dialog", 7, [FakeInfo("ok"), FakeInfo("cancel")])
        result = self.probe().run([dialog, dialog], "navigate")
        self.assertEqual(result["elements"], 3)
        self.assertEqual(result["duplicates_skipped"], 1)

    def test_elements_without_a_handle_are_never_skipped(self):
        same = [FakeInfo("row"), FakeInfo("row"), FakeInfo("row")]
        result = self.probe().run([FakeInfo("list", 9, same)], "navigate")
        self.assertEqual(result["elements"], 4)
        self.assertEqual(result["duplicates_skipped"], 0)

    def test_depth_is_the_depth_under_the_root_that_won(self):
        dialog = FakeInfo("dialog", 7, [FakeInfo("ok")])
        main = FakeInfo("main", 5, [dialog])
        result = self.probe().run([main, dialog], "navigate")
        depth = {el["name"]: el["depth"] for el in result["slowest"]}
        self.assertEqual(depth["dialog"], 1)             # as the owner's child, not as a root
        self.assertEqual(depth["ok"], 2)

    def test_a_failing_handle_read_is_counted_but_does_not_drop_the_element(self):
        class Unreadable(FakeInfo):
            @property
            def handle(self):
                raise OSError("gone")

            @handle.setter
            def handle(self, value):
                pass

        result = self.probe().run([Unreadable("ghost")], "navigate")
        self.assertEqual(result["elements"], 1)
        self.assertEqual(result["read_errors"], 1)


if __name__ == "__main__":
    unittest.main()
