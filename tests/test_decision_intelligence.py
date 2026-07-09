from __future__ import annotations

import unittest

import pandas as pd

from decision_intelligence import (
    DecisionIntelligenceEngine,
    DecisionObject,
    Priority,
    RuleBasedDecisionProvider,
    build_source_from_chart,
    build_source_from_kpi,
    build_source_from_widget,
    deserialize_decision,
    evaluate_widget,
    serialize_decision,
    validate_decision,
)
from widgets.widget_factory import WidgetFactory


class DecisionIntelligenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.df = pd.DataFrame(
            {
                "date": pd.date_range("2026-01-01", periods=6, freq="MS"),
                "revenue": [100, 120, 140, 130, 150, 160],
                "product": ["A", "B", "A", "B", "A", "B"],
            }
        )
        self.summary = {"rows": 6, "columns": 3, "missing_pct": 0.0, "completeness_pct": 100.0}
        self.engine = DecisionIntelligenceEngine()

    def test_decision_contract_contains_required_fields(self) -> None:
        source = build_source_from_kpi(
            widget_id="kpi-revenue",
            title="Revenue",
            metric_name="Revenue",
            metric_value="760",
            dataframe=self.df,
            summary=self.summary,
        )
        decision = self.engine.evaluate(source)
        payload = serialize_decision(decision)
        for field in (
            "decision_id",
            "source_widget",
            "insight",
            "reason",
            "business_impact",
            "recommended_actions",
            "priority",
            "confidence",
            "evidence",
            "risk_level",
            "opportunity",
            "executive_summary",
            "timestamp",
        ):
            self.assertIn(field, payload)

    def test_serialization_round_trip(self) -> None:
        source = build_source_from_chart(
            widget_id="chart-1",
            title="Revenue Trend",
            chart_type="line",
            reason="Time series trend",
            dataframe=self.df,
            summary=self.summary,
        )
        decision = self.engine.evaluate(source)
        restored = deserialize_decision(serialize_decision(decision))
        self.assertEqual(restored.decision_id, decision.decision_id)
        self.assertEqual(restored.insight, decision.insight)

    def test_validation_flags_low_quality_data(self) -> None:
        sparse = pd.DataFrame({"revenue": [1]})
        source = build_source_from_kpi(
            widget_id="kpi-sparse",
            title="Sparse KPI",
            metric_name="Revenue",
            metric_value="1",
            dataframe=sparse,
            summary={"rows": 1, "columns": 1, "missing_pct": 0.0, "completeness_pct": 100.0},
        )
        decision = self.engine.evaluate(source)
        self.assertFalse(decision.validated)
        self.assertTrue(decision.validation_flags)

    def test_widget_integration_produces_decision(self) -> None:
        widget = WidgetFactory.create("kpi", title="Revenue", dataset_id="ds-1")
        artifacts = {
            "_df_cache": self.df,
            "summary": self.summary,
            "kpis": {"Revenue": {"value": "760", "note": "revenue"}},
            "column_types": {"categorical": ["product"], "numeric": ["revenue"]},
        }
        decision = evaluate_widget(widget, artifacts=artifacts, dataframe=self.df, engine=self.engine)
        self.assertEqual(decision.source_widget, widget.widget_id)
        self.assertGreater(len(decision.recommended_actions), 0)

    def test_executive_summary_generated(self) -> None:
        sources = [
            build_source_from_kpi(
                widget_id="k1",
                title="Revenue",
                metric_name="Revenue",
                metric_value="760",
                dataframe=self.df,
                summary=self.summary,
            ),
            build_source_from_chart(
                widget_id="c1",
                title="Trend",
                chart_type="line",
                reason="Trend",
                dataframe=self.df,
                summary=self.summary,
            ),
        ]
        decisions = self.engine.evaluate_batch(sources)
        summary = self.engine.executive_summary(decisions)
        self.assertGreater(len(summary), 20)

    def test_provider_swappable_for_future_llm(self) -> None:
        engine = DecisionIntelligenceEngine(RuleBasedDecisionProvider())
        self.assertEqual(engine.provider_id, "rule_based_v1")

    def test_validate_decision_scores_dimensions(self) -> None:
        source = build_source_from_kpi(
            widget_id="kpi-1",
            title="Revenue",
            metric_name="Revenue",
            metric_value="760",
            dataframe=self.df,
            summary=self.summary,
        )
        raw = RuleBasedDecisionProvider().generate(source)
        decision = validate_decision(raw, source)
        scores = decision.quality_scores.to_dict()
        for key in (
            "business_relevance",
            "statistical_validity",
            "data_quality",
            "confidence",
            "explainability",
            "actionability",
        ):
            self.assertIn(key, scores)
            self.assertGreaterEqual(scores[key], 0.0)

    def test_priority_levels_are_standardized(self) -> None:
        source = build_source_from_kpi(
            widget_id="kpi-1",
            title="Revenue",
            metric_name="Revenue",
            metric_value="760",
            dataframe=self.df,
            summary=self.summary,
        )
        decision = self.engine.evaluate(source)
        self.assertIn(decision.priority, {item.value for item in Priority})


if __name__ == "__main__":
    unittest.main()
