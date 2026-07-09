"""Decision quality validation."""

from __future__ import annotations

from decision_intelligence.models import DecisionObject, DecisionQualityScores, DecisionSource, Priority


VALIDATION_THRESHOLD = 0.55
CONFIDENCE_THRESHOLD = 0.45


def score_business_relevance(decision: DecisionObject, source: DecisionSource) -> float:
    score = 0.5
    if decision.insight and len(decision.insight) > 20:
        score += 0.15
    if decision.business_impact:
        score += 0.15
    if source.metrics or source.dataset_summary:
        score += 0.1
    if decision.source_type in {"kpi", "chart", "trend"}:
        score += 0.1
    return min(score, 1.0)


def score_statistical_validity(source: DecisionSource) -> float:
    rows = int(source.dataset_summary.get("rows", 0))
    if rows >= 100:
        return 0.9
    if rows >= 30:
        return 0.75
    if rows >= 10:
        return 0.6
    if rows > 0:
        return 0.45
    return 0.2


def score_data_quality(source: DecisionSource) -> float:
    completeness = float(source.dataset_summary.get("completeness_pct", 0.0))
    if completeness <= 0:
        missing_pct = float(source.dataset_summary.get("missing_pct", 100.0))
        completeness = max(0.0, 100.0 - missing_pct)
    return min(max(completeness / 100.0, 0.0), 1.0)


def score_explainability(decision: DecisionObject) -> float:
    score = 0.4
    if decision.reason:
        score += 0.2
    if decision.evidence:
        score += min(0.3, 0.1 * len(decision.evidence))
    if decision.executive_summary:
        score += 0.1
    return min(score, 1.0)


def score_actionability(decision: DecisionObject) -> float:
    if not decision.recommended_actions:
        return 0.3
    actionable = sum(1 for action in decision.recommended_actions if len(action) > 12)
    return min(0.5 + 0.15 * actionable, 1.0)


def validate_decision(decision: DecisionObject, source: DecisionSource) -> DecisionObject:
    """Score and flag decisions that fail quality thresholds."""
    scores = DecisionQualityScores(
        business_relevance=score_business_relevance(decision, source),
        statistical_validity=score_statistical_validity(source),
        data_quality=score_data_quality(source),
        confidence=min(max(decision.confidence, 0.0), 1.0),
        explainability=score_explainability(decision),
        actionability=score_actionability(decision),
    )
    decision.quality_scores = scores

    flags: list[str] = []
    if scores.business_relevance < VALIDATION_THRESHOLD:
        flags.append("Low business relevance")
    if scores.statistical_validity < VALIDATION_THRESHOLD:
        flags.append("Limited statistical validity")
    if scores.data_quality < VALIDATION_THRESHOLD:
        flags.append("Poor data quality")
    if scores.confidence < CONFIDENCE_THRESHOLD:
        flags.append("Low confidence score")
    if scores.explainability < VALIDATION_THRESHOLD:
        flags.append("Insufficient explainability")
    if scores.actionability < VALIDATION_THRESHOLD:
        flags.append("Low actionability")

    decision.validation_flags = flags
    decision.validated = not flags and scores.average >= VALIDATION_THRESHOLD

    if not decision.validated and decision.priority == Priority.CRITICAL.value:
        decision.priority = Priority.HIGH.value

    decision.metadata["quality_average"] = round(scores.average, 3)
    return decision
