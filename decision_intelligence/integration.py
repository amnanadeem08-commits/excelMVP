"""Integration helpers: widgets and visualization request decisions via interface."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pandas as pd

from decision_intelligence.engine import DecisionIntelligenceEngine, get_default_engine
from decision_intelligence.models import DecisionObject, DecisionSource, SourceType

if TYPE_CHECKING:
    from widgets.base import BaseWidget


def dataset_summary_from_frame(df: pd.DataFrame, summary: dict[str, Any] | None = None) -> dict[str, Any]:
    summary = summary or {}
    total_cells = max(int(df.shape[0] * df.shape[1]), 1)
    missing_total = int(df.isna().sum().sum()) if not df.empty else 0
    missing_pct = round(missing_total / total_cells * 100, 2) if total_cells else 0.0
    return {
        "rows": int(summary.get("rows", len(df))),
        "columns": int(summary.get("columns", df.shape[1] if not df.empty else 0)),
        "missing_pct": float(summary.get("missing_pct", missing_pct)),
        "completeness_pct": float(summary.get("completeness_pct", max(0.0, 100.0 - missing_pct))),
    }


def build_source_from_widget(
    widget: BaseWidget,
    *,
    artifacts: dict[str, Any] | None = None,
    dataframe: pd.DataFrame | None = None,
) -> DecisionSource:
    artifacts = artifacts or {}
    df = dataframe if dataframe is not None else artifacts.get("_df_cache")
    if not isinstance(df, pd.DataFrame):
        df = pd.DataFrame()

    summary = dataset_summary_from_frame(df, artifacts.get("summary"))
    source_type = _widget_source_type(widget)
    metrics: dict[str, Any] = {}
    dimensions: list[str] = []
    trend_signal = ""

    if widget.widget_type == "kpi" and artifacts.get("kpis"):
        for label, payload in list(artifacts["kpis"].items())[:4]:
            metrics[label] = payload.get("value", "")
    if widget.widget_type == "chart":
        charts = artifacts.get("charts", [])
        metrics["chart_count"] = len(charts)
    if widget.widget_type == "chart" and widget.widget_settings.get("variant") == "forecast":
        source_type = SourceType.TREND.value
        trend_signal = "forecast"
    column_types = artifacts.get("column_types", {})
    dimensions = list(column_types.get("categorical", []))[:4]

    dataset_id = getattr(getattr(widget, "data_binding", None), "dataset_id", "") or ""

    return DecisionSource(
        source_id=widget.widget_id,
        source_type=source_type,
        title=widget.widget_title or widget.widget_name,
        widget_id=widget.widget_id,
        dataset_id=dataset_id,
        dataset_summary=summary,
        metrics=metrics,
        dimensions=dimensions,
        trend_signal=trend_signal,
        metadata={
            "widget_type": widget.widget_type,
            "legacy_type": widget.widget_metadata.legacy_type,
            "mode_key": widget.widget_metadata.mode_key,
        },
    )


def build_source_from_kpi(
    *,
    widget_id: str,
    title: str,
    metric_name: str,
    metric_value: Any,
    dataframe: pd.DataFrame,
    summary: dict[str, Any] | None = None,
) -> DecisionSource:
    return DecisionSource(
        source_id=widget_id,
        source_type=SourceType.KPI.value,
        title=title,
        widget_id=widget_id,
        dataset_summary=dataset_summary_from_frame(dataframe, summary),
        metrics={metric_name: metric_value},
    )


def build_source_from_chart(
    *,
    widget_id: str,
    title: str,
    chart_type: str,
    reason: str,
    dataframe: pd.DataFrame,
    summary: dict[str, Any] | None = None,
) -> DecisionSource:
    return DecisionSource(
        source_id=widget_id,
        source_type=SourceType.CHART.value,
        title=title,
        widget_id=widget_id,
        dataset_summary=dataset_summary_from_frame(dataframe, summary),
        metrics={"chart_type": chart_type},
        metadata={"recommendation_reason": reason},
    )


def build_source_from_trend(
    *,
    widget_id: str,
    title: str,
    trend_signal: str,
    dataframe: pd.DataFrame,
    summary: dict[str, Any] | None = None,
) -> DecisionSource:
    return DecisionSource(
        source_id=widget_id,
        source_type=SourceType.TREND.value,
        title=title,
        widget_id=widget_id,
        dataset_summary=dataset_summary_from_frame(dataframe, summary),
        trend_signal=trend_signal,
    )


def build_source_from_dashboard_section(
    *,
    section_id: str,
    title: str,
    artifacts: dict[str, Any],
    dataframe: pd.DataFrame,
) -> DecisionSource:
    return DecisionSource(
        source_id=section_id,
        source_type=SourceType.DASHBOARD_SECTION.value,
        title=title,
        widget_id=section_id,
        dataset_summary=dataset_summary_from_frame(dataframe, artifacts.get("summary")),
        metrics={
            "kpi_count": len(artifacts.get("kpis", {})),
            "chart_count": len(artifacts.get("charts", [])),
            "insight_count": len(artifacts.get("insights", [])),
        },
        metadata={"mode": artifacts.get("mode").key if artifacts.get("mode") else ""},
    )


def evaluate_widget(
    widget: BaseWidget,
    *,
    artifacts: dict[str, Any] | None = None,
    dataframe: pd.DataFrame | None = None,
    engine: DecisionIntelligenceEngine | None = None,
) -> DecisionObject:
    source = build_source_from_widget(widget, artifacts=artifacts, dataframe=dataframe)
    return (engine or get_default_engine()).evaluate(source)


def evaluate_dashboard_widgets(
    widgets: list[BaseWidget],
    *,
    artifacts: dict[str, Any],
    dataframe: pd.DataFrame,
    engine: DecisionIntelligenceEngine | None = None,
) -> list[DecisionObject]:
    engine = engine or get_default_engine()
    sources = [build_source_from_widget(widget, artifacts=artifacts, dataframe=dataframe) for widget in widgets]
    return engine.evaluate_batch(sources)


def _widget_source_type(widget: BaseWidget) -> str:
    if widget.widget_type == "kpi":
        return SourceType.KPI.value
    if widget.widget_type == "chart":
        if widget.widget_settings.get("variant") == "forecast":
            return SourceType.TREND.value
        return SourceType.CHART.value
    if widget.widget_type in {"table", "pivot", "text"}:
        return SourceType.DASHBOARD_SECTION.value
    return SourceType.DASHBOARD_SECTION.value
