from __future__ import annotations

import unittest

import pandas as pd

from decision_intelligence import (
    CONFIDENCE_VERSION,
    ENGINE_VERSION,
    DecisionIntelligenceEngine,
    DecisionTraceStore,
    build_source_from_kpi,
    build_source_from_widget,
    evaluate_widget,
    serialize_decision,
)
from decision_intelligence.traceability import build_traceability, evidence_references
from visualization_engine import VISUALIZATION_ENGINE_VERSION
from widgets.widget_factory import WidgetFactory


class DecisionTraceabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.df = pd.DataFrame(
            {
                "date": pd.date_range("2026-01-01", periods=6, freq="MS"),
                "revenue": [100, 120, 140, 130, 150, 160],
                "product": ["A", "B", "A", "B", "A", "B"],
            }
        )
        self.summary = {"rows": 6, "columns": 3, "missing_pct": 0.0, "completeness_pct": 100.0}
        self.trace_store = DecisionTraceStore()
        self.engine = DecisionIntelligenceEngine(trace_store=self.trace_store)

    def test_traceability_attached_on_evaluate(self) -> None:
        source = build_source_from_kpi(
            widget_id="kpi-revenue",
            title="Revenue",
            metric_name="Revenue",
            metric_value="760",
            dataframe=self.df,
            summary=self.summary,
        )
        source.dataset_id = "ds-revenue"
        decision = self.engine.evaluate(source)

        self.assertIsNotNone(decision.traceability)
        trace = decision.traceability
        assert trace is not None
        self.assertEqual(trace.decision_id, decision.decision_id)
        self.assertEqual(trace.widget_id, "kpi-revenue")
        self.assertEqual(trace.dataset_id, "ds-revenue")
        self.assertEqual(trace.engine_version, ENGINE_VERSION)
        self.assertEqual(trace.visualization_version, VISUALIZATION_ENGINE_VERSION)
        self.assertEqual(trace.confidence_version, CONFIDENCE_VERSION)
        self.assertTrue(trace.evidence_references)
        self.assertTrue(trace.reasoning_path)

    def test_traceability_serialized_in_contract(self) -> None:
        source = build_source_from_kpi(
            widget_id="kpi-1",
            title="Revenue",
            metric_name="Revenue",
            metric_value="760",
            dataframe=self.df,
            summary=self.summary,
        )
        decision = self.engine.evaluate(source)
        payload = serialize_decision(decision)

        self.assertIn("traceability", payload)
        trace = payload["traceability"]
        for field in (
            "decision_id",
            "widget_id",
            "dataset_id",
            "generated_at",
            "engine_version",
            "visualization_version",
            "confidence_version",
            "evidence_references",
            "reasoning_path",
        ):
            self.assertIn(field, trace)

    def test_trace_store_indexes_by_widget_and_dataset(self) -> None:
        source = build_source_from_kpi(
            widget_id="kpi-idx",
            title="Revenue",
            metric_name="Revenue",
            metric_value="760",
            dataframe=self.df,
            summary=self.summary,
        )
        source.dataset_id = "ds-idx"
        decision = self.engine.evaluate(source)
        assert decision.traceability is not None

        self.assertEqual(self.trace_store.count(), 1)
        self.assertEqual(self.trace_store.get(decision.decision_id), decision.traceability)
        self.assertEqual(len(self.trace_store.history_for_widget("kpi-idx")), 1)
        self.assertEqual(len(self.trace_store.history_for_dataset("ds-idx")), 1)

    def test_compare_traces_detects_evidence_drift(self) -> None:
        source = build_source_from_kpi(
            widget_id="kpi-drift",
            title="Revenue",
            metric_name="Revenue",
            metric_value="760",
            dataframe=self.df,
            summary=self.summary,
        )
        source.dataset_id = "ds-drift"
        first = self.engine.evaluate(source)
        second = self.engine.evaluate(source)
        assert first.traceability is not None and second.traceability is not None

        result = self.trace_store.compare(first.decision_id, second.decision_id)
        self.assertTrue(result["ok"])
        self.assertEqual(result["widget_id"], "kpi-drift")
        self.assertEqual(result["dataset_id"], "ds-drift")

    def test_evidence_references_exclude_raw_values(self) -> None:
        source = build_source_from_kpi(
            widget_id="kpi-safe",
            title="Revenue",
            metric_name="Revenue",
            metric_value="760",
            dataframe=self.df,
            summary=self.summary,
        )
        decision = self.engine.evaluate(source)
        assert decision.traceability is not None

        for ref in decision.traceability.evidence_references:
            self.assertNotIn("760", ref)
            self.assertIn(":", ref)

        refs = evidence_references(decision.evidence)
        self.assertEqual(refs, decision.traceability.evidence_references)

    def test_widget_source_includes_dataset_id(self) -> None:
        widget = WidgetFactory.create("kpi", title="Revenue", dataset_id="ds-widget-1")
        artifacts = {
            "_df_cache": self.df,
            "summary": self.summary,
            "kpis": {"Revenue": {"value": "760", "note": "revenue"}},
            "column_types": {"categorical": ["product"], "numeric": ["revenue"]},
        }
        decision = evaluate_widget(widget, artifacts=artifacts, dataframe=self.df, engine=self.engine)

        assert decision.traceability is not None
        self.assertEqual(decision.traceability.widget_id, widget.widget_id)
        self.assertEqual(decision.traceability.dataset_id, "ds-widget-1")

    def test_reasoning_path_documents_audit_steps(self) -> None:
        source = build_source_from_kpi(
            widget_id="kpi-audit",
            title="Revenue",
            metric_name="Revenue",
            metric_value="760",
            dataframe=self.df,
            summary=self.summary,
        )
        decision = self.engine.evaluate(source)
        trace = build_traceability(decision, source, provider_id="rule_based_v1")

        steps = [step["step"] for step in trace.reasoning_path]
        self.assertIn("source_ingest", steps)
        self.assertIn("provider_generate", steps)
        self.assertIn("quality_validate", steps)
        self.assertIn("priority_assign", steps)


if __name__ == "__main__":
    unittest.main()
