"""Layout manager: widget positions, validation, and auto-layout."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from canvas.grid import (
    GridConfig,
    WidgetPlacement,
    detect_overlaps,
    is_grid_empty,
    validate_placements,
)
from canvas.serialization import bump_updated_at, deserialize_layout, serialize_layout


@dataclass
class DashboardLayout:
    """In-memory dashboard layout model."""

    workbook_id: str
    sheet_id: str
    dashboard_id: str
    theme: str
    grid: GridConfig = field(default_factory=GridConfig)
    widgets: list[WidgetPlacement] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    version: str = "2.0.0"

    def to_dict(self) -> dict[str, Any]:
        return serialize_layout(
            workbook_id=self.workbook_id,
            sheet_id=self.sheet_id,
            dashboard_id=self.dashboard_id,
            theme=self.theme,
            grid=self.grid,
            widgets=self.widgets,
            created_at=self.created_at,
            updated_at=self.updated_at,
            version=self.version,
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DashboardLayout:
        parsed = deserialize_layout(data)
        return cls(
            workbook_id=parsed["workbook_id"],
            sheet_id=parsed["sheet_id"],
            dashboard_id=parsed["dashboard_id"],
            theme=parsed["theme"],
            grid=parsed["grid"],
            widgets=parsed["widgets"],
            created_at=parsed["created_at"],
            updated_at=parsed["updated_at"],
            version=parsed["version"],
        )


class LayoutManager:
    """Manage widget positions, validation, and persistence helpers."""

    def __init__(self, layout: DashboardLayout | None = None) -> None:
        self.layout = layout or DashboardLayout(
            workbook_id="",
            sheet_id="",
            dashboard_id="",
            theme="",
        )

    @property
    def widgets(self) -> list[WidgetPlacement]:
        return self.layout.widgets

    @property
    def grid(self) -> GridConfig:
        return self.layout.grid

    def load(self, data: dict[str, Any]) -> DashboardLayout:
        self.layout = DashboardLayout.from_dict(data)
        return self.layout

    def save(self) -> dict[str, Any]:
        self.layout.updated_at = bump_updated_at(self.layout.to_dict())["updated_at"]
        return self.layout.to_dict()

    def set_widgets(self, widgets: list[WidgetPlacement]) -> None:
        self.layout.widgets = list(widgets)

    def add_widget(self, widget: WidgetPlacement) -> None:
        self.layout.widgets.append(widget)

    def get_widget(self, widget_id: str) -> WidgetPlacement | None:
        return next((widget for widget in self.layout.widgets if widget.widget_id == widget_id), None)

    def validate(self) -> list[str]:
        return validate_placements(self.layout.widgets, self.layout.grid)

    def has_overlaps(self) -> bool:
        return bool(detect_overlaps(self.layout.widgets))

    def is_empty(self) -> bool:
        return is_grid_empty(self.layout.widgets)

    def total_rows(self) -> int:
        if self.is_empty():
            return 0
        return max(widget.row + widget.row_span for widget in self.layout.widgets if widget.visible)

    def auto_layout_from_artifacts(
        self,
        *,
        workbook_id: str,
        sheet_id: str,
        dashboard_id: str,
        theme: str,
        artifacts: dict[str, Any],
    ) -> DashboardLayout:
        """Generate a non-overlapping layout from dashboard artifacts."""
        widgets = _build_widgets_for_mode(dashboard_id, artifacts)
        normalized = _normalize_rows(widgets, columns=self.layout.grid.columns)
        self.layout = DashboardLayout(
            workbook_id=workbook_id,
            sheet_id=sheet_id,
            dashboard_id=dashboard_id,
            theme=theme,
            grid=self.layout.grid,
            widgets=normalized,
        )
        issues = self.validate()
        if issues:
            normalized = _normalize_rows(_build_widgets_for_mode(dashboard_id, artifacts, safe=True), columns=self.layout.grid.columns)
            self.layout.widgets = normalized
        return self.layout


def _add_widget(
    widgets: list[WidgetPlacement],
    *,
    widget_id: str,
    widget_type: str,
    row: int,
    col: int,
    col_span: int,
    row_span: int,
    metadata: dict[str, Any] | None = None,
) -> None:
    widgets.append(
        WidgetPlacement(
            widget_id=widget_id,
            widget_type=widget_type,
            row=row,
            col=col,
            col_span=col_span,
            row_span=row_span,
            metadata=metadata or {},
        )
    )


def _build_widgets_for_mode(mode_key: str, artifacts: dict[str, Any], *, safe: bool = False) -> list[WidgetPlacement]:
    widgets: list[WidgetPlacement] = []
    row = 0

    _add_widget(
        widgets,
        widget_id=f"{mode_key}-header",
        widget_type="section_header",
        row=row,
        col=0,
        col_span=12,
        row_span=1,
        metadata={"title": artifacts["mode"].label, "caption": artifacts["mode"].description},
    )
    row += 1

    if artifacts.get("kpis"):
        _add_widget(
            widgets,
            widget_id=f"{mode_key}-kpis",
            widget_type="kpi_grid",
            row=row,
            col=0,
            col_span=12,
            row_span=2,
            metadata={"count": len(artifacts["kpis"])},
        )
        row += 2

    insights = artifacts.get("insights", [])
    if insights and mode_key in {"executive", "financial", "operational"}:
        span = 6 if mode_key == "executive" and not safe else 12
        _add_widget(
            widgets,
            widget_id=f"{mode_key}-insights",
            widget_type="insight_list",
            row=row,
            col=0,
            col_span=span,
            row_span=max(2, min(4, len(insights))),
            metadata={"count": len(insights)},
        )
        row += max(2, min(4, len(insights)))

    if mode_key == "financial":
        _add_widget(
            widgets,
            widget_id=f"{mode_key}-forecast",
            widget_type="forecast_chart",
            row=row,
            col=0,
            col_span=12,
            row_span=3,
        )
        row += 3

    charts = artifacts.get("charts", [])
    if charts:
        chart_limit = artifacts["mode"].chart_limit or len(charts)
        chart_count = min(len(charts), chart_limit)
        rows_needed = max(1, (chart_count + 1) // 2)
        _add_widget(
            widgets,
            widget_id=f"{mode_key}-charts",
            widget_type="chart_grid",
            row=row,
            col=0,
            col_span=12,
            row_span=rows_needed * 2,
            metadata={"count": chart_count, "two_column": True},
        )
        row += rows_needed * 2

    pivots = artifacts.get("pivots", [])
    if pivots and mode_key in {"analytical", "operational"}:
        _add_widget(
            widgets,
            widget_id=f"{mode_key}-pivots",
            widget_type="pivot_list",
            row=row,
            col=0,
            col_span=12,
            row_span=max(2, min(4, len(pivots))),
            metadata={"count": len(pivots)},
        )
        row += max(2, min(4, len(pivots)))

    if mode_key == "analytical":
        _add_widget(
            widgets,
            widget_id=f"{mode_key}-explorer",
            widget_type="dataframe",
            row=row,
            col=0,
            col_span=12,
            row_span=3,
            metadata={"title": "Data Explorer"},
        )

    return widgets


def _normalize_rows(widgets: list[WidgetPlacement], *, columns: int) -> list[WidgetPlacement]:
    """Pack widgets into non-overlapping rows while preserving order."""
    packed: list[WidgetPlacement] = []
    cursor_row = 0
    for widget in widgets:
        col_span = min(widget.col_span, columns)
        row_span = max(1, widget.row_span)
        packed.append(
            WidgetPlacement(
                widget_id=widget.widget_id,
                widget_type=widget.widget_type,
                col=0,
                row=cursor_row,
                col_span=col_span,
                row_span=row_span,
                z_index=widget.z_index,
                locked=widget.locked,
                visible=widget.visible,
                metadata=dict(widget.metadata),
            )
        )
        cursor_row += row_span
    return packed
