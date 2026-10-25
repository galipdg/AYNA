"""Unit tests for uia_dump.py that run on any OS (no pywinauto needed).

    python3 -m unittest discover -s eval/spikes -p "test_*.py" -v
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import uia_dump  # noqa: E402


def node(name: str, *kids: SimpleNamespace) -> SimpleNamespace:
    return SimpleNamespace(name=name, kids=list(kids))


def flatten(roots: list, **limits: int) -> tuple[list[dict], bool]:
    return uia_dump.walk(roots, lambda n: {"name": n.name}, lambda n: n.kids, **limits)


def element(id_: int, parent: int | None, control_type: str, automation_id: str = "",
            name: str = "") -> dict:
    return {"id": id_, "parent": parent, "control_type": control_type,
            "automation_id": automation_id, "name": name}


def dump_doc(elements: list[dict], **target: str) -> dict:
    return {"format": uia_dump.FORMAT, "target": {"id": "demo", **target},
            "app": {"file_version": "1.2.3.4"}, "walk": {"seconds": 0.5}, "elements": elements}


class WalkTest(unittest.TestCase):
    def test_pre_order_with_parents_depths_and_sibling_indexes(self):
        elements, truncated = flatten([node("A", node("B", node("D")), node("C"))])
        self.assertEqual([e["name"] for e in elements], ["A", "B", "D", "C"])
        self.assertEqual([e["id"] for e in elements], [0, 1, 2, 3])
        self.assertEqual([e["parent"] for e in elements], [None, 0, 1, 0])
        self.assertEqual([e["depth"] for e in elements], [0, 1, 2, 1])
        self.assertEqual([e["index"] for e in elements], [0, 0, 0, 1])
        self.assertFalse(truncated)

    def test_each_root_starts_its_own_tree(self):
        elements, _ = flatten([node("Main", node("OK")), node("Dialog")])
        self.assertEqual([(e["name"], e["parent"], e["index"]) for e in elements],
                         [("Main", None, 0), ("OK", 0, 0), ("Dialog", None, 1)])

    def test_max_nodes_cuts_the_walk(self):
        tree = [node("A", node("B"), node("C"), node("D"))]
        elements, truncated = flatten(tree, max_nodes=2)
        self.assertEqual([e["name"] for e in elements], ["A", "B"])
        self.assertTrue(truncated)
        self.assertFalse(flatten(tree, max_nodes=4)[1])

    def test_max_depth_skips_deeper_children(self):
        elements, truncated = flatten([node("A", node("B", node("C")))], max_depth=1)
        self.assertEqual([e["name"] for e in elements], ["A", "B"])
        self.assertTrue(truncated)

    def test_leaf_at_max_depth_is_not_truncation(self):
        self.assertFalse(flatten([node("A", node("B"))], max_depth=1)[1])


class FakeElement:
    """Raw IUIAutomationElement stand-in."""

    CurrentControlType = 50000  # UIA_ButtonControlTypeId
    CurrentAutomationId = "okButton"
    CurrentClassName = "Button"
    CurrentFrameworkId = "WPF"
    CurrentBoundingRectangle = SimpleNamespace(left=10, top=20, right=110, bottom=50)
    CurrentLocalizedControlType = "button"
    CurrentHelpText = ""
    CurrentAccessKey = "Alt+O"
    CurrentAcceleratorKey = ""
    CurrentLabeledBy = None  # NULL pointer
    CurrentIsEnabled = 1
    CurrentIsOffscreen = 0
    CurrentIsKeyboardFocusable = 1
    CurrentIsPassword = 0
    CurrentIsControlElement = 1
    CurrentIsContentElement = 1
    CurrentNativeWindowHandle = 0

    def GetCurrentPropertyValue(self, property_id: int) -> bool:  # noqa: N802 (COM name)
        return property_id == 30031


class BrokenElement(FakeElement):
    @property
    def CurrentFrameworkId(self) -> str:  # noqa: N802 (COM name)
        raise OSError("COM error: element not available")


class FakeInfo:
    """pywinauto UIAElementInfo stand-in: the reader only uses .element and .children()."""

    def __init__(self, name: str = "OK", kids: list | None = None, element: type = FakeElement):
        self.element = element()
        self.element.CurrentName = name
        self.kids = kids or []

    def children(self) -> list:
        return self.kids


class BrokenInfo(FakeInfo):
    def __init__(self) -> None:
        super().__init__(element=BrokenElement)

    def children(self) -> list:
        raise OSError("COM error: element not available")


class UiaReaderTest(unittest.TestCase):
    def setUp(self):
        self.reader = uia_dump.UiaReader({50000: "Button"}, [("Invoke", 30031), ("Value", 30043)])

    def test_reads_properties_bounds_and_patterns(self):
        e = self.reader.read(FakeInfo())
        self.assertEqual((e["control_type"], e["automation_id"], e["name"]),
                         ("Button", "okButton", "OK"))
        self.assertEqual(e["bounds"], [10, 20, 110, 50])
        self.assertEqual(e["patterns"], ["Invoke"])
        self.assertIs(e["enabled"], True)
        self.assertIs(e["has_hwnd"], False)
        self.assertIsNone(e["labeled_by"])
        self.assertEqual(self.reader.errors, 0)

    def test_failing_property_costs_only_its_value(self):
        e = self.reader.read(BrokenInfo())
        self.assertIsNone(e["framework_id"])
        self.assertEqual(e["automation_id"], "okButton")
        self.assertEqual(self.reader.children(BrokenInfo()), [])
        self.assertEqual(self.reader.errors, 2)

    def test_labeled_by_name_and_long_names_are_clipped(self):
        info = FakeInfo(name="x" * 500)
        info.element.CurrentLabeledBy = SimpleNamespace(CurrentName="User name:")
        e = self.reader.read(info)
        self.assertEqual(e["labeled_by"], "User name:")
        self.assertEqual(len(e["name"]), uia_dump.MAX_TEXT + 1)
        self.assertTrue(e["name"].endswith("…"))

    def test_unknown_control_type_keeps_its_id(self):
        info = FakeInfo()
        info.element.CurrentControlType = 50999
        self.assertEqual(self.reader.read(info)["control_type"], 50999)

    def test_no_pattern_ids_means_no_patterns_key(self):
        self.assertNotIn("patterns", uia_dump.UiaReader({}, []).read(FakeInfo()))

    def test_reader_works_as_walk_callbacks(self):
        tree = [FakeInfo("Main", [FakeInfo("OK"), FakeInfo("Cancel")])]
        elements, _ = uia_dump.walk(tree, self.reader.read, self.reader.children)
        self.assertEqual([e["name"] for e in elements], ["Main", "OK", "Cancel"])


class WriteDumpTest(unittest.TestCase):
    def test_round_trip_with_one_element_per_line(self):
        doc = dump_doc([element(0, None, "Window", "Main", "Şifre: ı"), element(1, 0, "Button")])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "demo.json"
            uia_dump.write_dump(doc, path)
            text = path.read_text(encoding="utf-8")
        self.assertEqual(json.loads(text), doc)
        self.assertEqual(sum(line.startswith('    {"id": ') for line in text.splitlines()), 2)
        self.assertIn("Şifre: ı", text)

    def test_empty_element_list_is_valid_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "empty.json"
            uia_dump.write_dump(dump_doc([]), path)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["elements"], [])


class RichnessTest(unittest.TestCase):
    def setUp(self):
        self.doc = dump_doc([
            element(0, None, "Window", "MainForm", "Main"),
            element(1, 0, "Button", "okButton", "OK"),
            element(2, 0, "Edit", "", "User name"),
            element(3, 0, "Button", "  ", " "),  # blank counts as missing
            element(4, 0, "MenuItem", "1001", "File"),
            element(5, 0, "CheckBox", "dup"),
            element(6, 5, "CheckBox", "dup"),  # same id twice in one window
            element(7, 0, "Text", "okButton", "Label"),  # not interactive, but clashes
            element(8, None, "Window", "Dialog"),
            element(9, 8, "Button", "cancelButton", "Cancel"),
            element(10, 8, "Edit", "1f0e3dad-9a8b-4c7d-8e6f-5a4b3c2d1e0f"),
        ])

    def test_counts_over_interactive_elements(self):
        r = uia_dump.richness(self.doc)
        self.assertEqual(r["elements"], 11)
        self.assertEqual(r["interactive"], 8)
        self.assertEqual(r["automation_id"], 6)
        self.assertEqual(r["automation_id_generated"], 2)  # "1001" and the GUID
        # Unique in their window: 1001, cancelButton, the GUID. okButton clashes with a Text.
        self.assertEqual(r["automation_id_unique"], 3)
        self.assertEqual(r["name"], 4)
        self.assertEqual(r["either"], 7)

    def test_window_frame_controls_are_not_interactive(self):
        r = uia_dump.richness(dump_doc([
            element(0, None, "Window", "MainForm", "Main"),
            element(1, 0, "TitleBar"),
            element(2, 1, "MenuBar", "", "System Menu Bar"),
            element(3, 2, "MenuItem", "", "System"),
            element(4, 1, "Button", "", "Close"),
            element(5, 0, "Button", "okButton", "OK"),
        ]))
        self.assertEqual((r["elements"], r["frame"], r["interactive"]), (6, 4, 1))
        self.assertEqual(r["automation_id"], 1)

    def test_by_type_counts_every_element(self):
        by_type = uia_dump.richness(self.doc)["by_type"]
        self.assertEqual(by_type["Button"], {"count": 3, "automation_id": 2, "name": 2})
        self.assertEqual(by_type["Window"]["count"], 2)


class TablesTest(unittest.TestCase):
    def test_stats_table_row(self):
        doc = dump_doc([element(0, None, "Window"), element(1, 0, "Button", "ok", "")],
                       app="Demo", technology="WPF")
        table = uia_dump.stats_table([doc])
        self.assertIn("| demo | Demo | WPF | 1.2.3.4 | 0.5 s | 2 | 1 | 100% (1/1) | 0% (0/1) "
                      "| 100% (1/1) | 0% (0/1) | 100% (1/1) |", table)

    def test_target_version_overrides_file_version_and_no_interactive_gives_dash(self):
        doc = dump_doc([element(0, None, "Window")], version="2.57")
        self.assertIn("| 2.57 | 0.5 s | 1 | 0 | – |", uia_dump.stats_table([doc]))

    def test_by_type_table_sorted_by_count(self):
        doc = dump_doc([element(0, None, "Window"), element(1, 0, "Text", "", "a"),
                        element(2, 0, "Text"), element(3, 0, "Edit", "user")])
        rows = [line for line in uia_dump.by_type_table(doc).splitlines() if line.startswith("| ")]
        self.assertEqual([row.split(" | ")[0] for row in rows[1:]], ["| Text", "| Edit", "| Window"])
        self.assertIn("| Edit | yes | 1 | 100% (1/1) | 0% (0/1) |", rows)


def dump_args(*argv: str) -> argparse.Namespace:
    defaults = {"id": None, "process": None, "title_re": None, "app": None, "technology": None,
                "state": None, "targets": None, "only": []}
    parsed = argparse.ArgumentParser()
    parsed.add_argument("--only", action="append", default=[])
    parsed.add_argument("--id")
    parsed.add_argument("--process")
    return argparse.Namespace(**{**defaults, **vars(parsed.parse_args(argv))})


class SelectTargetsTest(unittest.TestCase):
    def test_committed_target_list_is_complete(self):
        targets = uia_dump.select_targets(dump_args())
        self.assertGreaterEqual(len(targets), 3)
        self.assertEqual(len({t["id"] for t in targets}), len(targets))
        for t in targets:
            self.assertTrue(t.get("process") or t.get("title_re"), t["id"])
            self.assertTrue(t.get("app") and t.get("technology") and t.get("state"), t["id"])
        self.assertGreaterEqual(len({t["technology"] for t in targets}), 3)

    def test_only_filters_and_rejects_unknown_ids(self):
        self.assertEqual([t["id"] for t in uia_dump.select_targets(dump_args("--only", "keepassxc"))],
                         ["keepassxc"])
        with self.assertRaises(SystemExit):
            uia_dump.select_targets(dump_args("--only", "nope"))

    def test_one_off_target_needs_process_or_title(self):
        with self.assertRaises(SystemExit):
            uia_dump.select_targets(dump_args("--id", "calc"))
        [target] = uia_dump.select_targets(dump_args("--id", "calc", "--process", "Calc.exe"))
        self.assertEqual((target["id"], target["app"], target["process"]),
                         ("calc", "calc", "Calc.exe"))


class MainTest(unittest.TestCase):
    def test_stats_reads_a_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            uia_dump.write_dump(dump_doc([element(0, None, "Window")]), Path(tmp) / "demo.json")
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(uia_dump.main(["stats", "--by-type", tmp]), 0)
        self.assertIn("| demo |", out.getvalue())
        self.assertIn("### demo:", out.getvalue())

    def test_dump_refuses_without_windows(self):
        with mock.patch.object(sys, "platform", "darwin"), self.assertRaises(SystemExit) as cm:
            uia_dump.main(["dump"])
        self.assertIn("Windows", str(cm.exception.code))


if __name__ == "__main__":
    unittest.main()
