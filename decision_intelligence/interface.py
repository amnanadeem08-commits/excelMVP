"""Decision Intelligence public interface."""

from __future__ import annotations

from typing import Protocol

from decision_intelligence.models import DecisionObject, DecisionSource


class DecisionIntelligenceInterface(Protocol):
    """Contract for all decision intelligence providers (rule-based, LLM, ML)."""

    def evaluate(self, source: DecisionSource) -> DecisionObject:
        """Evaluate a single source and return a standardized decision."""

    def evaluate_batch(self, sources: list[DecisionSource]) -> list[DecisionObject]:
        """Evaluate multiple sources."""

    def executive_summary(self, decisions: list[DecisionObject]) -> str:
        """Compose an executive narrative from validated decisions."""
