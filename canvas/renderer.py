"""Canvas Streamlit renderer integrated with the widget framework."""

from __future__ import annotations

import time
from typing import Any

import pandas as pd
import streamlit as st

from canvas.engine import CanvasEngine
from canvas.grid import css_grid_style, placement_style, sorted_render_groups
from canvas.state import load_or_create_layout
from dashboard import get_default_theme
from decision_intelligence.contract import serialize_decisions
from widgets.canvas_bridge import DashboardWidgetBridge


def inject_canvas_styles() -> None:
    st.markdown(
        """
        <style>
        .dashboard-canvas {
            border: 1px solid rgba(148, 163, 184, .28);
            border-radius: 12px;
            background: rgba(255, 255, 255, .9);
            padding: .85rem;
            margin-bottom: .75rem;
            box-shadow: 0 10px 28px rgba(15, 23, 42, .05);
        }
        .canvas-widget {
            border: 1px solid rgba(148, 163, 184, .18);
            border-radius: 10px;
            background: rgba(248, 250, 252, .72);
            padding: .55rem .65rem;
            min-height: 2.5rem;
        }
        .canvas-widget[data-grid-visible="true"] {
            outline: 1px dashed rgba(37, 99, 235, .18);
        }
        .canvas-meta {
            font-size: .78rem;
            color: #64748b;
            margin-top: .35rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_dashboard_canvas(
    df: pd.DataFrame,
    *,
    workbook_id: str,
    sheet_id: str,
    dashboard_id: str,
    theme: dict[str, Any] | None,
    artifacts: dict[str, Any],
    dashboard_config: dict[str, Any] | None = None,
    container_width_px: float = 1200.0,
) -> dict[str, Any]:
    """Render dashboard via Canvas -> Widget Controller -> Renderer pipeline."""
    theme = theme or get_default_theme()
    theme_name = str(theme.get("accent", "default"))
    artifacts = dict(artifacts)
    artifacts["_df_cache"] = df
    artifacts["_theme_cache"] = theme

    layout = load_or_create_layout(
        workbook_id=workbook_id,
        sheet_id=sheet_id,
        dashboard_id=dashboard_id,
        theme=theme_name,
        artifacts=artifacts,
    )
    engine = CanvasEngine(layout, container_width_px=container_width_px)
    dims = engine.dimensions()
    canvas_state = st.session_state.get("canvas_state", {}).get("active", {})
    grid_visible = bool(canvas_state.get("grid_visible", True))

    dataset_id = f"{workbook_id}::{sheet_id}"
    bridge = DashboardWidgetBridge()
    widgets = bridge.build_from_layout(
        layout,
        dataset_id=dataset_id,
        dataframe=df,
        theme=theme_name,
        mode_key=dashboard_id,
    )

    inject_canvas_styles()
    started = time.perf_counter()
    st.markdown(
        f'<div class="dashboard-canvas" style="{css_grid_style(layout.grid, dims.effective_columns, dims.total_rows)}">',
        unsafe_allow_html=True,
    )

    context_bundle = dict(artifacts)
    for placement in sorted_render_groups(layout.widgets):
        st.markdown(
            f'<div style="{placement_style(placement, dims.effective_columns)}">',
            unsafe_allow_html=True,
        )
        widget = bridge.controller.get(placement.widget_id)
        if widget is not None:
            from widgets.renderer import RenderContext

            bridge.renderer.render(
                widget,
                RenderContext(
                    dataset_registry=bridge.dataset_registry,
                    artifacts=context_bundle,
                    theme=theme,
                    dashboard_config=dashboard_config,
                    grid_visible=grid_visible,
                ),
            )
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
    engine.mark_render_complete((time.perf_counter() - started) * 1000)

    export_bundle = bridge.export_adapter.export_dashboard_bundle(widgets)
    decisions = bridge.evaluate_decisions(widgets, artifacts=artifacts, dataframe=df)
    executive_summary = bridge.executive_decision_summary(decisions)
    st.caption(
        f"Canvas grid: {dims.effective_columns} columns · {dims.total_rows} rows · "
        f"{len(widgets)} widgets · layout v{layout.version} · widget schema v3 · "
        f"{sum(1 for d in decisions if d.validated)}/{len(decisions)} validated decisions"
    )
    return {
        "layout": layout.to_dict(),
        "widgets": [widget.to_dict() for widget in widgets],
        "export_bundle": export_bundle,
        "decisions": serialize_decisions(decisions),
        "executive_decision_summary": executive_summary,
        "metrics": {
            "init_ms": engine.metrics.init_ms,
            "render_ms": engine.metrics.render_ms,
            "peak_memory_kb": engine.metrics.peak_memory_kb,
            "widget_count": len(widgets),
            "validation_issues": engine.metrics.validation_issues,
            "effective_columns": dims.effective_columns,
            "total_rows": dims.total_rows,
        },
    }
