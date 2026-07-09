"""Export adapter: each widget exports itself."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from widgets.base import BaseWidget
from widgets.validators import validate_export_compatibility


@dataclass
class ExportResult:
    target: str
    widget_id: str
    widget_type: str
    ok: bool
    payload: dict[str, Any]
    errors: list[str]


class WidgetExportAdapter:
    """Widget-level export contract for dashboard/pdf/ppt/excel/png/html."""

    def export(self, widget: BaseWidget, target: str) -> ExportResult:
        widget.before_export({"target": target})
        errors = validate_export_compatibility(widget.widget_type, target)
        payload = self._build_payload(widget, target)
        result = ExportResult(
            target=target,
            widget_id=widget.widget_id,
            widget_type=widget.widget_type,
            ok=not errors,
            payload=payload,
            errors=errors,
        )
        widget.after_export({"target": target, "ok": result.ok})
        return result

    def export_many(self, widgets: list[BaseWidget], target: str) -> list[ExportResult]:
        return [self.export(widget, target) for widget in widgets if widget.widget_state.visible]

    def export_dashboard_bundle(self, widgets: list[BaseWidget]) -> dict[str, Any]:
        return {
            "widgets": [result.payload for result in self.export_many(widgets, "dashboard")],
            "count": len(widgets),
        }

    def _build_payload(self, widget: BaseWidget, target: str) -> dict[str, Any]:
        return {
            "widget_id": widget.widget_id,
            "widget_type": widget.widget_type,
            "title": widget.widget_title or widget.widget_settings.get("title", ""),
            "target": target,
            "placement": widget.placement.to_dict(),
            "settings": dict(widget.widget_settings),
            "binding": widget.data_binding.to_dict(),
            "metadata": widget.widget_metadata.to_dict(),
        }
