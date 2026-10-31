"""Tests for the OS-independent parts of uia_probe.py (#161).

The measurement itself needs Windows and a running application; everything that decides
what is measured and how it is reported is pure and tested here.
"""

from __future__ import annotations

import unittest

from uia_probe import (
    MODES,
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


if __name__ == "__main__":
    unittest.main()
