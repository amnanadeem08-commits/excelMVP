"""Renderers for Smart Dashboard Modes."""

from __future__ import annotations

import re
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from ai_insights import generate_ai_insights
from analytics_engine import (
    analyze_dataset,
    best_numeric_column,
    build_kpis,
    categorical_dimensions,
    generate_pivot_tables,
    numeric_measures,
)
from dashboard import (
    ChartSpec,
    filter_dataframe,
    generate_charts,
    get_default_theme,
    render_card,
    render_charts,
    render_metric_cards,
)
from data_cleaning import detect_column_types
from forecasting.simple_forecast import ForecastResult, simple_date_forecast
from canvas.renderer import render_dashboard_canvas
from insights.click_insights import render_explain_button

from .mode_config import DASHBOARD_MODES, DEFAULT_MODE, MODE_ORDER, get_mode


FINANCIAL_KEYWORDS = {
    "revenue": ["revenue", "sales", "income", "amount", "total", "net sales"],
    "cost": ["cost", "expense", "cogs", "spend", "paid", "charge"],
    "profit": ["profit", "margin", "gross profit", "net profit", "earnings"],
}

OPERATIONAL_KEYWORDS = {
    "volume": ["quantity", "qty", "units", "volume", "count", "orders", "tickets", "transactions"],
    "inventory": ["stock", "inventory", "on hand", "available", "reorder"],
    "customer": ["customer", "client", "account", "user"],
    "process": ["status", "stage", "priority", "fulfillment", "delivery", "lead time", "duration", "cycle"],
}


def render_mode_selector(default_mode: str = DEFAULT_MODE) -> str:
    """Render card-like mode descriptions plus a radio selector."""
    current = st.session_state.get("smart_dashboard_mode", default_mode)
    if current not in DASHBOARD_MODES:
        current = default_mode

    st.subheader("Smart Dashboard Modes")
    cols = st.columns(4)
    for col, key in zip(cols, MODE_ORDER):
        mode = DASHBOARD_MODES[key]
        with col:
            active = "Active" if key == current else mode.audience
            st.markdown(f"**{mode.label}**")
            st.caption(f"{mode.description} Best for {mode.audience.lower()}.")
            st.caption(active)

    labels = [DASHBOARD_MODES[key].label for key in MODE_ORDER]
    selected_label = st.radio(
        "Choose dashboard mode",
        labels,
        index=MODE_ORDER.index(current),
        horizontal=True,
        key="smart_dashboard_mode_label",
    )
    selected_key = MODE_ORDER[labels.index(selected_label)]
    st.session_state["smart_dashboard_mode"] = selected_key
    return selected_key


def prepare_mode_artifacts(
    df: pd.DataFrame,
    mode_key: str,
    *,
    column_types: dict[str, list[str]] | None = None,
    theme: dict | None = None,
    base_charts: list[ChartSpec] | None = None,
    base_pivots: list[Any] | None = None,
    base_ai: dict | None = None,
) -> dict[str, Any]:
    """Build mode-aware artifacts that can also feed exports."""
    theme = theme or get_default_theme()
    column_types = column_types or detect_column_types(df)
    summary = analyze_dataset(df, column_types)
    kpis = build_kpis(df, summary, column_types)
    charts = list(base_charts) if base_charts is not None else generate_charts(df, column_types, theme)
    pivots = list(base_pivots) if base_pivots is not None else generate_pivot_tables(df, column_types)
    ai = base_ai or generate_ai_insights(df, column_types)
    insights = list(ai.get("key_insights", []))
    recommendations = list(ai.get("recommendations", []))

    mode = get_mode(mode_key)
    if mode.key == "executive":
        charts = _priority_charts(charts, ["trend", "top", "share"])[: mode.chart_limit or 2]
        pivots = []
        insights = insights[:5]
        kpis = dict(list(kpis.items())[:6])
    elif mode.key == "financial":
        financial = _financial_context(df, column_types, theme)
        kpis = {**kpis, **financial["kpis"]}
        if financial["charts"]:
            charts = financial["charts"] + _priority_charts(charts, ["monthly", "trend", "correlation"])[:3]
        else:
            charts = _priority_charts(charts, ["monthly", "trend", "correlation"])[: mode.chart_limit or 6]
        insights = financial["insights"] + insights[:3]
    elif mode.key == "operational":
        operational = _operational_context(df, column_types)
        kpis = {**kpis, **operational["kpis"]}
        insights = operational["insights"] + insights[:3]
        charts = _priority_charts(charts, ["top", "distribution", "record count", "vs"])[: mode.chart_limit or 6]
    else:
        charts = charts[: mode.chart_limit] if mode.chart_limit else charts

    return {
        "mode": mode,
        "summary": summary,
        "kpis": kpis,
        "charts": charts,
        "pivots": pivots if mode.include_pivots else [],
        "insights": insights[:8],
        "recommendations": recommendations[:8],
        "column_types": column_types,
    }


