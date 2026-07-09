"""Widget factory: dashboard never creates widgets directly."""

from __future__ import annotations

from typing import Any

from canvas.grid import WidgetPlacement as CanvasPlacement
from widgets.base import BaseWidget
from widgets.databinding import default_binding
from widgets.models import WidgetMetadata, WidgetPlacement, WidgetState, WidgetStyle, new_widget_id
from widgets.registry import get_widget_class


LEGACY_TYPE_MAP: dict[str, str] = {
    "section_header": "text",
    "kpi_grid": "kpi",
    "insight_list": "text",
    "chart_grid": "chart",
    "pivot_list": "pivot",
    "dataframe": "table",
    "forecast_chart": "chart",
}


class WidgetFactory:
    """Create widgets from specs, layouts, or plugin registrations."""

    @staticmethod
    def create(
        widget_type: str,
        *,
        widget_id: str | None = None,
        title: str = "",
        settings: dict[str, Any] | None = None,
        dataset_id: str = "",
        placement: WidgetPlacement | None = None,
        theme: str = "default",
        metadata: dict[str, Any] | None = None,
    ) -> BaseWidget:
        widget_cls = get_widget_class(widget_type)
        widget_settings = dict(settings or {})
        if title:
            widget_settings.setdefault("title", title)
        widget = widget_cls(
            widget_id=widget_id or new_widget_id(),
            widget_name=widget_type,
            widget_title=title,
            placement=placement or WidgetPlacement(),
            widget_style=WidgetStyle(theme=theme),
            widget_settings=widget_settings,
            data_binding=default_binding(dataset_id) if dataset_id else default_binding(""),
            widget_metadata=WidgetMetadata(extra=dict(metadata or {})),
        )
        widget.initialize({"source": "factory"})
        return widget

    @staticmethod
    def from_legacy_placement(
        placement: CanvasPlacement,
        *,
        legacy_type: str,
        widget_id: str,
        dataset_id: str,
        theme: str,
        mode_key: str,
        metadata: dict[str, Any] | None = None,
    ) -> BaseWidget:
        widget_type = LEGACY_TYPE_MAP.get(legacy_type, legacy_type)
        settings = dict(metadata or {})
        settings["legacy_type"] = legacy_type
        if legacy_type == "forecast_chart":
            settings["variant"] = "forecast"
        if legacy_type == "insight_list":
            settings["variant"] = "insights"
        if legacy_type == "section_header":
            settings["variant"] = "header"
        title = settings.get("title", widget_id)
        widget = WidgetFactory.create(
            widget_type,
            widget_id=widget_id,
            title=str(title),
            settings=settings,
            dataset_id=dataset_id,
            placement=WidgetPlacement(
                col=placement.col,
                row=placement.row,
                col_span=placement.col_span,
                row_span=placement.row_span,
                z_index=placement.z_index,
            ),
            theme=theme,
            metadata={"mode_key": mode_key, "legacy_type": legacy_type},
        )
        widget.widget_state.visible = placement.visible if hasattr(placement, "visible") else True
        widget.widget_state.locked = placement.locked if hasattr(placement, "locked") else False
        widget.widget_metadata.mode_key = mode_key
        widget.widget_metadata.legacy_type = legacy_type
        return widget

    @staticmethod
    def from_canvas_layout(
        layout_widgets: list[CanvasPlacement],
        *,
        dataset_id: str,
        theme: str,
        mode_key: str,
        placement_meta: dict[str, dict[str, Any]] | None = None,
    ) -> list[BaseWidget]:
        widgets: list[BaseWidget] = []
        for placement in layout_widgets:
            meta = dict((placement_meta or {}).get(placement.widget_id, {}))
            legacy_type = placement.widget_type
            widget = WidgetFactory.from_legacy_placement(
                placement,
                legacy_type=legacy_type,
                widget_id=placement.widget_id,
                dataset_id=dataset_id,
                theme=theme,
                mode_key=mode_key,
                metadata={**placement.metadata, **meta},
            )
            widgets.append(widget)
        return widgets
