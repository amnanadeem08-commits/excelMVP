"""Dashboard module: interactive Streamlit + Plotly UI building blocks.

Contains everything visual: page styling, KPI cards, sidebar filters, and
automatic chart generation (line, bar, pie, histogram, scatter, heatmap).

CUSTOMIZE:
- Change the color palette / fonts in ``inject_styles``.
- Add chart types in ``generate_charts``.
- Adjust how many filter widgets render in ``filter_dataframe``.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import plotly.express as px
import streamlit as st

from analytics_engine import categorical_dimensions, numeric_measures

PLOTLY_TEMPLATE = "plotly_white"


@dataclass
class ChartSpec:
    """A titled Plotly figure ready to render or export."""

    title: str
    figure: object


def _format(fig, title: str):
    fig.update_layout(
        title=title,
        template=PLOTLY_TEMPLATE,
        height=430,
        margin=dict(l=20, r=20, t=60, b=30),
        hovermode="x unified",
        legend_title_text="",
    )
    return fig


def generate_charts(df: pd.DataFrame, column_types: dict[str, list[str]]) -> list[ChartSpec]:
    """Build a smart set of charts based on the detected column types."""
    charts: list[ChartSpec] = []
    numeric_cols = numeric_measures(df, column_types)
    categorical_cols = categorical_dimensions(df, column_types)
    date_cols = [col for col in column_types.get("datetime", []) if col in df.columns]

    # Line charts: trends over time.
    for date_col in date_cols[:2]:
        for measure in numeric_cols[:2]:
            monthly = (
                df.assign(_month=pd.to_datetime(df[date_col], errors="coerce").dt.to_period("M").dt.to_timestamp())
                .dropna(subset=["_month"])
                .groupby("_month", as_index=False)[measure]
                .sum()
                .sort_values("_month")
            )
            if len(monthly) >= 2:
                title = f"Monthly {measure} Trend"
                fig = px.line(monthly, x="_month", y=measure, markers=True, labels={"_month": "Month"}, title=title)
                charts.append(ChartSpec(title, _format(fig, title)))

    # Bar / pie charts: top categories.
    for cat in categorical_cols[:4]:
        for measure in numeric_cols[:2]:
            aggregated = df.groupby(cat, as_index=False)[measure].sum().sort_values(measure, ascending=False).head(10)
            if aggregated.empty:
                continue
            orientation = "h" if aggregated[cat].astype(str).str.len().median() > 14 else "v"
            title = f"Top {cat} by {measure}"
            if orientation == "h":
                aggregated = aggregated.sort_values(measure, ascending=True)
                fig = px.bar(aggregated, x=measure, y=cat, orientation="h", title=title, text_auto=".2s")
            else:
                fig = px.bar(aggregated, x=cat, y=measure, title=title, text_auto=".2s")
            charts.append(ChartSpec(title, _format(fig, title)))

            if 2 <= df[cat].nunique(dropna=True) <= 6:
                pie_title = f"{measure} Share by {cat}"
                fig = px.pie(aggregated, names=cat, values=measure, hole=0.42, title=pie_title)
                charts.append(ChartSpec(pie_title, _format(fig, pie_title)))

    # Distributions.
    for measure in numeric_cols[:4]:
        if df[measure].nunique(dropna=True) > 5:
            title = f"{measure} Distribution"
            fig = px.histogram(df, x=measure, nbins=35, marginal="box", title=title)
            charts.append(ChartSpec(title, _format(fig, title)))

    # Relationship scatter.
    if len(numeric_cols) >= 2:
        x_col, y_col = numeric_cols[:2]
        title = f"{x_col} vs {y_col}"
        sample = df[[x_col, y_col]].dropna()
        if len(sample) > 0:
            if len(sample) > 3000:
                sample = sample.sample(3000, random_state=42)
            fig = px.scatter(sample, x=x_col, y=y_col, title=title)
            charts.append(ChartSpec(title, _format(fig, title)))

    # Correlation heatmap.
    if len(numeric_cols) >= 3:
        corr = df[numeric_cols[:12]].corr(numeric_only=True)
        title = "Correlation Heatmap"
        fig = px.imshow(corr, text_auto=".2f", aspect="auto", color_continuous_scale="RdBu_r", title=title)
        charts.append(ChartSpec(title, _format(fig, title)))

    return charts[:14]


# ---------------------------------------------------------------------------
# Streamlit UI helpers
# ---------------------------------------------------------------------------
def inject_styles() -> None:
    """Inject the client-friendly CSS theme."""
    st.markdown(
        """
        <style>
        :root {
            --surface: #ffffff;
            --surface-soft: #f8fafc;
            --card-bg: rgba(255,255,255,.92);
            --card-border: rgba(148, 163, 184, .28);
            --ink: #111827;
            --muted: #64748b;
            --accent: #2563eb;
            --accent-dark: #1d4ed8;
            --success: #059669;
            --warning: #d97706;
        }
        .stApp {
            background:
                linear-gradient(135deg, rgba(37,99,235,.10), transparent 28rem),
                linear-gradient(180deg, #f8fafc 0%, #eef2f7 100%);
            color: var(--ink);
            font-family: Inter, "Segoe UI", system-ui, -apple-system, sans-serif;
        }
        .block-container { padding-top: 1.3rem; padding-bottom: 2.4rem; max-width: 1480px; }
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0f172a 0%, #111827 100%);
            color: #fff;
            border-right: 1px solid rgba(255,255,255,.08);
        }
        [data-testid="stSidebar"] * { color: inherit; }
        [data-testid="stSidebar"] [data-testid="stFileUploader"] {
            border: 1px solid rgba(255,255,255,.16);
            background: rgba(255,255,255,.06);
            border-radius: 8px;
            padding: .55rem;
        }
        .hero { padding: 1.3rem 0 1.05rem; border-bottom: 1px solid rgba(148,163,184,.22); margin-bottom: .4rem; }
        .hero h1 { font-size: clamp(2rem, 4vw, 3.4rem); line-height: 1.05; margin: 0; color: var(--ink); }
        .hero p { color: var(--muted); font-size: 1.05rem; margin-top: .65rem; max-width: 58rem; }
        .metric-card {
            border: 1px solid var(--card-border);
            background: var(--card-bg);
            border-radius: 8px;
            padding: 1rem 1.1rem;
            box-shadow: 0 12px 32px rgba(15,23,42,.08);
            min-height: 112px;
        }
        .metric-card .label { color: var(--muted); font-size: .82rem; text-transform: uppercase; letter-spacing: .08em; }
        .metric-card .value { color: var(--ink); font-size: 1.85rem; font-weight: 750; margin-top: .3rem; overflow-wrap: anywhere; }
        .metric-card .note { color: var(--muted); font-size: .9rem; margin-top: .2rem; }
        .section-title { font-size: 1.35rem; font-weight: 760; margin: 1.55rem 0 .7rem; color: var(--ink); }
        .insight {
            border-left: 4px solid #2563eb;
            background: rgba(255,255,255,.88);
            border-radius: 8px;
            padding: .8rem 1rem;
            margin-bottom: .65rem;
            color: #1d2939;
            box-shadow: 0 8px 24px rgba(15,23,42,.05);
        }
        .warning { border-left-color: #f97316; }
        div[data-testid="stDataFrame"] {
            border: 1px solid rgba(148,163,184,.28);
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 10px 26px rgba(15,23,42,.05);
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: .35rem;
            background: rgba(255,255,255,.78);
            border: 1px solid rgba(148,163,184,.24);
            border-radius: 8px;
            padding: .35rem;
        }
        .stTabs [data-baseweb="tab"] { border-radius: 7px; color: #475569; font-weight: 650; padding: .6rem .85rem; }
        .stTabs [aria-selected="true"] { background: #111827; color: #ffffff; }
        div[data-testid="stFileUploader"] {
            background: rgba(255,255,255,.92);
            border: 1px dashed rgba(37,99,235,.42);
            border-radius: 8px;
            padding: .65rem;
        }
        .stButton > button, .stDownloadButton > button {
            background: linear-gradient(180deg, var(--accent), var(--accent-dark));
            color: #ffffff;
            border: 0;
            border-radius: 8px;
            padding: .62rem 1rem;
            font-weight: 700;
            box-shadow: 0 8px 18px rgba(37,99,235,.24);
            transition: transform .12s ease, box-shadow .12s ease, background .12s ease;
        }
        .stButton > button:hover, .stDownloadButton > button:hover {
            color: #ffffff;
            background: linear-gradient(180deg, #1d4ed8, #1e40af);
            border: 0;
            transform: translateY(-1px);
            box-shadow: 0 12px 24px rgba(37,99,235,.30);
        }
        .stButton > button:active, .stDownloadButton > button:active,
        .stButton > button:focus, .stDownloadButton > button:focus {
            color: #ffffff; border: 0; outline: 2px solid rgba(37,99,235,.24);
        }
        div[role="radiogroup"] {
            background: rgba(255,255,255,.86);
            border: 1px solid rgba(148,163,184,.28);
            border-radius: 8px;
            padding: .45rem .65rem;
        }
        div[role="radiogroup"] label { color: #334155; font-weight: 650; }
        .stAlert { border-radius: 8px; }
        h1, h2, h3, p, label { letter-spacing: 0; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_card(label: str, value: str, note: str = "") -> None:
    """Render a single KPI metric card."""
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="label">{label}</div>
            <div class="value">{value}</div>
            <div class="note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metric_cards(kpis: dict[str, dict[str, str]]) -> None:
    """Render a responsive grid of KPI cards."""
    cols = st.columns(min(4, max(1, len(kpis))))
    for idx, (label, metric) in enumerate(kpis.items()):
        with cols[idx % len(cols)]:
            render_card(label, metric["value"], metric.get("note", ""))


def render_charts(charts: list[ChartSpec]) -> None:
    """Render all charts in the dashboard."""
    if not charts:
        st.warning("No valid chart combinations were detected for this dataset.")
        return
    for chart in charts:
        st.plotly_chart(chart.figure, use_container_width=True)


def filter_dataframe(df: pd.DataFrame, column_types: dict[str, list[str]]) -> pd.DataFrame:
    """Render sidebar filters (category + date) and return the filtered data."""
    filtered = df.copy()
    st.sidebar.header("Filters")

    categorical = column_types.get("categorical", []) + column_types.get("boolean", [])
    for column in categorical[:8]:
        values = sorted([str(v) for v in filtered[column].dropna().unique()])[:250]
        if not values:
            continue
        selected = st.sidebar.multiselect(column, values, default=values)
        if selected:
            filtered = filtered[filtered[column].astype(str).isin(selected)]

    for column in column_types.get("datetime", [])[:3]:
        series = pd.to_datetime(filtered[column], errors="coerce").dropna()
        if series.empty:
            continue
        start, end = series.min().date(), series.max().date()
        picked = st.sidebar.date_input(column, value=(start, end), min_value=start, max_value=end)
        if isinstance(picked, tuple) and len(picked) == 2:
            filtered = filtered[
                (pd.to_datetime(filtered[column], errors="coerce").dt.date >= picked[0])
                & (pd.to_datetime(filtered[column], errors="coerce").dt.date <= picked[1])
            ]

    return filtered