def render_smart_dashboard(
    df: pd.DataFrame,
    *,
    mode_key: str,
    column_types: dict[str, list[str]] | None = None,
    theme: dict | None = None,
    charts: list[ChartSpec] | None = None,
    pivots: list[Any] | None = None,
    ai: dict | None = None,
    dashboard_config: dict[str, Any] | None = None,
    workbook_id: str = "",
    sheet_id: str = "",
) -> dict[str, Any]:
    """Dispatch to the canvas renderer and return export artifacts."""
    artifacts = prepare_mode_artifacts(
        df,
        mode_key,
        column_types=column_types,
        theme=theme,
        base_charts=charts,
        base_pivots=pivots,
        base_ai=ai,
    )

    render_dashboard_canvas(
        df,
        workbook_id=workbook_id or "workbook",
        sheet_id=sheet_id or "sheet",
        dashboard_id=artifacts["mode"].key,
        theme=theme,
        artifacts=artifacts,
        dashboard_config=dashboard_config,
    )
    return artifacts


def render_executive_dashboard(
    df: pd.DataFrame,
    *,
    artifacts: dict[str, Any] | None = None,
    theme: dict | None = None,
    dashboard_config: dict[str, Any] | None = None,
) -> None:
    """Executive dashboard: KPIs, short insights, minimal charts."""
    artifacts = artifacts or prepare_mode_artifacts(df, "executive", theme=theme)
    st.markdown("#### Executive Dashboard")
    st.caption("KPIs and short business signals for owners, CEOs, and managers.")
    _render_kpis_with_explain(df, artifacts["kpis"], mode="Executive")

    st.markdown("#### Summary Insights")
    for item in artifacts["insights"][:5]:
        st.info(item)

    if artifacts["charts"]:
        st.markdown("#### Minimal Visuals")
        render_charts(
            artifacts["charts"],
            theme or get_default_theme(),
            two_column=True,
            max_charts=2,
            dashboard_config=dashboard_config,
        )
        for idx, chart in enumerate(artifacts["charts"][:2]):
            render_explain_button(f"exec-chart-{idx}", df, chart.title, mode="Executive", chart_type="chart")


def render_analytical_dashboard(
    df: pd.DataFrame,
    *,
    artifacts: dict[str, Any] | None = None,
    theme: dict | None = None,
    dashboard_config: dict[str, Any] | None = None,
) -> None:
    """Analytical dashboard: full charts, filters, pivots, and exploration."""
    artifacts = artifacts or prepare_mode_artifacts(df, "analytical", theme=theme)
    st.markdown("#### Analytical Dashboard")
    st.caption("Full chart set, pivot tables, and drill-down style exploration for analysts.")
    render_metric_cards(artifacts["kpis"], theme or get_default_theme())
    render_explain_button("analytical-kpis", df, "Analytical KPI set", mode="Analytical")

    st.markdown("#### Detailed Charts")
    render_charts(
        artifacts["charts"],
        theme or get_default_theme(),
        two_column=True,
        dashboard_config=dashboard_config,
    )
    if artifacts["charts"]:
        selected = st.selectbox("Explain chart", [chart.title for chart in artifacts["charts"]], key="analytical-chart-explain")
        render_explain_button("analytical-chart", df, selected, mode="Analytical", chart_type="chart")

    st.markdown("#### Pivot Tables")
    if not artifacts["pivots"]:
        st.info("No valid pivot tables were generated from the available columns.")
    for pivot in artifacts["pivots"][:8]:
        with st.expander(pivot.title):
            st.dataframe(pivot.data, use_container_width=True, hide_index=True)

    st.markdown("#### Data Explorer")
    st.dataframe(df.head(300), use_container_width=True)


