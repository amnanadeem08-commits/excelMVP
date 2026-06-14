"""Click-based KPI and chart explanations for Smart Dashboard Modes."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st


def _format_value(value: Any) -> str:
    if value is None:
        return "not available"
    if isinstance(value, (int, float)):
        return f"{value:,.2f}"
    return str(value)


def build_click_insight(
    df: pd.DataFrame,
    title: str,
    *,
    metric_value: Any = None,
    column: str | None = None,
    mode: str | None = None,
    chart_type: str | None = None,
) -> dict[str, str]:
    """Return a rule-based explanation for a clicked KPI or chart.

    The language stays grounded in the available data. When a column is missing
    or insufficient, the explanation says so directly.
    """
    rows = len(df)
    section = title.strip() or "Selected item"
    value_text = _format_value(metric_value)

    if rows == 0:
        return {
            "means": f"{section} is meant to summarize part of the uploaded dataset.",
            "data_says": "The filtered dataset has no rows, so there is not enough data to interpret this item.",
            "matters": "Decisions based on an empty slice can be misleading.",
            "next_action": "Relax filters or upload a dataset with valid records, then review this metric again.",
        }

    data_says = f"The current filtered dataset contains {rows:,} records."
    if column and column in df.columns:
        series = df[column]
        if pd.api.types.is_numeric_dtype(series):
            data_says = (
                f"{column} has total {series.sum():,.2f}, average {series.mean():,.2f}, "
                f"and {series.notna().sum():,} valid values."
            )
        else:
            top = series.astype(str).value_counts(dropna=False).head(1)
            if not top.empty:
                data_says = f"{column} is led by '{top.index[0]}', appearing {int(top.iloc[0]):,} time(s)."
    elif metric_value is not None:
        data_says = f"The current value shown for this item is {value_text}."

    if column and column not in df.columns:
        data_says = f"The column '{column}' is not available in this dataset, so this item cannot be explained from data."

    chart_label = f" {chart_type}" if chart_type else ""
    mode_label = f" in {mode} mode" if mode else ""
    return {
        "means": f"{section} is a{chart_label} signal{mode_label} used to simplify what the dataset is showing.",
        "data_says": data_says,
        "matters": "It helps the user separate important movement or concentration from raw spreadsheet detail.",
        "next_action": "Compare this signal against the related pivot table or chart, then decide whether to investigate the leading segment, trend, or data quality issue.",
    }


def render_explain_button(
    key: str,
    df: pd.DataFrame,
    title: str,
    *,
    metric_value: Any = None,
    column: str | None = None,
    mode: str | None = None,
    chart_type: str | None = None,
) -> None:
    """Render a button and explanation panel for a KPI or chart."""
    if st.button("Why this matters", key=f"explain-{key}"):
        insight = build_click_insight(
            df,
            title,
            metric_value=metric_value,
            column=column,
            mode=mode,
            chart_type=chart_type,
        )
        st.markdown(f"**What it means:** {insight['means']}")
        st.markdown(f"**What the data says:** {insight['data_says']}")
        st.markdown(f"**Why it matters:** {insight['matters']}")
        st.markdown(f"**Recommended next action:** {insight['next_action']}")
