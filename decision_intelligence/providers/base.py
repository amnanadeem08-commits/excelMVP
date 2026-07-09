"""Decision provider protocol."""

from __future__ import annotations

from typing import Protocol

from decision_intelligence.models import DecisionObject, DecisionSource


class DecisionProvider(Protocol):
    """Pluggable provider: rule-based, LLM, ML, predictive, prescriptive, agent."""

    provider_id: str

    def generate(self, source: DecisionSource) -> DecisionObject:
        """Produce a raw decision object from a source context."""