def render_financial_dashboard(
    df: pd.DataFrame,
    *,
    artifacts: dict[str, Any] | None = None,
    theme: dict | None = None,
    dashboard_config: dict[str, Any] | None = None,
) -> None:
    """Financial dashboard: revenue, cost, profit, margins, trends, forecast."""
    theme = theme or get_default_theme()
    artifacts = artifacts or prepare_mode_artifacts(df, "financial", theme=theme)
    column_types = artifacts["column_types"]
    context = _financial_context(df, column_types, theme)

    st.markdown("#### Financial Dashboard")
    st.caption("Revenue, cost, profit, margin, trends, and simple forecasts when the data supports them.")
    if context["fallback"]:
        st.warning(context["fallback"])

    _render_kpis_with_explain(df, artifacts["kpis"], mode="Financial")
    for item in context["insights"]:
        st.info(item)

    if context["forecast"].ok:
        st.markdown("#### Forecast")
        st.plotly_chart(_forecast_figure(context["forecast"], theme), use_container_width=True)
        render_explain_button(
            "financial-forecast",
            df,
            "Simple financial forecast",
            column=context["forecast"].value_column,
            mode="Financial",
            chart_type="forecast",
        )
    elif context["forecast"].message:
        st.info(context["forecast"].message)

    if artifacts["charts"]:
        st.markdown("#### Financial Trends")
        render_charts(
            artifacts["charts"],
            theme,
            two_column=True,
            max_charts=6,
            focus="Finance",
            dashboard_config=dashboard_config,
        )


def render_operational_dashboard(
    df: pd.DataFrame,
    *,
    artifacts: dict[str, Any] | None = None,
    theme: dict | None = None,
    dashboard_config: dict[str, Any] | None = None,
) -> None:
    """Operational dashboard: volume, usage, inventory, customers, process signals."""
    theme = theme or get_default_theme()
    artifacts = artifacts or prepare_mode_artifacts(df, "operational", theme=theme)
    context = _operational_context(df, artifacts["column_types"])

    st.markdown("#### Operational Dashboard")
    st.caption("Volume, activity, inventory, customer, and process signals for operations managers.")
    if context["fallback"]:
        st.info(context["fallback"])

    _render_kpis_with_explain(df, artifacts["kpis"], mode="Operational")
    for item in context["insights"]:
        st.info(item)

    if artifacts["charts"]:
        st.markdown("#### Operational Charts")
        render_charts(
            artifacts["charts"],
            theme,
            two_column=True,
            max_charts=6,
            focus="Operations",
            dashboard_config=dashboard_config,
        )

    if artifacts["pivots"]:
        st.markdown("#### Operational Breakdowns")
        for pivot in artifacts["pivots"][:4]:
            with st.expander(pivot.title):
                st.dataframe(pivot.data, use_container_width=True, hide_index=True)


def _render_kpis_with_explain(df: pd.DataFrame, kpis: dict[str, dict[str, str]], *, mode: str) -> None:
    cols = st.columns(min(3, max(1, len(kpis))))
    for idx, (label, metric) in enumerate(kpis.items()):
        with cols[idx % len(cols)]:
            render_card(label, metric["value"], metric.get("note", ""))
            render_explain_button(
                f"{mode.lower()}-kpi-{idx}-{_slug(label)}",
                df,
                label,
                metric_value=metric.get("value"),
                mode=mode,
            )


def _priority_charts(charts: list[ChartSpec], keywords: list[str]) -> list[ChartSpec]:
    def score(item: tuple[int, ChartSpec]) -> tuple[int, int]:
        index, chart = item
        title = chart.title.lower()
        return (-sum(1 for word in keywords if word in title), index)

    return [chart for _, chart in sorted(enumerate(charts), key=score)]


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _find_column(df: pd.DataFrame, keywords: list[str], numeric_only: bool = False) -> str | None:
    for keyword in keywords:
        for column in df.columns:
            if keyword in str(column).lower():
                if numeric_only and not pd.api.types.is_numeric_dtype(df[column]):
                    continue
                return column
    return None


