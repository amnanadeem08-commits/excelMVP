from __future__ import annotations

import time
import unittest

import pandas as pd

from canvas.engine import CanvasEngine
from canvas.layout import LayoutManager


class CanvasPerformanceTests(unittest.TestCase):
    def test_canvas_initialization_is_fast_for_large_widget_plan(self) -> None:
        artifacts = {
            "mode": type(
                "Mode",
                (),
                {
                    "key": "analytical",
                    "label": "Analytical Dashboard",
                    "description": "Perf test",
                    "chart_limit": None,
                },
            )(),
            "kpis": {f"KPI {idx}": {"value": str(idx), "note": "n"} for idx in range(12)},
            "charts": [object() for _ in range(16)],
            "pivots": [type("Pivot", (), {"title": f"P{idx}", "data": pd.DataFrame({"a": [1]})})() for idx in range(8)],
            "insights": [f"Insight {idx}" for idx in range(10)],
        }
        manager = LayoutManager()
        started = time.perf_counter()
        layout = manager.auto_layout_from_artifacts(
            workbook_id="perf.xlsx",
            sheet_id="Data",
            dashboard_id="analytical",
            theme="Corporate Blue",
            artifacts=artifacts,
        )
        elapsed_ms = (time.perf_counter() - started) * 1000
        engine = CanvasEngine(layout)
        engine.initialize(
            workbook_id="perf.xlsx",
            sheet_id="Data",
            dashboard_id="analytical",
            theme="Corporate Blue",
            artifacts=artifacts,
        )
        self.assertGreater(len(layout.widgets), 4)
        self.assertLess(elapsed_ms, 250.0)
        self.assertLess(engine.metrics.init_ms, 250.0)
        self.assertFalse(engine.validate())


if __name__ == "__main__":
    unittest.main()
