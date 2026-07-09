from __future__ import annotations

import unittest

import pandas as pd

from workbook import WorkbookManager, load_or_create, persist


class _UploadStub:
    def __init__(self, name: str, size: int) -> None:
        self.name = name
        self.size = size


class WorkbookSessionTests(unittest.TestCase):
    def test_load_or_create_initializes_single_sheet_csv(self) -> None:
        df = pd.DataFrame({"revenue": [100, 200]})
        upload = _UploadStub("sales.csv", 128)
        manager = load_or_create(upload, df)
        self.assertEqual(manager.sheet_names, ["Sheet1"])
        self.assertEqual(len(manager.get_active_dataframe()), 2)

    def test_persist_round_trip_keeps_sheet_mutations(self) -> None:
        df = pd.DataFrame({"revenue": [100, 200]})
        upload = _UploadStub("sales.csv", 128)
        manager = load_or_create(upload, df)
        manager.add_sheet("Targets")
        persist(manager)
        restored = load_or_create(upload, df)
        self.assertIn("Targets", restored.sheet_names)
        self.assertEqual(restored.active_sheet, "Targets")

    def test_new_upload_resets_workbook_state(self) -> None:
        first = _UploadStub("sales.csv", 128)
        second = _UploadStub("finance.csv", 256)
        sales = pd.DataFrame({"revenue": [100]})
        finance = pd.DataFrame({"expense": [50]})

        manager = load_or_create(first, sales)
        manager.add_sheet("Extra")
        persist(manager)

        reset = load_or_create(second, finance)
        self.assertEqual(reset.source_name, "finance.csv")
        self.assertEqual(reset.sheet_names, ["Sheet1"])
        self.assertNotIn("Extra", reset.sheet_names)


if __name__ == "__main__":
    unittest.main()