def _financial_context(df: pd.DataFrame, column_types: dict[str, list[str]], theme: dict) -> dict[str, Any]:
    revenue_col = _find_column(df, FINANCIAL_KEYWORDS["revenue"], numeric_only=True) or best_numeric_column(df, column_types)
    cost_col = _find_column(df, FINANCIAL_KEYWORDS["cost"], numeric_only=True)
    profit_col = _find_column(df, FINANCIAL_KEYWORDS["profit"], numeric_only=True)
    date_cols = [col for col in column_types.get("datetime", []) if col in df.columns]
    kpis: dict[str, dict[str, str]] = {}
    insights: list[str] = []
    charts: list[ChartSpec] = []
    fallback = ""

    if revenue_col:
        revenue = float(pd.to_numeric(df[revenue_col], errors="coerce").fillna(0).sum())
        kpis["Revenue"] = {"value": f"{revenue:,.2f}", "note": revenue_col}
        insights.append(f"Revenue is calculated from {revenue_col} and totals {revenue:,.2f}.")
    if cost_col:
        cost = float(pd.to_numeric(df[cost_col], errors="coerce").fillna(0).sum())
        kpis["Cost"] = {"value": f"{cost:,.2f}", "note": cost_col}
    if profit_col:
        profit = float(pd.to_numeric(df[profit_col], errors="coerce").fillna(0).sum())
    elif revenue_col and cost_col:
        profit = float(pd.to_numeric(df[revenue_col], errors="coerce").fillna(0).sum()) - float(
            pd.to_numeric(df[cost_col], errors="coerce").fillna(0).sum()
        )
    else:
        profit = None
    if profit is not None:
        kpis["Profit"] = {"value": f"{profit:,.2f}", "note": profit_col or "Revenue - Cost"}
        if revenue_col:
            revenue_total = float(pd.to_numeric(df[revenue_col], errors="coerce").fillna(0).sum())
            margin = (profit / revenue_total * 100) if revenue_total else 0
            kpis["Margin"] = {"value": f"{margin:.1f}%", "note": "Profit / Revenue"}
            insights.append(f"Estimated margin is {margin:.1f}% based on available financial columns.")

    if not revenue_col and not profit_col:
        fallback = "Financial mode needs a revenue, sales, amount, profit, or margin-style numeric column. The dataset does not clearly contain one."

    forecast = ForecastResult(False, "", pd.DataFrame(), pd.DataFrame())
    forecast_value = profit_col or revenue_col
    if date_cols and forecast_value:
        forecast = simple_date_forecast(df, date_cols[0], forecast_value)
        if forecast.ok:
            charts.append(ChartSpec(f"{forecast_value} Forecast", _forecast_figure(forecast, theme)))
    elif forecast_value:
        forecast = ForecastResult(False, "Forecast skipped: no valid date column was detected.", pd.DataFrame(), pd.DataFrame())

    return {"kpis": kpis, "insights": insights, "charts": charts, "forecast": forecast, "fallback": fallback}


def _forecast_figure(result: ForecastResult, theme: dict):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=result.history["date"], y=result.history["actual"], mode="lines+markers", name="Actual"))
    fig.add_trace(go.Scatter(x=result.forecast["date"], y=result.forecast["forecast"], mode="lines+markers", name="Forecast"))
    fig.update_layout(
        title=result.message,
        template="plotly_white",
        height=430,
        colorway=theme["palette"],
        margin=dict(l=20, r=20, t=60, b=30),
        hovermode="x unified",
    )
    return fig


def _operational_context(df: pd.DataFrame, column_types: dict[str, list[str]]) -> dict[str, Any]:
    volume_col = _find_column(df, OPERATIONAL_KEYWORDS["volume"], numeric_only=True)
    inventory_col = _find_column(df, OPERATIONAL_KEYWORDS["inventory"], numeric_only=True)
    customer_col = _find_column(df, OPERATIONAL_KEYWORDS["customer"], numeric_only=False)
    process_col = _find_column(df, OPERATIONAL_KEYWORDS["process"], numeric_only=False)

    kpis: dict[str, dict[str, str]] = {}
    insights: list[str] = []
    fallback = ""

    if volume_col:
        total = float(pd.to_numeric(df[volume_col], errors="coerce").fillna(0).sum())
        kpis["Volume"] = {"value": f"{total:,.0f}", "note": volume_col}
        insights.append(f"Operational volume from {volume_col} totals {total:,.0f}.")
    else:
        kpis["Records"] = {"value": f"{len(df):,}", "note": "Operational activity count"}

    if inventory_col:
        stock = pd.to_numeric(df[inventory_col], errors="coerce").dropna()
        if not stock.empty:
            kpis["Avg Stock"] = {"value": f"{stock.mean():,.1f}", "note": inventory_col}
            low_threshold = stock.quantile(0.15)
            low_count = int((stock <= low_threshold).sum())
            insights.append(f"{low_count:,} record(s) sit in the low-stock band for {inventory_col}.")

    if customer_col:
        active = int(df[customer_col].nunique(dropna=True))
        kpis["Customers"] = {"value": f"{active:,}", "note": customer_col}
        insights.append(f"{customer_col} has {active:,} unique value(s), useful for activity concentration checks.")

    if process_col:
        top = df[process_col].astype(str).value_counts(dropna=False).head(1)
        if not top.empty:
            kpis["Top Status"] = {"value": str(top.index[0])[:18], "note": process_col}
            insights.append(f"{process_col} is led by '{top.index[0]}', appearing {int(top.iloc[0]):,} time(s).")

    if not any([volume_col, inventory_col, customer_col, process_col]):
        fallback = "Operational mode did not find clear order, quantity, inventory, customer, status, or process columns. Showing general activity signals instead."

    return {"kpis": kpis, "insights": insights, "fallback": fallback}
