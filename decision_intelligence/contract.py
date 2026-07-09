"""Decision output contract serialization."""

from __future__ import annotations

import json
from typing import Any

from decision_intelligence.models import DecisionObject


def serialize_decision(decision: DecisionObject) -> dict[str, Any]:
    return decision.to_dict()


def deserialize_decision(data: dict[str, Any]) -> DecisionObject:
    return DecisionObject.from_dict(data)


def serialize_decisions(decisions: list[DecisionObject]) -> list[dict[str, Any]]:
    return [decision.to_dict() for decision in decisions]


def decisions_to_json(decisions: list[DecisionObject]) -> str:
    return json.dumps(serialize_decisions(decisions), indent=2, default=str)
