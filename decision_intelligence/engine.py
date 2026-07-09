"""Decision Intelligence Engine — independent from visualization rendering."""

from __future__ import annotations

from decision_intelligence.interface import DecisionIntelligenceInterface
from decision_intelligence.models import DecisionObject, DecisionSource
from decision_intelligence.providers.base import DecisionProvider
from decision_intelligence.providers.rule_based import RuleBasedDecisionProvider
from decision_intelligence.traceability import DecisionTraceStore, build_traceability
from decision_intelligence.validators import validate_decision


class DecisionIntelligenceEngine:
    """Orchestrates providers, validation, and standardized decision output."""

    def __init__(
        self,
        provider: DecisionProvider | None = None,
        *,
        trace_store: DecisionTraceStore | None = None,
    ) -> None:
        self._provider = provider or RuleBasedDecisionProvider()
        self._history: list[DecisionObject] = []
        self.trace_store = trace_store or DecisionTraceStore()

    @property
    def provider_id(self) -> str:
        return getattr(self._provider, "provider_id", "unknown")

    def set_provider(self, provider: DecisionProvider) -> None:
        """Swap provider for LLM, ML, predictive, or agent backends."""
        self._provider = provider

    def evaluate(self, source: DecisionSource) -> DecisionObject:
        raw = self._provider.generate(source)
        decision = validate_decision(raw, source)
        trace = build_traceability(decision, source, provider_id=self.provider_id)
        decision.traceability = trace
        self.trace_store.record(trace)
        self._history.append(decision)
        return decision

    def evaluate_batch(self, sources: list[DecisionSource]) -> list[DecisionObject]:
        return [self.evaluate(source) for source in sources]

    def executive_summary(self, decisions: list[DecisionObject] | None = None) -> str:
        decisions = decisions if decisions is not None else self._history
        validated = [decision for decision in decisions if decision.validated]
        pool = validated or decisions
        if not pool:
            return "No decision intelligence is available for the current dashboard context."

        critical = [d for d in pool if d.priority == "Critical"]
        high = [d for d in pool if d.priority == "High"]
        lead = critical or high or pool[:1]
        summaries = [decision.executive_summary for decision in lead[:3]]
        validated_note = "" if validated else " (Note: some recommendations failed validation and require review.)"
        return " ".join(summaries) + validated_note

    def history(self, *, limit: int = 50) -> list[DecisionObject]:
        return self._history[-limit:]

    def clear_history(self) -> None:
        self._history.clear()

    def trace_history_for_widget(self, widget_id: str, *, limit: int = 20):
        return self.trace_store.history_for_widget(widget_id, limit=limit)

    def trace_history_for_dataset(self, dataset_id: str, *, limit: int = 20):
        return self.trace_store.history_for_dataset(dataset_id, limit=limit)

    def compare_traces(self, left_id: str, right_id: str) -> dict:
        return self.trace_store.compare(left_id, right_id)


_default_engine: DecisionIntelligenceEngine | None = None


def get_default_engine() -> DecisionIntelligenceEngine:
    global _default_engine
    if _default_engine is None:
        _default_engine = DecisionIntelligenceEngine()
    return _default_engine


# Type-check protocol conformance
def _assert_interface(engine: DecisionIntelligenceEngine) -> DecisionIntelligenceInterface:
    return engine
