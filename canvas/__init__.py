"""Dashboard canvas engine public API."""

from canvas.engine import CanvasDimensions, CanvasEngine, CanvasMetrics, DEFAULT_CONTAINER_WIDTH
from canvas.grid import (
    GridConfig,
    WidgetPlacement,
    detect_overlaps,
    is_grid_empty,
    resolve_columns,
    validate_placements,
)
from canvas.layout import DashboardLayout, LayoutManager
from canvas.renderer import inject_canvas_styles, render_dashboard_canvas
from canvas.serialization import deserialize_layout, layout_signature, serialize_layout
from canvas.state import get_canvas_state, load_or_create_layout, load_layout, persist_layout

__all__ = [
    "CanvasDimensions",
    "CanvasEngine",
    "CanvasMetrics",
    "DEFAULT_CONTAINER_WIDTH",
    "DashboardLayout",
    "GridConfig",
    "LayoutManager",
    "WidgetPlacement",
    "deserialize_layout",
    "detect_overlaps",
    "get_canvas_state",
    "inject_canvas_styles",
    "is_grid_empty",
    "layout_signature",
    "load_layout",
    "load_or_create_layout",
    "persist_layout",
    "render_dashboard_canvas",
    "resolve_columns",
    "serialize_layout",
    "validate_placements",
]
