from __future__ import annotations

import unittest

import pandas as pd

from dashboard_modes import DASHBOARD_MODES, prepare_mode_artifacts
from forecasting.simple_forecast import simple_date_forecast
from insights.click_insights import build_click_insight


class SmartDashboardModeTests(unittest.TestCase):
    def test_mode_definitions_include_required_modes(self):
        self.assertEqual(
            set(DASHBOARD_MODES),
            {"executive", "analytical", "financial", "operational"},
        )

    def test_simple_forecast_uses_monthly_trend(self):
        df = pd.DataFrame(
            {
                "date": pd.date_range("2026-01-01", periods=4, freq="MS"),
                "revenue": [100, 120, 140, 160],
            }
        )
        result = simple_date_forecast(df, "date", "revenue", periods=2)
        self.assertTrue(result.ok)
        self.assertEqual(len(result.forecast), 2)
        self.assertGreater(result.forecast["forecast"].iloc[-1], result.history["actual"].iloc[-1])

    def test_simple_forecast_fallback_for_sparse_data(self):
        df = pd.DataFrame({"date": ["2026-01-01", "2026-02-01"], "revenue": [100, 120]})
        result = simple_date_forecast(df, "date", "revenue")
        self.assertFalse(result.ok)
        self.assertIn("at least three", result.message)

    def test_click_insight_does_not_hallucinate_missing_column(self):
        df = pd.DataFrame({"revenue": [100, 200]})
        insight = build_click_insight(df, "Missing KPI", column="profit")
        self.assertIn("not available", insight["data_says"])

    def test_financial_artifacts_find_finance_metrics(self):
        df = pd.DataFrame(
            {
                "month": pd.date_range("2026-01-01", periods=4, freq="MS"),
                "revenue": [1000, 1200, 1400, 1600],
                "expense": [700, 760, 820, 900],
                "profit": [300, 440, 580, 700],
            }
        )
        artifacts = prepare_mode_artifacts(df, "financial")
        self.assertIn("Revenue", artifacts["kpis"])
        self.assertIn("Profit", artifacts["kpis"])
        self.assertTrue(any("Forecast" in chart.title for chart in artifacts["charts"]))

    def test_operational_artifacts_find_activity_metrics(self):
        df = pd.DataFrame(
            {
                "date": pd.date_range("2026-01-01", periods=4, freq="MS"),
                "orders": [10, 12, 14, 16],
                "stock": [5, 4, 12, 20],
                "status": ["Shipped", "Delayed", "Shipped", "Backlog"],
                "customer": ["A", "B", "A", "C"],
            }
        )
        artifacts = prepare_mode_artifacts(df, "operational")
        self.assertIn("Volume", artifacts["kpis"])
        self.assertTrue(artifacts["insights"])


if __name__ == "__main__":
    unittest.main()
