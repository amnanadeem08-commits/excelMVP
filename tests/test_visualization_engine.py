from __future__ import annotations

import unittest

import pandas as pd

from data_cleaning import detect_column_types
from dashboard import get_default_theme
from visualization_engine import VisualizationEngine


class VisualizationEngineTests(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame(
            {
                "date": pd.date_range("2026-01-01", periods=8, freq="MS"),
                "category": ["A", "B", "C", "A", "B", "C", "A", "B"],
                "revenue": [100, 120, 90, 140, 150, 130, 170, 160],
                "cost": [60, 70, 55, 82, 90, 79, 101, 95],
            }
        )
        self.column_types = detect_column_types(self.df)
        self.engine = VisualizationEngine(get_default_theme(), template_name="Executive Dashboard")

    def test_recommendations_cover_expected_core_types(self):
        recs = self.engine.recommend(self.df, self.column_types)
        chart_types = {rec.chart_type for rec in recs}
        self.assertIn("line", chart_types)
        self.assertIn("bar", chart_types)
        self.assertIn("histogram", chart_types)
        self.assertIn("scatter", chart_types)

    def test_auto_chart_generation_includes_advanced_types(self):
        charts = self.engine.build_auto_charts(self.df, self.column_types, max_charts=30)
        chart_types = {chart.chart_type for chart in charts}
        self.assertIn("line", chart_types)
        self.assertIn("area", chart_types)
        self.assertIn("donut", chart_types)
        self.assertIn("treemap", chart_types)
        self.assertIn("waterfall", chart_types)
        self.assertIn("funnel", chart_types)
        self.assertIn("gauge", chart_types)
        self.assertIn("table_view", chart_types)


if __name__ == "__main__":
    unittest.main()
