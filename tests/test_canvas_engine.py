from __future__ import annotations

import unittest

from canvas.grid import GridConfig, WidgetPlacement, detect_overlaps, is_grid_empty, resolve_columns, validate_placements
from canvas.layout import LayoutManager
from canvas.serialization import deserialize_layout, serialize_layout


class CanvasGridTests(unittest.TestCase):
    def test_resolve_columns_uses_ratio_breakpoints(self) -> None:
        grid = GridConfig(columns=12, min_column_width_px=72)
        self.assertEqual(resolve_columns(1400, grid), 12)
        self.assertEqual(resolve_columns(700, grid), 8)
        self.assertEqual(resolve_columns(400, grid), 4)

    def test_overlap_detection_finds_collision(self) -> None:
        left = WidgetPlacement("a", "chart", col=0, row=0, col_span=6, row_span=2)
        right = WidgetPlacement("b", "chart", col=4, row=1, col_span=4, row_span=2)
        self.assertEqual(detect_overlaps([left, right]), [("a", "b")])

    def test_validate_rejects_out_of_bounds_widget(self) -> None:
        grid = GridConfig(columns=12)
        widget = WidgetPlacement("wide", "chart", col=10, row=0, col_span=4, row_span=1)
        issues = validate_placements([widget], grid)
        self.assertTrue(any("exceeds grid width" in issue for issue in issues))

    def test_empty_grid_detection(self) -> None:
        hidden = WidgetPlacement("hidden", "chart", col=0, row=0, visible=False)
        self.assertTrue(is_grid_empty([hidden]))


class CanvasLayoutManagerTests(unittest.TestCase):
    def test_auto_layout_is_non_overlapping(self) -> None:
        artifacts = {
            "mode": type("Mode", (), {"key": "executive", "label": "Executive Dashboard", "description": "Test", "chart_limit": 2})(),
            "kpis": {"Revenue": {"value": "100", "note": "x"}},
            "charts": [],
            "pivots": [],
            "insights": ["One", "Two"],
        }
        manager = LayoutManager()
        layout = manager.auto_layout_from_artifacts(
            workbook_id="book.xlsx",
            sheet_id="Sales",
            dashboard_id="executive",
            theme="Corporate Blue",
            artifacts=artifacts,
        )
        self.assertFalse(manager.has_overlaps())
        self.assertGreaterEqual(len(layout.widgets), 3)

    def test_serialization_round_trip(self) -> None:
        widget = WidgetPlacement("chart-1", "chart_grid", col=0, row=1, col_span=12, row_span=2)
        payload = serialize_layout(
            workbook_id="book.xlsx",
            sheet_id="Sales",
            dashboard_id="analytical",
            theme="Corporate Blue",
            grid=GridConfig(),
            widgets=[widget],
        )
        parsed = deserialize_layout(payload)
        self.assertEqual(parsed["workbook_id"], "book.xlsx")
        self.assertEqual(parsed["widgets"][0].widget_id, "chart-1")
        self.assertEqual(parsed["version"], "2.0.0")


if __name__ == "__main__":
    unittest.main()
