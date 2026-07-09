"""Widget renderer: presentation only, no business logic."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

import pandas as pd
import streamlit as st

from widgets.base import BaseWidget
from widgets.databinding import DatasetRegistry, resolve_dataset
from widgets.events import EventBus


RenderCallable = Callable[[BaseWidget, "RenderContext"], None]


@dataclass
class RenderContext:
    dataset_registry: DatasetRegistry
    artifacts: dict[str, Any] = field(default_factory=dict)
    theme: dict[str, Any] | None = None
    dashboard_config: dict[str, Any] | None = None
    grid_visible: bool = True
    render_target: str = "dashboard"
    deferred: bool = False


class WidgetRenderer:
    """Render widgets to multiple targets while keeping logic isolated."""

    def __init__(self, event_bus: EventBus | None = None) -> None:
        self.event_bus = event_bus or EventBus()
        self._renderers: dict[str, RenderCallable] = {}
        self._register_builtin_renderers()

    def register(self, widget_type: str, renderer: RenderCallable) -> None:
        self._renderers[widget_type] = renderer

    def can_render(self, widget: BaseWidget, target: str = "dashboard") -> bool:
        legacy = widget.widget_metadata.legacy_type or widget.widget_type
        return target == "dashboard" and (widget.widget_type in self._renderers or legacy in _LEGACY_RENDERERS)

    def render(self, widget: BaseWidget, context: RenderContext) -> None:
        if not widget.widget_state.visible:
            return
        if context.deferred and widget.widget_type in {"chart", "table", "pivot"}:
            st.caption(f"{widget.widget_title or widget.widget_name} (deferred)")
            return

        widget.before_render({"target": context.render_target})
        dataset = resolve_dataset(widget.data_binding, context.dataset_registry)
        context.artifacts["_resolved_dataset"] = dataset

        renderer = self._resolve_renderer(widget)
        if renderer is None:
            st.caption(f"No renderer for widget type: {widget.widget_type}")
        else:
            if context.render_target == "dashboard":
                st.markdown(
                    f'<div class="canvas-widget" data-grid-visible="{str(context.grid_visible).lower()}">',
                    unsafe_allow_html=True,
                )
                renderer(widget, context)
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                renderer(widget, context)

        widget.after_render({"target": context.render_target})
        self.event_bus.emit("widget_refreshed", widget.widget_id, target=context.render_target)

    def render_many(self, widgets: list[BaseWidget], context: RenderContext) -> None:
        visible = [widget for widget in widgets if widget.widget_state.visible]
        for widget in sorted(visible, key=lambda item: (item.placement.row, item.placement.col, item.placement.z_index)):
            self.render(widget, context)

    def _resolve_renderer(self, widget: BaseWidget) -> RenderCallable | None:
        if widget.widget_type in self._renderers:
            return self._renderers[widget.widget_type]
        legacy = widget.widget_metadata.legacy_type
        if legacy in _LEGACY_RENDERERS:
            return _LEGACY_RENDERERS[legacy]
        return None

    def _register_builtin_renderers(self) -> None:
        self.register("text", _render_text_widget)
        self.register("kpi", _render_kpi_widget)
        self.register("chart", _render_chart_widget)
        self.register("table", _render_table_widget)
        self.register("pivot", _render_pivot_widget)
        self.register("image", _render_image_widget)
        self.register("logo", _render_logo_widget)
        self.register("divider", _render_divider_widget)
        self.register("shape", _render_shape_widget)


_LEGACY_RENDERERS: dict[str, RenderCallable] = {}


def _legacy_renderer(legacy_type: str) -> Callable[[RenderCallable], None]:
    def decorator(func: RenderCallable) -> RenderCallable:
        _LEGACY_RENDERERS[legacy_type] = func
        return func

    return decorator


@_legacy_renderer("section_header")
def _render_section_header_legacy(widget: BaseWidget, context: RenderContext) -> None:
    _render_text_widget(widget, context)


@_legacy_renderer("kpi_grid")
def _render_kpi_grid_legacy(widget: BaseWidget, context: RenderContext) -> None:
    _render_kpi_widget(widget, context)


@_legacy_renderer("insight_list")
def _render_insight_list_legacy(widget: BaseWidget, context: RenderContext) -> None:
    _render_text_widget(widget, context)


@_legacy_renderer("chart_grid")
def _render_chart_grid_legacy(widget: BaseWidget, context: RenderContext) -> None:
    _render_chart_widget(widget, context)


@_legacy_renderer("pivot_list")
def _render_pivot_list_legacy(widget: BaseWidget, context: RenderContext) -> None:
    _render_pivot_widget(widget, context)


@_legacy_renderer("dataframe")
def _render_dataframe_legacy(widget: BaseWidget, context: RenderContext) -> None:
    _render_table_widget(widget, context)


@_legacy_renderer("forecast_chart")
def _render_forecast_legacy(widget: BaseWidget, context: RenderContext) -> None:
    _render_chart_widget(widget, context)


def _df(context: RenderContext) -> pd.DataFrame:
    if "_df_cache" in context.artifacts:
        frame = context.artifacts["_df_cache"]
        if isinstance(frame, pd.DataFrame):
            return frame
    if "_resolved_dataset" in context.artifacts:
        frame = context.artifacts["_resolved_dataset"]
        if isinstance(frame, pd.DataFrame):
            return frame
    return pd.DataFrame()


def _render_text_widget(widget: BaseWidget, context: RenderContext) -> None:
    settings = widget.widget_settings
    variant = settings.get("variant", "text")
    artifacts = context.artifacts
    if variant == "header":
        title = settings.get("title") or artifacts["mode"].label
        caption = settings.get("caption") or artifacts["mode"].description
        st.markdown(f"#### {title}")
        st.caption(caption)
        mode_key = artifacts["mode"].key
        df = _df(context)
        theme = context.theme or artifacts.get("_theme_cache", {})
        if mode_key == "financial":
            from dashboard_modes.renderers import _financial_context

            ctx = _financial_context(df, artifacts["column_types"], theme)
            if ctx["fallback"]:
                st.warning(ctx["fallback"])
        elif mode_key == "operational":
            from dashboard_modes.renderers import _operational_context

            ctx = _operational_context(df, artifacts["column_types"])
            if ctx["fallback"]:
                st.info(ctx["fallback"])
    elif variant == "insights":
        st.markdown("#### Summary Insights")
        for item in artifacts.get("insights", [])[: int(settings.get("count", 5))]:
            st.info(item)
    else:
        st.markdown(widget.widget_title or settings.get("title", "Text"))


def _render_kpi_widget(widget: BaseWidget, context: RenderContext) -> None:
    from dashboard_modes.renderers import _render_kpis_with_explain
    from insights.click_insights import render_explain_button

    artifacts = context.artifacts
    df = _df(context)
    mode_label = artifacts["mode"].label.split()[0]
    _render_kpis_with_explain(df, artifacts["kpis"], mode=mode_label)
    if artifacts["mode"].key == "analytical":
        render_explain_button("analytical-kpis", df, "Analytical KPI set", mode="Analytical")


def _render_chart_widget(widget: BaseWidget, context: RenderContext) -> None:
    from dashboard import render_charts
    from insights.click_insights import render_explain_button

    artifacts = context.artifacts
    df = _df(context)
    theme = context.theme or artifacts.get("_theme_cache", {})
    settings = widget.widget_settings
    mode_key = artifacts["mode"].key

    if settings.get("variant") == "forecast":
        from dashboard_modes.renderers import _financial_context, _forecast_figure

        forecast = _financial_context(df, artifacts["column_types"], theme)["forecast"]
        if forecast.ok:
            st.markdown("#### Forecast")
            st.plotly_chart(_forecast_figure(forecast, theme), use_container_width=True)
            render_explain_button(
                "financial-forecast-canvas",
                df,
                "Simple financial forecast",
                column=forecast.value_column,
                mode="Financial",
                chart_type="forecast",
            )
        elif forecast.message:
            st.info(forecast.message)
        return

    title = "Minimal Visuals" if mode_key == "executive" else "Detailed Charts"
    if mode_key == "financial":
        title = "Financial Trends"
    elif mode_key == "operational":
        title = "Operational Charts"
    st.markdown(f"#### {title}")

    charts = artifacts.get("charts", [])
    count = int(settings.get("count", len(charts)))
    render_charts(
        charts,
        theme,
        two_column=bool(settings.get("two_column", True)),
        max_charts=count,
        dashboard_config=context.dashboard_config,
    )
    if mode_key == "executive":
        for idx, chart in enumerate(charts[:2]):
            render_explain_button(f"exec-chart-{idx}", df, chart.title, mode="Executive", chart_type="chart")
    elif mode_key == "analytical" and charts:
        selected = st.selectbox("Explain chart", [chart.title for chart in charts], key="analytical-chart-explain")
        render_explain_button("analytical-chart", df, selected, mode="Analytical", chart_type="chart")


def _render_table_widget(widget: BaseWidget, context: RenderContext) -> None:
    title = widget.widget_settings.get("title", "Data Explorer")
    st.markdown(f"#### {title}")
    st.dataframe(_df(context).head(300), use_container_width=True)


def _render_pivot_widget(widget: BaseWidget, context: RenderContext) -> None:
    artifacts = context.artifacts
    title = "Operational Breakdowns" if artifacts["mode"].key == "operational" else "Pivot Tables"
    st.markdown(f"#### {title}")
    pivots = artifacts.get("pivots", [])
    if not pivots:
        st.info("No valid pivot tables were generated from the available columns.")
        return
    for pivot in pivots[: int(widget.widget_settings.get("count", 8))]:
        with st.expander(pivot.title):
            st.dataframe(pivot.data, use_container_width=True, hide_index=True)


def _render_image_widget(widget: BaseWidget, context: RenderContext) -> None:
    st.caption(widget.widget_title or "Image widget")
    st.info("Image widget ready for asset binding.")


def _render_logo_widget(widget: BaseWidget, context: RenderContext) -> None:
    st.caption(widget.widget_title or "Company Logo")


def _render_divider_widget(widget: BaseWidget, context: RenderContext) -> None:
    st.divider()


def _render_shape_widget(widget: BaseWidget, context: RenderContext) -> None:
    st.markdown("---")
