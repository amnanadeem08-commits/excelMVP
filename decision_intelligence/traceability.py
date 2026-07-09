"""Decision traceability: audit metadata without sensitive data."""

from __future__ import annotations

from typing import Any

from decision_intelligence.models import (
    CONFIDENCE_VERSION,
    ENGINE_VERSION,
    DecisionObject,
    DecisionSource,
    DecisionTraceability,
    SupportingEvidence,
)


def _visualization_version() -> str:
    try:
        from visualization_engine import VISUALIZATION_ENGINE_VERSION

        return VISUALIZATION_ENGINE_VERSION
    except Exception:
        return "unknown"


def evidence_references(evidence: list[SupportingEvidence]) -> list[str]:
    """Return reference pointers only — no raw sensitive values."""
    refs: list[str] = []
    for item in evidence:
        refs.append(f"{item.evidence_type}:{item.label}@{item.source or 'analysis'}")
    return refs


def build_reasoning_path(
    *,
    source: DecisionSource,
    provider_id: str,
    validated: bool,
    validation_flags: list[str],
    priority: str,
    confidence: float,
) -> list[dict[str, str]]:
    """Describe the non-sensitive reasoning chain for audit purposes."""
    path = [
        {"step": "source_ingest", "detail": f"type={source.source_type}, title={source.title}"},
        {
            "step": "dataset_context",
            "detail": (
                f"dataset_id={source.dataset_id or 'unspecified'}, "
                f"rows={source.dataset_summary.get('rows', 0)}, "
                f"completeness={source.dataset_summary.get('completeness_pct', 0)}%"
            ),
        },
        {"step": "provider_generate", "detail": f"provider={provider_id}"},
        {
            "step": "quality_validate",
            "detail": (
                f"validated={validated}, flags={len(validation_flags)}, "
                f"confidence={confidence:.2f}"
            ),
        },
        {"step": "priority_assign", "detail": f"priority={priority}"},
    ]
    if source.trend_signal:
        path.insert(2, {"step": "trend_signal", "detail": f"signal={source.trend_signal}"})
    if validation_flags:
        path.append({"step": "validation_flags", "detail": "; ".join(validation_flags[:3])})
    return path


def build_traceability(
    decision: DecisionObject,
    source: DecisionSource,
    *,
    provider_id: str,
) -> DecisionTraceability:
    """Attach audit metadata to a decision without storing sensitive payloads."""
    return DecisionTraceability(
        decision_id=decision.decision_id,
        widget_id=source.widget_id or source.source_id,
        dataset_id=source.dataset_id,
        generated_at=decision.timestamp,
        engine_version=ENGINE_VERSION,
        visualization_version=_visualization_version(),
        confidence_version=CONFIDENCE_VERSION,
        evidence_references=evidence_references(decision.evidence),
        reasoning_path=build_reasoning_path(
            source=source,
            provider_id=provider_id,
            validated=decision.validated,
            validation_flags=decision.validation_flags,
            priority=decision.priority,
            confidence=decision.confidence,
        ),
        provider_id=provider_id,
        source_type=source.source_type,
    )


class DecisionTraceStore:
    """In-memory trace registry for temporal comparison and audit."""

    def __init__(self) -> None:
        self._by_decision: dict[str, DecisionTraceability] = {}
        self._by_widget: dict[str, list[str]] = {}
        self._by_dataset: dict[str, list[str]] = {}

    def record(self, trace: DecisionTraceability) -> None:
        self._by_decision[trace.decision_id] = trace
        if trace.widget_id:
            self._by_widget.setdefault(trace.widget_id, []).append(trace.decision_id)
        if trace.dataset_id:
            self._by_dataset.setdefault(trace.dataset_id, []).append(trace.decision_id)

    def get(self, decision_id: str) -> DecisionTraceability | None:
        return self._by_decision.get(decision_id)

    def history_for_widget(self, widget_id: str, *, limit: int = 20) -> list[DecisionTraceability]:
        ids = self._by_widget.get(widget_id, [])
        return [self._by_decision[item] for item in ids[-limit:] if item in self._by_decision]

    def history_for_dataset(self, dataset_id: str, *, limit: int = 20) -> list[DecisionTraceability]:
        ids = self._by_dataset.get(dataset_id, [])
        return [self._by_decision[item] for item in ids[-limit:] if item in self._by_decision]

    def compare(self, left_id: str, right_id: str) -> dict[str, Any]:
        """Compare two decision traces to detect recommendation drift."""
        left = self._by_decision.get(left_id)
        right = self._by_decision.get(right_id)
        if left is None or right is None:
            return {"ok": False, "message": "One or both decision traces were not found."}
        changed: dict[str, Any] = {}
        if left.confidence_version != right.confidence_version:
            changed["confidence_version"] = [left.confidence_version, right.confidence_version]
        if left.engine_version != right.engine_version:
            changed["engine_version"] = [left.engine_version, right.engine_version]
        if left.reasoning_path != right.reasoning_path:
            changed["reasoning_path_length"] = [len(left.reasoning_path), len(right.reasoning_path)]
        if left.evidence_references != right.evidence_references:
            changed["evidence_references"] = {
                "added": sorted(set(right.evidence_references) - set(left.evidence_references)),
                "removed": sorted(set(left.evidence_references) - set(right.evidence_references)),
            }
        return {
            "ok": True,
            "left_decision_id": left_id,
            "right_decision_id": right_id,
            "widget_id": left.widget_id,
            "dataset_id": left.dataset_id,
            "changed": changed,
            "has_drift": bool(changed),
        }

    def count(self) -> int:
        return len(self._by_decision)

    def clear(self) -> None:
        self._by_decision.clear()
        self._by_widget.clear()
        self._by_dataset.clear()
