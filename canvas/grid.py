"""Grid system for the dashboard canvas."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


LAYOUT_VERSION = "2.0.0"

# Breakpoints: minimum footprint-ratio thresholds mapped to column counts.
# footprint_ratio = (min_column_width * base_columns) / container_width
BREAKPOINTS: tuple[tuple[float, int], ...] = (
    (1.25, 4),   # tablet-ready (narrow)
    (0.72, 8),   # laptop
    (0.0, 12),   # desktop / wide
)


@dataclass(frozen=True)
class GridConfig:
    """Responsive grid configuration."""

    columns: int = 12
    row_height_px: int = 80
    gap_px: int = 12
    min_column_width_px: int = 72

    def to_dict(self) -> dict[str, Any]:
        return {
            "columns": self.columns,
            "row_height_px": self.row_height_px,
            "gap_px": self.gap_px,
            "min_column_width_px": self.min_column_width_px,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GridConfig:
        return cls(
            columns=int(data.get("columns", 12)),
            row_height_px=int(data.get("row_height_px", 80)),
            gap_px=int(data.get("gap_px", 12)),
            min_column_width_px=int(data.get("min_column_width_px", 72)),
        )


@dataclass
class WidgetPlacement:
    """A widget position on the canvas grid."""

    widget_id: str
    widget_type: str
    col: int
    row: int
    col_span: int = 4
    row_span: int = 2
    z_index: int = 0
    locked: bool = False
    visible: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "widget_id": self.widget_id,
            "widget_type": self.widget_type,
            "col": self.col,
            "row": self.row,
            "col_span": self.col_span,
            "row_span": self.row_span,
            "z_index": self.z_index,
            "locked": self.locked,
            "visible": self.visible,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WidgetPlacement:
        return cls(
            widget_id=str(data["widget_id"]),
            widget_type=str(data["widget_type"]),
            col=int(data["col"]),
            row=int(data["row"]),
            col_span=int(data.get("col_span", 4)),
            row_span=int(data.get("row_span", 2)),
            z_index=int(data.get("z_index", 0)),
            locked=bool(data.get("locked", False)),
            visible=bool(data.get("visible", True)),
            metadata=dict(data.get("metadata", {})),
        )

    def occupies(self, col: int, row: int) -> bool:
        return (
            self.col <= col < self.col + self.col_span
            and self.row <= row < self.row + self.row_span
        )

    def overlaps(self, other: WidgetPlacement) -> bool:
        if not self.visible or not other.visible:
            return False
        horizontal = self.col < other.col + other.col_span and other.col < self.col + self.col_span
        vertical = self.row < other.row + other.row_span and other.row < self.row + self.row_span
        return horizontal and vertical


def resolve_columns(container_width_px: float, grid: GridConfig) -> int:
    """Return effective column count for a container width using ratio breakpoints."""
    if container_width_px <= 0:
        return grid.columns
    max_fit = max(1, int(container_width_px // max(grid.min_column_width_px, 1)))
    footprint_ratio = (grid.min_column_width_px * grid.columns) / max(container_width_px, 1.0)
    chosen = grid.columns
    for threshold, columns in sorted(BREAKPOINTS, reverse=True):
        if footprint_ratio >= threshold:
            chosen = columns
            break
    return max(1, min(chosen, grid.columns, max_fit))


def is_grid_empty(widgets: list[WidgetPlacement]) -> bool:
    """Return True when no visible widgets occupy the grid."""
    return not any(widget.visible for widget in widgets)


def detect_overlaps(widgets: list[WidgetPlacement]) -> list[tuple[str, str]]:
    """Return pairs of widget ids that overlap."""
    visible = [widget for widget in widgets if widget.visible]
    pairs: list[tuple[str, str]] = []
    for index, left in enumerate(visible):
        for right in visible[index + 1 :]:
            if left.overlaps(right):
                pairs.append((left.widget_id, right.widget_id))
    return pairs


def validate_placements(widgets: list[WidgetPlacement], grid: GridConfig) -> list[str]:
    """Validate widget coordinates against the grid."""
    issues: list[str] = []
    if is_grid_empty(widgets):
        issues.append("Grid has no visible widgets.")
        return issues

    for widget in widgets:
        if not widget.visible:
            continue
        if widget.col < 0 or widget.row < 0:
            issues.append(f"{widget.widget_id}: negative coordinates are invalid.")
        if widget.col_span < 1 or widget.row_span < 1:
            issues.append(f"{widget.widget_id}: span must be at least 1.")
        if widget.col + widget.col_span > grid.columns:
            issues.append(
                f"{widget.widget_id}: exceeds grid width ({widget.col + widget.col_span}>{grid.columns})."
            )

    for left_id, right_id in detect_overlaps(widgets):
        issues.append(f"Overlap detected between '{left_id}' and '{right_id}'.")

    return issues


def row_groups(widgets: list[WidgetPlacement]) -> list[list[WidgetPlacement]]:
    """Group visible widgets by row for rendering."""
    visible = [widget for widget in widgets if widget.visible]
    if not visible:
        return []
    max_row = max(widget.row + widget.row_span for widget in visible)
    groups: list[list[WidgetPlacement]] = []
    for row_index in range(max_row):
        row_widgets = [widget for widget in visible if widget.occupies(0, row_index) or widget.row == row_index]
        if row_index == 0 or any(widget.row == row_index for widget in visible):
            current = [widget for widget in visible if widget.row <= row_index < widget.row + widget.row_span]
            current = [widget for widget in current if widget.row == row_index or row_index == widget.row]
        row_widgets = [widget for widget in visible if widget.row == row_index]
        if row_widgets:
            groups.append(sorted(row_widgets, key=lambda item: (item.col, item.z_index)))
    return groups


def sorted_render_groups(widgets: list[WidgetPlacement]) -> list[WidgetPlacement]:
    """Return widgets in stable render order (row, col, z-index)."""
    visible = [widget for widget in widgets if widget.visible]
    return sorted(visible, key=lambda item: (item.row, item.col, item.z_index))


def css_grid_style(grid: GridConfig, effective_columns: int, total_rows: int) -> str:
    """Build CSS grid styles for the canvas container."""
    row_count = max(total_rows, 1)
    return (
        "display:grid;"
        f"grid-template-columns:repeat({effective_columns}, minmax(0, 1fr));"
        f"grid-auto-rows:minmax({grid.row_height_px}px, auto);"
        f"gap:{grid.gap_px}px;"
        "width:100%;"
        "align-items:stretch;"
    )


def placement_style(widget: WidgetPlacement, effective_columns: int) -> str:
    """Inline CSS grid-area style for a widget."""
    col_start = widget.col + 1
    col_end = min(widget.col + widget.col_span, effective_columns) + 1
    row_start = widget.row + 1
    row_end = widget.row + widget.row_span + 1
    return (
        f"grid-column:{col_start} / {col_end};"
        f"grid-row:{row_start} / {row_end};"
        "min-width:0;"
    )
