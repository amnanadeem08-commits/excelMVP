"""Layout serialization for dashboard canvas."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from canvas.grid import LAYOUT_VERSION, GridConfig, WidgetPlacement


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def serialize_layout(
    *,
    workbook_id: str,
    sheet_id: str,
    dashboard_id: str,
    theme: str,
    grid: GridConfig,
    widgets: list[WidgetPlacement],
    created_at: str | None = None,
    updated_at: str | None = None,
    version: str = LAYOUT_VERSION,
) -> dict[str, Any]:
    """Serialize a dashboard layout to a versioned dictionary."""
    timestamp = _utc_now()
    return {
        "version": version,
        "workbook_id": workbook_id,
        "sheet_id": sheet_id,
        "dashboard_id": dashboard_id,
        "theme": theme,
        "grid": grid.to_dict(),
        "widgets": [widget.to_dict() for widget in widgets],
        "created_at": created_at or timestamp,
        "updated_at": updated_at or timestamp,
    }


def deserialize_layout(data: dict[str, Any]) -> dict[str, Any]:
    """Deserialize layout metadata and return normalized structures."""
    version = str(data.get("version", LAYOUT_VERSION))
    grid = GridConfig.from_dict(data.get("grid", {}))
    widgets = [WidgetPlacement.from_dict(item) for item in data.get("widgets", [])]
    return {
        "version": version,
        "workbook_id": str(data.get("workbook_id", "")),
        "sheet_id": str(data.get("sheet_id", "")),
        "dashboard_id": str(data.get("dashboard_id", "")),
        "theme": str(data.get("theme", "")),
        "grid": grid,
        "widgets": widgets,
        "created_at": str(data.get("created_at", "")),
        "updated_at": str(data.get("updated_at", "")),
    }


def layout_signature(data: dict[str, Any]) -> str:
    """Compact signature used to detect whether layout regeneration is needed."""
    widget_bits = [
        f"{item['widget_id']}:{item['widget_type']}:{item.get('col')}:{item.get('row')}"
        for item in data.get("widgets", [])
    ]
    return "|".join(
        [
            str(data.get("workbook_id", "")),
            str(data.get("sheet_id", "")),
            str(data.get("dashboard_id", "")),
            str(data.get("theme", "")),
            str(data.get("grid", {}).get("columns", "")),
            ",".join(widget_bits),
        ]
    )


def bump_updated_at(layout: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of layout data with a fresh updated_at timestamp."""
    updated = dict(layout)
    updated["updated_at"] = _utc_now()
    return updated
