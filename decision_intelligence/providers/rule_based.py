"""Rule-based decision provider (no external AI)."""

from __future__ import annotations

from decision_intelligence.models import (
    DecisionObject,
    DecisionSource,
    Priority,
    RiskLevel,
    SourceType,
    SupportingEvidence,
)


class RuleBasedDecisionProvider:
    """Offline decision intelligence using dataset signals and heuristics."""

    provider_id = "rule_based_v1"

    def generate(self, source: DecisionSource) -> DecisionObject:
        rows = int(source.dataset_summary.get("rows", 0))
        completeness = float(source.dataset_summary.get("completeness_pct", 0.0))
        if completeness <= 0:
            completeness = max(0.0, 100.0 - float(source.dataset_summary.get("missing_pct", 0.0)))

        insight = self._insight(source, rows)
        reason = self._reason(source, completeness)
        impact = self._business_impact(source)
        actions = self._actions(source)
        priority = self._priority(source, completeness)
        confidence = self._confidence(source, completeness, rows)
        evidence = self._evidence(source, rows, completeness)
        risk_level, risk_text = self._risk(source, completeness)
        opportunity = self._opportunity(source)
        executive = self._executive_summary(source, insight, impact, priority)

        return DecisionObject(
            source_widget=source.widget_id or source.source_id,
            source_type=source.source_type,
            insight=insight,
            reason=reason,
            business_impact=impact,
            recommended_actions=actions,
            priority=priority,
            confidence=confidence,
            evidence=evidence,
            risk_level=risk_level,
            risk_assessment=risk_text,
            opportunity=opportunity,
            executive_summary=executive,
            metadata={"provider": self.provider_id, "source_title": source.title},
        )

    def _insight(self, source: DecisionSource, rows: int) -> str:
        if source.source_type == SourceType.KPI.value:
            metric = next(iter(source.metrics), "metric")
            value = source.metrics.get(metric, "n/a")
            return f"{source.title}: {metric} is reporting {value} across {rows:,} filtered records."
        if source.source_type == SourceType.CHART.value:
            return f"{source.title} indicates a pattern worth monitoring in the current dataset slice."
        if source.source_type == SourceType.TREND.value:
            signal = source.trend_signal or "stable"
            return f"{source.title} shows a {signal} trend based on available time-series signals."
        return f"{source.title} summarizes key signals from the active dashboard section."

    def _reason(self, source: DecisionSource, completeness: float) -> str:
        parts = [f"Analysis uses {completeness:.1f}% data completeness"]
        if source.dimensions:
            parts.append(f"across dimensions {', '.join(source.dimensions[:3])}")
        if source.trend_signal:
            parts.append(f"with trend signal '{source.trend_signal}'")
        return ", ".join(parts) + "."

    def _business_impact(self, source: DecisionSource) -> str:
        if source.source_type == SourceType.KPI.value:
            return "KPI movement can affect forecasting, resource allocation, and executive reporting accuracy."
        if source.source_type == SourceType.CHART.value:
            return "Chart patterns may indicate revenue concentration, operational bottlenecks, or emerging risks."
        if source.source_type == SourceType.TREND.value:
            return "Trend shifts can influence planning cycles, inventory decisions, and budget forecasts."
        return "This section influences how stakeholders interpret performance and prioritize next steps."

    def _actions(self, source: DecisionSource) -> list[str]:
        actions = [
            f"Validate the data binding and filters behind '{source.title}'.",
            "Compare this signal with prior period or benchmark metrics.",
        ]
        if source.source_type == SourceType.KPI.value:
            actions.append("Confirm whether the KPI threshold or target has changed before acting.")
        if source.source_type == SourceType.TREND.value and source.trend_signal in {"decline", "negative"}:
            actions.append("Investigate root causes for the negative trend within two planning cycles.")
        if float(source.dataset_summary.get("missing_pct", 0.0)) > 15:
            actions.insert(0, "Improve source data completeness before making high-stakes decisions.")
        return actions[:4]

    def _priority(self, source: DecisionSource, completeness: float) -> str:
        if completeness < 50:
            return Priority.CRITICAL.value
        if source.trend_signal in {"decline", "negative", "spike"}:
            return Priority.HIGH.value
        if source.source_type == SourceType.KPI.value:
            return Priority.HIGH.value
        if source.source_type in {SourceType.CHART.value, SourceType.TREND.value}:
            return Priority.MEDIUM.value
        return Priority.LOW.value

    def _confidence(self, source: DecisionSource, completeness: float, rows: int) -> float:
        base = 0.55
        base += min(completeness / 200.0, 0.25)
        base += min(rows / 500.0, 0.15)
        if source.metrics:
            base += 0.05
        return round(min(base, 0.95), 2)

    def _evidence(self, source: DecisionSource, rows: int, completeness: float) -> list[SupportingEvidence]:
        evidence = [
            SupportingEvidence("Filtered rows", f"{rows:,}", "metric", "dataset_summary"),
            SupportingEvidence("Data completeness", f"{completeness:.1f}%", "metric", "dataset_summary"),
        ]
        for key, value in list(source.metrics.items())[:3]:
            evidence.append(SupportingEvidence(key, str(value), "metric", "source.metrics"))
        for dimension in source.dimensions[:2]:
            evidence.append(SupportingEvidence(dimension, "active dimension", "dimension", "source.dimensions"))
        return evidence

    def _risk(self, source: DecisionSource, completeness: float) -> tuple[str, str]:
        if completeness < 40:
            return RiskLevel.CRITICAL.value, "Low data quality increases the risk of incorrect business decisions."
        if source.trend_signal in {"decline", "negative"}:
            return RiskLevel.HIGH.value, "Negative trend may compound if corrective action is delayed."
        if int(source.dataset_summary.get("rows", 0)) < 10:
            return RiskLevel.HIGH.value, "Very small sample size may not represent operational reality."
        return RiskLevel.MEDIUM.value, "Standard monitoring risk; revisit if underlying data changes materially."

    def _opportunity(self, source: DecisionSource) -> str:
        if source.trend_signal in {"growth", "positive", "increase"}:
            return "Positive momentum may support expansion, upsell, or resource reinvestment."
        if source.source_type == SourceType.CHART.value:
            return "Visual concentration patterns may reveal optimization or cross-sell opportunities."
        return "Stable performance creates room to test targeted improvements with controlled experiments."

    def _executive_summary(self, source: DecisionSource, insight: str, impact: str, priority: str) -> str:
        return (
            f"{priority} priority: {insight} {impact} "
            f"Leadership should review '{source.title}' in the next decision cycle."
        )
