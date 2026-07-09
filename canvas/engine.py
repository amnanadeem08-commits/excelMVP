"""Dashboard canvas engine: initialization, sizing, and layout orchestration."""

from __future__ import annotations

import time
import tracemalloc
from dataclasses import dataclass, field
from typing import Any

from canvas.grid import GridConfig, WidgetPlacement, resolve_columns, sorted_render_groups, validate_placements
from canvas.layout import DashboardLayout, LayoutManager
from canvas.serialization import layout_signature


DEFAULT_CONTAINER_WIDTH = 1200.0


@dataclass
class CanvasDimensions:
    """Computed canvas dimensions for responsive rendering."""

    container_width_px: float
    effective_columns: int
    total_rows: int
    row_height_px: int
    gap_px: int

    @property
    def height_px(self) -> float:
        return max(self.total_rows, 1) * self.row_height_px + max(self.total_rows - 1, 0) * self.gap_px


@dataclass
class CanvasMetrics:
    """Performance metrics for canvas operations."""

    init_ms: float = 0.0
    render_ms: float = 0.0
    peak_memory_kb: float = 0.0
    widget_count: int = 0
    validation_issues: list[str] = field(default_factory=list)


class CanvasEngine:
    """Reusable dashboard canvas engine."""

    def __init__(
        self,
        layout: DashboardLayout | None = None,
        *,
        container_width_px: float = DEFAULT_CONTAINER_WIDTH,
    ) -> None:
        self.layout_manager = LayoutManager(layout)
        self.container_width_px = container_width_px
        self.metrics = CanvasMetrics()
        self._dimensions: CanvasDimensions | None = None

    @property
    def layout(self) -> DashboardLayout:
        return self.layout_manager.layout

    def initialize(
        self,
        *,
        workbook_id: str,
        sheet_id: str,
        dashboard_id: str,
        theme: str,
        artifacts: dict[str, Any],
        grid: GridConfig | None = None,
    ) -> DashboardLayout:
        """Initialize or refresh the canvas layout from dashboard artifacts."""
        started = time.perf_counter()
        tracemalloc.start()
        if grid is not None:
            self.layout_manager.layout.grid = grid
        layout = self.layout_manager.auto_layout_from_artifacts(
            workbook_id=workbook_id,
            sheet_id=sheet_id,
            dashboard_id=dashboard_id,
            theme=theme,
            artifacts=artifacts,
        )
        self._dimensions = self._compute_dimensions(layout)
        self.metrics.init_ms = (time.perf_counter() - started) * 1000
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        self.metrics.peak_memory_kb = peak / 1024
        self.metrics.widget_count = len(layout.widgets)
        self.metrics.validation_issues = self.layout_manager.validate()
        return layout

    def load(self, data: dict[str, Any]) -> DashboardLayout:
        layout = self.layout_manager.load(data)
        self._dimensions = self._compute_dimensions(layout)
        self.metrics.validation_issues = self.layout_manager.validate()
        self.metrics.widget_count = len(layout.widgets)
        return layout

    def dimensions(self) -> CanvasDimensions:
        if self._dimensions is None:
            self._dimensions = self._compute_dimensions(self.layout)
        return self._dimensions

    def render_plan(self) -> list[WidgetPlacement]:
        """Return widgets in render order without drawing."""
        return sorted_render_groups(self.layout.widgets)

    def serialize(self) -> dict[str, Any]:
        payload = self.layout_manager.save()
        payload.setdefault("metadata", {})["signature"] = layout_signature(payload)
        return payload

    def validate(self) -> list[str]:
        return validate_placements(self.layout.widgets, self.layout.grid)

    def _compute_dimensions(self, layout: DashboardLayout) -> CanvasDimensions:
        effective_columns = resolve_columns(self.container_width_px, layout.grid)
        total_rows = self.layout_manager.total_rows()
        return CanvasDimensions(
            container_width_px=self.container_width_px,
            effective_columns=effective_columns,
            total_rows=total_rows,
            row_height_px=layout.grid.row_height_px,
            gap_px=layout.grid.gap_px,
        )

    def mark_render_complete(self, elapsed_ms: float) -> None:
        self.metrics.render_ms = elapsed_ms
