"""Canvas state management for Streamlit sessions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import streamlit as st

from canvas.layout import DashboardLayout, LayoutManager
from canvas.serialization import layout_signature


SESSION_ROOT = "canvas_state"
LAYOUTS_KEY = "layouts"
ACTIVE_KEY = "active"


@dataclass
class CanvasSessionState:
    """Reserved-ready canvas session model."""

    active_dashboard_id: str | None = None
    active_sheet_id: str | None = None
    current_layout: dict[str, Any] | None = None
    selected_widget_id: str | None = None
    zoom_level: float = 1.0
    grid_visible: bool = True
    layout_cache: dict[str, dict[str, Any]] = field(default_factory=dict)


def _root() -> dict[str, Any]:
    if SESSION_ROOT not in st.session_state:
        st.session_state[SESSION_ROOT] = {
            ACTIVE_KEY: {
                "active_dashboard_id": None,
                "active_sheet_id": None,
                "selected_widget_id": None,
                "zoom_level": 1.0,
                "grid_visible": True,
            },
            LAYOUTS_KEY: {},
        }
    return st.session_state[SESSION_ROOT]


def _layout_key(workbook_id: str, sheet_id: str, dashboard_id: str) -> str:
    return f"{workbook_id}::{sheet_id}::{dashboard_id}"


def get_canvas_state() -> CanvasSessionState:
    root = _root()
    active = root[ACTIVE_KEY]
    return CanvasSessionState(
        active_dashboard_id=active.get("active_dashboard_id"),
        active_sheet_id=active.get("active_sheet_id"),
        current_layout=active.get("current_layout"),
        selected_widget_id=active.get("selected_widget_id"),
        zoom_level=float(active.get("zoom_level", 1.0)),
        grid_visible=bool(active.get("grid_visible", True)),
        layout_cache=dict(root.get(LAYOUTS_KEY, {})),
    )


def set_active_context(
    *,
    workbook_id: str,
    sheet_id: str,
    dashboard_id: str,
    layout: dict[str, Any],
) -> None:
    root = _root()
    key = _layout_key(workbook_id, sheet_id, dashboard_id)
    root[LAYOUTS_KEY][key] = layout
    root[ACTIVE_KEY] = {
        "active_dashboard_id": dashboard_id,
        "active_sheet_id": sheet_id,
        "selected_widget_id": root[ACTIVE_KEY].get("selected_widget_id"),
        "zoom_level": root[ACTIVE_KEY].get("zoom_level", 1.0),
        "grid_visible": root[ACTIVE_KEY].get("grid_visible", True),
        "current_layout": layout,
    }


def load_layout(workbook_id: str, sheet_id: str, dashboard_id: str) -> dict[str, Any] | None:
    root = _root()
    return root[LAYOUTS_KEY].get(_layout_key(workbook_id, sheet_id, dashboard_id))


def persist_layout(layout: dict[str, Any]) -> None:
    root = _root()
    key = _layout_key(layout["workbook_id"], layout["sheet_id"], layout["dashboard_id"])
    root[LAYOUTS_KEY][key] = layout
    root[ACTIVE_KEY]["current_layout"] = layout


def artifacts_signature(artifacts: dict[str, Any]) -> str:
    """Compact signature for artifact-driven layout regeneration."""
    mode = artifacts["mode"].key
    return "|".join(
        [
            mode,
            str(len(artifacts.get("kpis", {}))),
            str(len(artifacts.get("charts", []))),
            str(len(artifacts.get("pivots", []))),
            str(len(artifacts.get("insights", []))),
            str(bool(artifacts.get("financial_forecast"))),
        ]
    )


def load_or_create_layout(
    *,
    workbook_id: str,
    sheet_id: str,
    dashboard_id: str,
    theme: str,
    artifacts: dict[str, Any],
    manager: LayoutManager | None = None,
) -> DashboardLayout:
    """Load a cached layout or auto-generate one for the current context."""
    manager = manager or LayoutManager()
    artifact_sig = artifacts_signature(artifacts)
    existing = load_layout(workbook_id, sheet_id, dashboard_id)
    if existing:
        existing_sig = existing.get("metadata", {}).get("artifacts_signature")
        if existing_sig == artifact_sig:
            layout = manager.load(existing)
            set_active_context(
                workbook_id=workbook_id,
                sheet_id=sheet_id,
                dashboard_id=dashboard_id,
                layout=existing,
            )
            return layout

    layout = manager.auto_layout_from_artifacts(
        workbook_id=workbook_id,
        sheet_id=sheet_id,
        dashboard_id=dashboard_id,
        theme=theme,
        artifacts=artifacts,
    )
    payload = layout.to_dict()
    payload["metadata"] = {"artifacts_signature": artifact_sig, "signature": layout_signature(payload)}
    persist_layout(payload)
    set_active_context(
        workbook_id=workbook_id,
        sheet_id=sheet_id,
        dashboard_id=dashboard_id,
        layout=payload,
    )
    return layout
