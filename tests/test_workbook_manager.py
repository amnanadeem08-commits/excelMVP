from __future__ import annotations

import unittest

import pandas as pd

from workbook.manager import WorkbookManager


class WorkbookManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.sales = pd.DataFrame(
            {
                "product": ["A", "B", "C"],
                "revenue": [100, 200, 150],
            }
        )
        self.finance = pd.DataFrame(
            {
                "month": ["Jan", "Feb"],
                "expense": [50, 60],
            }
        )
        self.workbook = WorkbookManager(
            {"Sales": self.sales, "Finance": self.finance},
            active_sheet="Sales",
        )

    def test_from_upload_wraps_single_dataframe(self) -> None:
        manager = WorkbookManager.from_upload(self.sales, source_name="sales.csv")
        self.assertEqual(manager.sheet_names, ["Sheet1"])
        self.assertEqual(len(manager.get_active_dataframe()), 3)

    def test_from_upload_preserves_multi_sheet_order(self) -> None:
        parsed = {"Finance": self.finance, "Sales": self.sales}
        manager = WorkbookManager.from_upload(parsed, source_name="book.xlsx")
        self.assertEqual(set(manager.sheet_names), {"Finance", "Sales"})
        self.assertEqual(len(manager.get_active_dataframe()), 2)

    def test_add_sheet_creates_unique_name_and_activates(self) -> None:
        new_name = self.workbook.add_sheet()
        self.assertIn(new_name, self.workbook.sheet_names)
        self.assertEqual(self.workbook.active_sheet, new_name)
        self.assertTrue(self.workbook.dirty)
        self.assertEqual(list(self.workbook.get_active_dataframe().columns), ["product", "revenue"])

    def test_rename_sheet_updates_active_reference(self) -> None:
        ok, message = self.workbook.rename_sheet("Sales", "Revenue Data")
        self.assertTrue(ok)
        self.assertIn("Renamed", message)
        self.assertEqual(self.workbook.active_sheet, "Revenue Data")
        self.assertNotIn("Sales", self.workbook.sheet_names)

    def test_rename_sheet_rejects_duplicate_names(self) -> None:
        ok, message = self.workbook.rename_sheet("Sales", "Finance")
        self.assertFalse(ok)
        self.assertIn("already exists", message)

    def test_delete_sheet_blocks_last_sheet(self) -> None:
        single = WorkbookManager({"Only": self.sales})
        ok, message = single.delete_sheet("Only")
        self.assertFalse(ok)
        self.assertIn("last sheet", message.lower())

    def test_delete_sheet_switches_active_sheet(self) -> None:
        ok, _ = self.workbook.delete_sheet("Sales")
        self.assertTrue(ok)
        self.assertEqual(self.workbook.active_sheet, "Finance")
        self.assertNotIn("Sales", self.workbook.sheet_names)

    def test_duplicate_sheet_copies_data_and_inserts_after_source(self) -> None:
        ok, new_name = self.workbook.duplicate_sheet("Sales")
        self.assertTrue(ok)
        self.assertIn(new_name, self.workbook.sheet_names)
        self.assertEqual(self.workbook.active_sheet, new_name)
        duplicated = self.workbook.sheets[new_name]
        pd.testing.assert_frame_equal(duplicated, self.sales)
        self.assertEqual(self.workbook.sheet_names.index(new_name), 1)

    def test_state_round_trip_preserves_workbook(self) -> None:
        self.workbook.add_sheet("Targets")
        state = self.workbook.to_state_dict()
        restored = WorkbookManager.from_state_dict(state)
        self.assertEqual(restored.sheet_names, self.workbook.sheet_names)
        self.assertEqual(restored.active_sheet, self.workbook.active_sheet)
        self.assertTrue(restored.dirty)
        pd.testing.assert_frame_equal(
            restored.get_active_dataframe(),
            self.workbook.get_active_dataframe(),
        )

    def test_select_active_via_loader_matches_data_loader_contract(self) -> None:
        frame = self.workbook.select_active_via_loader()
        pd.testing.assert_frame_equal(frame, self.sales)


if __name__ == "__main__":
    unittest.main()
