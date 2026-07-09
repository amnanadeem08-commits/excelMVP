"""AI adapter — delegates decision intelligence through the DI interface."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from decision_intelligence.engine import DecisionIntelligenceEngine, get_default_engine
from decision_intelligence.integration import evaluate_widget
from decision_intelligence.models import DecisionObject
from widgets.base import BaseWidget


@dataclass
class AIInsight:
    title: str
    summary: str
    confidence: float
    reason: str
    recommendations: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AIVisualizationSuggestion:
    chart_type: str
    confidence: float
    reason: str
    alternatives: list[str] = field(default_factory=list)


def decision_to_ai_insight(decision: DecisionObject) -> AIInsight:
    """Map standardized decision contract to legacy AIInsight shape."""
    return AIInsight(
        title=decision.source_widget or "Widget",
        summary=decision.insight,
        confidence=decision.confidence,
        reason=decision.reason,
        recommendations=list(decision.recommended_actions),
        metadata={
            "decision_id": decision.decision_id,
            "validated": decision.validated,
            "validation_flags": decision.validation_flags,
            "priority": decision.priority,
            "executive_summary": decision.executive_summary,
            "business_impact": decision.business_impact,
            "opportunity": decision.opportunity,
            "risk_assessment": decision.risk_assessment,
        },
    )


class WidgetAIAdapter:
    """Expose AI-ready capabilities via Decision Intelligence (no embedded business logic)."""

    def __init__(self, engine: DecisionIntelligenceEngine | None = None) -> None:
        self._engine = engine or get_default_engine()
        self._context: dict[str, Any] = {}

    def set_context(self, *, artifacts: dict[str, Any] | None = None) -> None:
        self._context = {"artifacts": artifacts or {}}

    def evaluate_decision(self, widget: BaseWidget) -> DecisionObject:
        return evaluate_widget(
            widget,
            artifacts=self._context.get("artifacts"),
            dataframe=self._context.get("artifacts", {}).get("_df_cache"),
            engine=self._engine,
        )

    def explain_widget(self, widget: BaseWidget) -> AIInsight:
        decision = self.evaluate_decision(widget)
        return decision_to_ai_insight(decision)

    def explain_kpi(self, widget: BaseWidget) -> AIInsight:
        return self.explain_widget(widget)

    def suggest_visualization(self, widget: BaseWidget) -> AIVisualizationSuggestion:
        decision = self.evaluate_decision(widget)
        chart_type = "bar" if widget.widget_type == "kpi" else "line"
        return AIVisualizationSuggestion(
            chart_type=chart_type,
            confidence=decision.confidence,
            reason=decision.reason,
            alternatives=["bar", "line", "donut", "table_view"],
        )

    def detect_problems(self, widget: BaseWidget) -> list[str]:
        decision = self.evaluate_decision(widget)
        problems = list(decision.validation_flags)
        problems.extend(widget.validate())
        if not widget.data_binding.dataset_id:
            problems.append("Missing dataset binding.")
        return problems

    def generate_insight(self, widget: BaseWidget) -> AIInsight:
        return self.explain_widget(widget)

    def business_recommendation(self, widget: BaseWidget) -> AIInsight:
        decision = self.evaluate_decision(widget)
        insight = decision_to_ai_insight(decision)
        if decision.opportunity:
            insight.recommendations.append(decision.opportunity)
        return insight

    def confidence_score(self, widget: BaseWidget) -> float:
        return self.evaluate_decision(widget).confidence

    def get_decision(self, widget: BaseWidget) -> DecisionObject:
        return self.evaluate_decision(widget)
