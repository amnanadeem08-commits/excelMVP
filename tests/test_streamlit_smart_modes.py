from __future__ import annotations

import os
from pathlib import Path
import unittest

from streamlit.testing.v1 import AppTest


MODE_LABELS = [
    "Executive Dashboard",
    "Analytical Dashboard",
    "Financial Dashboard",
    "Operational Dashboard",
]


class StreamlitSmartModeSmokeTests(unittest.TestCase):
    def test_sales_sample_renders_mode_selector(self):
        sample = Path("samples/smart_modes_sales.csv")
        os.environ["EXCELMVP_SKIP_HEAVY_EXPORTS"] = "1"
        try:
            app = AppTest.from_file("app.py")
            app.run(timeout=20)

            uploader = None
            if hasattr(app, "file_uploader") and app.file_uploader:
                uploader = app.file_uploader[0]
            elif hasattr(app, "get"):
                widgets = app.get("file_uploader")
                if widgets:
                    uploader = widgets[0]

            if uploader is None or not hasattr(uploader, "upload"):
                self.skipTest("Streamlit AppTest uploader interaction API is unavailable in this runtime")

            uploader.upload(sample.name, sample.read_bytes(), "text/csv").run(timeout=120)
            self.assertFalse(app.exception)

            add_sheet = next((btn for btn in app.button if btn.label == "Add Sheet"), None)
            self.assertIsNotNone(add_sheet)

            mode_radio = next(radio for radio in app.radio if radio.label == "Choose dashboard mode")
            self.assertEqual(list(mode_radio.options), MODE_LABELS)
            self.assertEqual(mode_radio.value, "Executive Dashboard")
        finally:
            os.environ.pop("EXCELMVP_SKIP_HEAVY_EXPORTS", None)


if __name__ == "__main__":
    unittest.main()
