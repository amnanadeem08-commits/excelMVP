from __future__ import annotations

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
        app = AppTest.from_file("app.py")
        app.run(timeout=20)
        app.file_uploader[0].upload(sample.name, sample.read_bytes(), "text/csv").run(timeout=35)
        self.assertFalse(app.exception)

        mode_radio = next(radio for radio in app.radio if radio.label == "Choose dashboard mode")
        self.assertEqual(list(mode_radio.options), MODE_LABELS)
        self.assertEqual(mode_radio.value, "Executive Dashboard")


if __name__ == "__main__":
    unittest.main()
