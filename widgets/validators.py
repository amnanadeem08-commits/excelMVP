"""Widget validation."""

from __future__ import annotations

from typing import Any

from widgets.models import DataBinding, WidgetPlacement, WidgetStyle


SUPPORTED_EXPORT_TARGETS = {"dashboard", "pdf", "ppt", "excel", "png", "html"}
SUPPORTED_RENDER_TARGETS = {"dashboard", "pdf", "ppt", "excel", "png", "html"}


def validate_settings(widget_type: str, settings: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if not widget_type:
        issues.append("widget_type is required.")
    if widget_type in {"kpi", "chart", "table", "pivot"} and not settings.get("title"):
        issues.append(f"{widget_type}: title is recommended.")
    if widget_type == "chart" and not settings.get("chart_source") and not settings.get("chart_index"):
        if settings.get("variant") != "forecast":
            issues.append("chart: chart_source or chart_index required.")
    return issues


def validate_binding(binding: DataBinding) -> list[str]:
    issues: list[str] = []
    if not binding.dataset_id:
        issues.append("dataset_id is required.")
    if binding.refresh_policy not in {"on_change", "manual", "scheduled"}:
        issues.append(f"Unsupported refresh_policy: {binding.refresh_policy}")
    return issues


def validate_placement(placement: WidgetPlacement, *, max_columns: int = 12) -> list[str]:
    issues: list[str] = []
    if placement.col < 0 or placement.row < 0:
        issues.append("Placement coordinates cannot be negative.")
    if placement.col_span < 1 or placement.row_span < 1:
        issues.append("Placement spans must be >= 1.")
    if placement.col + placement.col_span > max_columns:
        issues.append("Placement exceeds grid width.")
    return issues


def validate_style(style: WidgetStyle, *, theme: str | None = None) -> list[str]:
    issues: list[str] = []
    if theme and style.theme not in {theme, "default"}:
        issues.append(f"Theme mismatch: widget={style.theme}, dashboard={theme}")
    return issues


def validate_export_compatibility(widget_type: str, target: str) -> list[str]:
    issues: list[str] = []
    if target not in SUPPORTED_EXPORT_TARGETS:
        issues.append(f"Unsupported export target: {target}")
    if widget_type in {"divider", "shape"} and target in {"excel", "ppt"}:
        issues.append(f"{widget_type} has limited support for {target}.")
    return issues


def validate_widget(
    *,
    widget_type: str,
    settings: dict[str, Any],
    binding: DataBinding,
    placement: WidgetPlacement,
    style: WidgetStyle,
    theme: str | None = None,
) -> list[str]:
    return (
        validate_settings(widget_type, settings)
        + validate_binding(binding)
        + validate_placement(placement)
        + validate_style(style, theme=theme)
    )
