"""Visualization engine decision intelligence hook tests."""

from __future__ import annotations

import unittest

import pandas as pd

from visualization_engine import ChartRecommendation, VisualizationEngine


class VisualizationDecisionHookTests(unittest.TestCase):
    def test_request_decision_delegates_to_decision_intelligence(self) -> None:
        df = pd.DataFrame(
            {
                "month": pd.date_range("2026-01-01", periods=4, freq="MS"),
                "revenue": [100, 120, 140, 160],
                "product": ["A", "B", "A", "B"],
            }
        )
        engine = VisualizationEngine({"accent": "#2563eb", "palette": ["#2563eb"]})
        recommendation = ChartRecommendation("line", "Time vs numeric trend is best shown as a line chart.", 98)
        decision = engine.request_decision_for_recommendation(df, recommendation, widget_id="chart-line")
        self.assertEqual(decision["source_widget"], "chart-line")
        self.assertIn("insight", decision)
        self.assertIn("recommended_actions", decision)
        self.assertIn("validated", decision)


if __name__ == "__main__":
    unittest.main()
