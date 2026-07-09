"""Decision Intelligence domain models and output contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


DECISION_SCHEMA_VERSION = "1.1.0"
ENGINE_VERSION = "1.1.0"
CONFIDENCE_VERSION = "1.0.0"


class Priority(str, Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class RiskLevel(str, Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    NONE = "None"


class SourceType(str, Enum):
    KPI = "kpi"
    CHART = "chart"
    TREND = "trend"
    DASHBOARD_SECTION = "dashboard_section"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def new_decision_id() -> str:
    return str(uuid4())


@dataclass
class SupportingEvidence:
    """Metric, dimension or calculation supporting a decision."""

    label: str
    value: str
    evidence_type: str = "metric"
    source: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "value": self.value,
            "evidence_type": self.evidence_type,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SupportingEvidence:
        return cls(
            label=str(data.get("label", "")),
            value=str(data.get("value", "")),
            evidence_type=str(data.get("evidence_type", "metric")),
            source=str(data.get("source", "")),
        )


@dataclass
class DecisionTraceability:
    """Audit metadata for decision explainability — no sensitive data stored."""

    decision_id: str
    widget_id: str = ""
    dataset_id: str = ""
    generated_at: str = field(default_factory=utc_now)
    engine_version: str = ENGINE_VERSION
    visualization_version: str = ""
    confidence_version: str = CONFIDENCE_VERSION
    evidence_references: list[str] = field(default_factory=list)
    reasoning_path: list[dict[str, str]] = field(default_factory=list)
    provider_id: str = ""
    source_type: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "widget_id": self.widget_id,
            "dataset_id": self.dataset_id,
            "generated_at": self.generated_at,
            "engine_version": self.engine_version,
            "visualization_version": self.visualization_version,
            "confidence_version": self.confidence_version,
            "evidence_references": list(self.evidence_references),
            "reasoning_path": [dict(step) for step in self.reasoning_path],
            "provider_id": self.provider_id,
            "source_type": self.source_type,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DecisionTraceability:
        return cls(
            decision_id=str(data.get("decision_id", new_decision_id())),
            widget_id=str(data.get("widget_id", "")),
            dataset_id=str(data.get("dataset_id", "")),
            generated_at=str(data.get("generated_at", utc_now())),
            engine_version=str(data.get("engine_version", ENGINE_VERSION)),
            visualization_version=str(data.get("visualization_version", "")),
            confidence_version=str(data.get("confidence_version", CONFIDENCE_VERSION)),
            evidence_references=list(data.get("evidence_references", [])),
            reasoning_path=[dict(step) for step in data.get("reasoning_path", [])],
            provider_id=str(data.get("provider_id", "")),
            source_type=str(data.get("source_type", "")),
        )


@dataclass
class DecisionQualityScores:
    """Validation dimension scores (0.0–1.0)."""

    business_relevance: float = 0.0
    statistical_validity: float = 0.0
    data_quality: float = 0.0
    confidence: float = 0.0
    explainability: float = 0.0
    actionability: float = 0.0

    def to_dict(self) -> dict[str, float]:
        return {
            "business_relevance": self.business_relevance,
            "statistical_validity": self.statistical_validity,
            "data_quality": self.data_quality,
            "confidence": self.confidence,
            "explainability": self.explainability,
            "actionability": self.actionability,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DecisionQualityScores:
        return cls(
            business_relevance=float(data.get("business_relevance", 0.0)),
            statistical_validity=float(data.get("statistical_validity", 0.0)),
            data_quality=float(data.get("data_quality", 0.0)),
            confidence=float(data.get("confidence", 0.0)),
            explainability=float(data.get("explainability", 0.0)),
            actionability=float(data.get("actionability", 0.0)),
        )

    @property
    def average(self) -> float:
        scores = list(self.to_dict().values())
        return sum(scores) / max(len(scores), 1)


@dataclass
class DecisionObject:
    """Standardized decision output contract for all intelligence consumers."""

    decision_id: str = field(default_factory=new_decision_id)
    source_widget: str = ""
    source_type: str = SourceType.DASHBOARD_SECTION.value
    insight: str = ""
    reason: str = ""
    business_impact: str = ""
    recommended_actions: list[str] = field(default_factory=list)
    priority: str = Priority.MEDIUM.value
    confidence: float = 0.0
    evidence: list[SupportingEvidence] = field(default_factory=list)
    risk_level: str = RiskLevel.MEDIUM.value
    risk_assessment: str = ""
    opportunity: str = ""
    executive_summary: str = ""
    timestamp: str = field(default_factory=utc_now)
    schema_version: str = DECISION_SCHEMA_VERSION
    validated: bool = True
    validation_flags: list[str] = field(default_factory=list)
    quality_scores: DecisionQualityScores = field(default_factory=DecisionQualityScores)
    traceability: DecisionTraceability | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "decision_id": self.decision_id,
            "source_widget": self.source_widget,
            "source_type": self.source_type,
            "insight": self.insight,
            "reason": self.reason,
            "business_impact": self.business_impact,
            "recommended_actions": list(self.recommended_actions),
            "priority": self.priority,
            "confidence": self.confidence,
            "evidence": [item.to_dict() for item in self.evidence],
            "risk_level": self.risk_level,
            "risk_assessment": self.risk_assessment,
            "opportunity": self.opportunity,
            "executive_summary": self.executive_summary,
            "timestamp": self.timestamp,
            "schema_version": self.schema_version,
            "validated": self.validated,
            "validation_flags": list(self.validation_flags),
            "quality_scores": self.quality_scores.to_dict(),
            "metadata": dict(self.metadata),
        }
        if self.traceability is not None:
            payload["traceability"] = self.traceability.to_dict()
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DecisionObject:
        return cls(
            decision_id=str(data.get("decision_id", new_decision_id())),
            source_widget=str(data.get("source_widget", "")),
            source_type=str(data.get("source_type", SourceType.DASHBOARD_SECTION.value)),
            insight=str(data.get("insight", "")),
            reason=str(data.get("reason", "")),
            business_impact=str(data.get("business_impact", "")),
            recommended_actions=list(data.get("recommended_actions", [])),
            priority=str(data.get("priority", Priority.MEDIUM.value)),
            confidence=float(data.get("confidence", 0.0)),
            evidence=[SupportingEvidence.from_dict(item) for item in data.get("evidence", [])],
            risk_level=str(data.get("risk_level", RiskLevel.MEDIUM.value)),
            risk_assessment=str(data.get("risk_assessment", "")),
            opportunity=str(data.get("opportunity", "")),
            executive_summary=str(data.get("executive_summary", "")),
            timestamp=str(data.get("timestamp", utc_now())),
            schema_version=str(data.get("schema_version", DECISION_SCHEMA_VERSION)),
            validated=bool(data.get("validated", True)),
            validation_flags=list(data.get("validation_flags", [])),
            quality_scores=DecisionQualityScores.from_dict(data.get("quality_scores", {})),
            traceability=(
                DecisionTraceability.from_dict(data["traceability"])
                if data.get("traceability")
                else None
            ),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass
class DecisionSource:
    """Input context for decision evaluation — no rendering data."""

    source_id: str
    source_type: str
    title: str
    widget_id: str = ""
    dataset_id: str = ""
    dataset_summary: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)
    dimensions: list[str] = field(default_factory=list)
    trend_signal: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_type": self.source_type,
            "title": self.title,
            "widget_id": self.widget_id,
            "dataset_id": self.dataset_id,
            "dataset_summary": dict(self.dataset_summary),
            "metrics": dict(self.metrics),
            "dimensions": list(self.dimensions),
            "trend_signal": self.trend_signal,
            "metadata": dict(self.metadata),
        }
