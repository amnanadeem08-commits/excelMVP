from __future__ import annotations

import math
import pandas as pd
import streamlit as st

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple


# COLOR_THEMES dict
COLOR_THEMES: dict[str, dict[str, str]] = {
    "Corporate Blue": {
        "primary": "#2563eb",
        "on_primary": "#ffffff",
        "secondary": "#0891b2",
        "on_secondary": "#ffffff",
        "tertiary": "#059669",
        "on_tertiary": "#ffffff",
        "accent": "#d97706",
        "on_accent": "#ffffff",
        "surface_soft": "#e0f2fe",
        "accent_light": "#f6e05e",
        "accent_dark": "#c2410c",
        "sidebar_from": "#0f172a",
        "sidebar_to": "#111827",
        "gradient_rgb": "37,99,235",
        "ink": "#1e293b",
        "muted": "#64748b",
        "surface_soft": "#e0f2fe",
        "palette": ["#2563eb", "#0891b2", "#059669", "#d97706", "#7c3aed"],
        "success": "#059669",
        "warning": "#f59e0b",
    },
    "Light": {
        "primary": "#1d4ed8",
        "on_primary": "#ffffff",
        "secondary": "#0f172a",
        "on_secondary": "#f8fafc",
        "tertiary": "#1e293b",
        "on_tertiary": "#f8fafc",
        "accent": "#f97316",
        "on_accent": "#ffffff",
        "surface_soft": "#f1f5f9",
        "accent_light": "#fbbf24",
        "accent_dark": "#b45309",
        "sidebar_from": "#1e293b",
        "sidebar_to": "#f1f5f9",
        "gradient_rgb": "29,78,216",
        "ink": "#0f172a",
        "muted": "#64748b",
        "surface_soft": "#f1f5f9",
        "palette": ["#1d4ed8", "#0f172a", "#1e293b", "#f97316", "#fbbf24"],
        "success": "#059669",
        "warning": "#f59e0b",
    },
    "Dark": {
        "accent": "#64748b",
        "on_accent": "#f8fafc",
        "accent_dark": "#475569",
        "sidebar_from": "#0f172a",
        "sidebar_to": "#1e293b",
        "gradient_rgb": "100,116,139",
        "ink": "#f1f5f9",
        "muted": "#94a3b8",
        "surface_soft": "#0f172a",
        "palette": ["#64748b", "#475569", "#1e293b", "#3b82f6", "#a5f3fc"],
        "success": "#10b981",
        "warning": "#f59e0b",
        "is_dark": True,
        "surface": "#0f172a",
        "card_bg": "#1e293b",
        "paper_bg": "#0f172a",
        "plot_bg": "#1e293b",
    },
    "Light Professional": {
        "primary": "#2563eb",
        "on_primary": "#ffffff",
        "secondary": "#64748b",
        "on_secondary": "#f8fafc",
        "tertiary": "#a5f3fc",
        "on_tertiary": "#0f172a",
        "accent": "#d97706",
        "on_accent": "#ffffff",
        "accent_dark": "#c2410c",
        "sidebar_from": "#0f172a",
        "sidebar_to": "#1e293b",
        "gradient_rgb": "37,99,235",
        "ink": "#1e293b",
        "muted": "#64748b",
        "surface_soft": "#e0f2fe",
        "palette": ["#2563eb", "#64748b", "#a5f3fc", "#d97706", "#f8fafc"],
        "success": "#10b981",
        "warning": "#f59e0b",
    },
    "Slate Minimal": {
        "primary": "#64748b",
        "on_primary": "#f8fafc",
        "secondary": "#94a3b8",
        "on_secondary": "#0f172a",
        "tertiary": "#e2e8f0",
        "on_tertiary": "#1e293b",
        "accent": "#f6e05e",
        "on_accent": "#1e293b",
        "accent_dark": "#e4e6eb",
        "sidebar_from": "#0f172a",
        "sidebar_to": "#1e293b",
        "gradient_rgb": "100,116,139",
        "ink": "#f8fafc",
        "muted": "#64748b",
        "surface_soft": "#f1f5f9",
        "palette": ["#64748b", "#94a3b8", "#e2e8f0", "#f6e05e", "#0f172a"],
        "success": "#10b981",
        "warning": "#f59e0b",
    },
}

import re

def _normalize_hex(color: str) -> str | None:
    """Return a valid #RRGGBB string or None."""
    if not color:
        return None
    color = color.strip()
    if re.fullmatch(r"#[0-9A-Fa-f]{6}", color):
        return color.lower()
    if re.fullmatch(r"[0-9A-Fa-f]{6}", color):
        return f"#{color.lower()}"
    if re.fullmatch(r"#[0-9A-Fa-f]{3}", color):
        h = color[1:]
        return f"#{h[0] * 2}{h[1] * 2}{h[2] * 2}".lower()
    return None


def _hex_to_rgb_tuple(hex_color: str) -> tuple[int, int, int]:
    h = _normalize_hex(hex_color) or "#2563eb"
    return int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)


def _rgb_string(hex_color: str) -> str:
    r, g, b = _hex_to_rgb_tuple(hex_color)
    return f"{r},{g},{b}"


def _darken_hex(hex_color: str, factor: float = 0.72) -> str:
    r, g, b = _hex_to_rgb_tuple(hex_color)
    return f"#{int(r * factor):02x}{int(g * factor):02x}{int(b * factor):02x}"


def _lighten_hex(hex_color: str, factor: float = 0.28) -> str:
    r, g, b = _hex_to_rgb_tuple(hex_color)
    return f"#{int(r + (255 - r) * factor):02x}{int(g + (255 - g) * factor):02x}{int(b + (255 - b) * factor):02x}"


def build_custom_theme(primary: str, secondary: str | None = None, tertiary: str | None = None) -> dict:
    """Build a full theme dict from 1-3 client hex colors."""
    primary = _normalize_hex(primary) or "#2563eb"
    secondary = _normalize_hex(secondary) or _lighten_hex(primary, 0.35)
    tertiary = _normalize_hex(tertiary) or _darken_hex(primary, 0.85)
    accent_dark = _darken_hex(primary, 0.78)
    return {
        "accent": primary,
        "accent_dark": accent_dark,
        "sidebar_from": _darken_hex(primary, 0.32),
        "sidebar_to": _darken_hex(primary, 0.48),
        "gradient_rgb": _rgb_string(primary),
        "ink": "#111827",
        "muted": "#64748b",
        "surface_soft": _lighten_hex(primary, 0.92),
        "palette": [primary, secondary, tertiary, accent_dark, _lighten_hex(secondary, 0.4)],
        "success": "#059669",
        "warning": "#d97706",
    }



# Valid chart kinds mapping (case-insensitive)
def _valid_chart_kind(chart_kind_label: str) -> str:
    """Map friendly chart kind labels to internal kind strings."""
    kind_map = {
        "bar": "bar",
        "line": "line",
        "pie": "pie",
        "histogram": "histogram",
        "scatter": "scatter",
        "heatmap": "heatmap",
        "pie / donut": "pie",
    }
    normalized = chart_kind_label.lower().strip()
    result = kind_map.get(normalized, "")
    if not result:
        raise ValueError(f"Unknown chart kind label: {chart_kind_label}")
    return result


@dataclass
class ChartSpec:
    """A titled Plotly figure ready to render or export."""
    title: str
    figure: object
    kind: str = ""


# Chart type labels (friendly names)
CHART_TYPE_LABELS: dict[str, str] = {
    "bar": "Bar",
    "line": "Line",
    "pie": "Pie / Donut",
    "histogram": "Histogram",
    "scatter": "Scatter",
    "heatmap": "Correlation heatmap",
}

CHART_LABELS_BY_FRIENDLY: dict[str, str] = {v: k for k, v in CHART_TYPE_LABELS.items()}

# Chart guide
CHART_GUIDE: list[dict[str, str]] = [
    {
        "chart": "Bar",
        "use_when": "Comparing discrete categories or showing counts",
        "avoid_when": "Continuous data with many ranks or part-to-whole relationships",
    },
    {
        "chart": "Line",
        "use_when": "Showing trends over time or ordered sequences",
        "avoid_when": "Comparing discrete categories at a single point",
    },
    {
        "chart": "Pie / Donut",
        "use_when": "Showing part-to-whole relationships with few categories",
        "avoid_when": "More than 8 segments or when category ordering matters",
    },
    {
        "chart": "Histogram",
        "use_when": "Examining the distribution of a single numeric measure",
        "avoid_when": "Comparing categories or showing exact values",
    },
    {
        "chart": "Scatter",
        "use_when": "Exploring correlation between two numeric measures",
        "avoid_when": "Showing part-to-whole or discrete category comparisons",
    },
    {
        "chart": "Correlation heatmap",
        "use_when": "Showing pairwise correlations across many numeric measures",
        "avoid_when": "Fewer than 3 numeric measures or when individual values matter",
    },
]


def available_chart_types(column_types: dict[str, list[str]]) -> list[str]:
    """Return the subset of chart types that can be rendered given *column_types$.

    Based on detected column types; the actual per-dataset checks happen in generate_charts.
    """
    numeric = column_types.get("numeric", []) + column_types.get("currency", []) + column_types.get("percentage", [])
    categorical = column_types.get("categorical", [])
    datetime = column_types.get("datetime", [])
    boolean = column_types.get("boolean", [])

    kinds: list[str] = []

    # Bar: available when there's a categorical, datetime, or boolean column.
    if categorical or datetime or boolean:
        kinds.append("bar")

    # Line: available when there's a datetime column.
    if datetime:
        kinds.append("line")

    # Pie / Donut: available when there's a categorical column.
    if categorical:
        kinds.append("pie")

    # Histogram: available when there's at least one numeric column.
    if numeric:
        kinds.append("histogram")

    # Scatter: needs >= 2 numeric columns.
    if len(numeric) >= 2:
        kinds.append("scatter")

    # Heatmap: needs >= 3 numeric columns.
    if len(numeric) >= 3:
        kinds.append("heatmap")

    return kinds


def _sort_aggregate(
    df: pd.DataFrame, category_col: str, value_col: str, order: str = "desc"
) -> pd.DataFrame:
    """Aggregate *value_col* by *category_col* and return a sorted DataFrame."""
    if category_col not in df.columns:
        raise ValueError(f"Category column '{category_col}' was not found in the dataset.")
    if value_col not in df.columns:
        raise ValueError(f"Value column '{value_col}' was not found in the dataset.")
    aggregated = df.groupby(category_col, as_index=False)[value_col].sum()
    if order == "desc":
        aggregated = aggregated.sort_values(value_col, ascending=False)
    elif order == "asc":
        aggregated = aggregated.sort_values(value_col, ascending=True)
    elif order == "alpha":
        aggregated = aggregated.sort_values(category_col, kind="mergesort")
    else:
        raise ValueError(f"Unsupported order '{order}'. Use 'desc', 'asc', or 'alpha'.")
    return aggregated


def _build_palette(theme: dict) -> list[str]:
    """Build a palette list from theme dict colors."""
    return [
        theme.get("primary", "#2563eb"),
        theme.get("secondary", "#0891b2"),
        theme.get("tertiary", "#059669"),
        theme.get("accent", "#d97706"),
        theme.get("surface_soft", "#e0f2fe"),
    ]


def get_default_theme() -> dict:
    """Return the default theme dict."""
    return COLOR_THEMES["Corporate Blue"]


def generate_charts(
    df: pd.DataFrame,
    column_types: dict[str, list[str]],
    theme: dict | None = None,
    chart_types: list[str] | None = None,
    top_n: int | None = None,
) -> list[ChartSpec]:
    """Build a smart set of charts based on the detected column types.

    Args:
        df: The input DataFrame.
        column_types: Dict mapping category names to lists of column names.
            Expected keys: "numeric", "categorical", "datetime", "boolean",
                "currency", "percentage".
        theme: Optional theme dict; defaults to get_default_theme().
        chart_types: Optional list of chart type names to force; if None,
            all applicable types are generated.
        top_n: Optional maximum number of charts to return.

    Returns:
        A list of ChartSpec instances.
    """
    theme = theme or get_default_theme()
    palette = _build_palette(theme)

    if chart_types is not None:
        allowed = set(chart_types)
    else:
        allowed = None

    # Determine column type lists
    numeric_cols = (
        column_types.get("numeric", [])
        + column_types.get("currency", [])
        + column_types.get("percentage", [])
    )
    categorical_cols = column_types.get("categorical", [])
    datetime_cols = column_types.get("datetime", [])

    charts: list[ChartSpec] = []

    # Line charts: trends over time.
    for date_col in datetime_cols[:2]:
        for measure in numeric_cols[:2]:
            monthly = (
                df.assign(_month=pd.to_datetime(df[date_col], errors="coerce").dt.to_period("M"))
                .dropna(subset=["_month"])
                .groupby("_month", as_index=False)[measure]
                .sum()
                .sort_values("_month")
            )
            title = f"Monthly {measure} Trend"
            if len(monthly) >= 2:
                import plotly.express as px
                fig = px.line(monthly, x="_month", y=measure, title=title, color_discrete_sequence=palette)
                fig.update_layout(
                    title=dict(text=title, font=dict(size=17, color=theme["ink"])),
                    font=dict(color=theme["ink"]),
                    paper_bgcolor=theme.get("paper_bg", "#ffffff"),
                    plot_bgcolor=theme.get("plot_bg", "#ffffff"),
                )
                charts.append(ChartSpec(title=title, figure=fig, kind="line"))

    # Bar / pie charts: top categories (limit to 3 per chart for top_n compatibility).
    for cat in categorical_cols[:3]:
        for measure in numeric_cols[:2]:
            aggregated = (
                df.groupby(cat, as_index=False)[measure]
                .sum()
                .sort_values(measure, ascending=False)
                .head(3)
            )
            if aggregated.empty:
                continue
            orientation = "h" if aggregated[cat].astype(str).str.len().median() > 14 else "v"
            title = f"Top {cat} by {measure}"
            if orientation == "h":
                aggregated = aggregated.sort_values(measure, ascending=True)
                import plotly.express as px
                fig = px.bar(aggregated, x=measure, y=cat, orientation="h", title=title, color_discrete_sequence=palette)
                fig.update_layout(
                    font=dict(color=theme["ink"]),
                    paper_bgcolor=theme.get("paper_bg", "#ffffff"),
                    plot_bgcolor=theme.get("plot_bg", "#ffffff"),
                )
                charts.append(ChartSpec(title=title, figure=fig, kind="bar"))
            else:
                import plotly.express as px
                fig = px.bar(aggregated, x=measure, y=cat, orientation="v", title=title, color_discrete_sequence=palette)
                fig.update_layout(
                    font=dict(color=theme["ink"]),
                    paper_bgcolor=theme.get("paper_bg", "#ffffff"),
                    plot_bgcolor=theme.get("plot_bg", "#ffffff"),
                )
                charts.append(ChartSpec(title=title, figure=fig, kind="bar"))

    # Heatmap: correlation across numeric measures (requires >= 3 numeric columns)
    numeric_for_heatmap = (
        column_types.get("numeric", [])
        + column_types.get("currency", [])
        + column_types.get("percentage", [])
    )
    if len(numeric_for_heatmap) >= 3:
        corr = df[numeric_for_heatmap[:12]].corr(numeric_only=True)
        import plotly.express as px
        fig = px.imshow(
            corr, text_auto=".2f", aspect="auto",
            color_continuous_scale=["#e0f2fe", "#d97706", "#c2410c"],
            title="Correlation Heatmap",
        )
        fig.update_layout(
                    title=dict(text="Correlation Heatmap", font=dict(size=17, color=theme["ink"])),
                    font=dict(color=theme["ink"]),
                    paper_bgcolor=theme.get("paper_bg", "#ffffff"),
                    plot_bgcolor=theme.get("plot_bg", "#ffffff"),
                )
        charts.append(ChartSpec(title="Correlation Heatmap", figure=fig, kind="heatmap"))

    # Force chart_types filtering if specified
    if allowed is not None:
        charts = [c for c in charts if c.kind in allowed]

    # Limit total charts returned
    charts = charts[:14]

    if top_n is not None:
        charts = charts[:top_n]

    return charts


def build_custom_chart(
    df: pd.DataFrame,
    chart_kind_label: str,
    x_col: str | None = None,
    y_col: str | None = None,
    *,
    agg: str = "sum",
    title: str | None = None,
    theme: dict | None = None,
    x_label: str | None = None,
    y_label: str | None = None,
    column_types: dict[str, list[str]] | None = None,
) -> ChartSpec:
    """Build a single custom chart from user-specified kind, X, and Y.

    Args:
        df: The input DataFrame.
        chart_kind_label: One of the friendly chart type labels (from CHART_TYPE_LABELS).
        x_col: Name of the X column, or None for count/bar charts.
        y_col: Name of the Y column, or None for count/bar charts.
        agg: Aggregation function name ("sum" or "mean").
        title: Optional explicit title; auto-generated if not provided.
        theme: Optional theme dict; defaults to get_default_theme().
        x_label: Optional X axis label.
        y_label: Optional Y axis label.
        column_types: Optional dict mapping column type categories to lists of column names.
            If provided, used for column type validation.

    Returns:
        A ChartSpec instance with the built chart.

    Raises:
        ValueError: If the chart kind is unsupported, required columns are missing,
            or the chart type is not appropriate for the given columns.
    """
    theme = theme or get_default_theme()
    palette = _build_palette(theme)
    kind = _valid_chart_kind(chart_kind_label)

    # Auto-generate title
    if title is None:
        if kind == "bar":
            if x_col is None and y_col is None:
                title = "Record Count by Category"
            elif x_col is not None and y_col is None:
                title = f"Record Count by {x_col}"
            elif x_col is not None and y_col is not None:
                title = f"{agg.title()} of {y_col} by {x_col}"
            else:
                title = f"{agg.title()} by Category"
        elif kind == "line":
            if x_col is None and y_col is None:
                title = "Trend"
            else:
                title = f"{agg.title()} Trend: {y_col} over {x_col}"
        elif kind == "pie":
            if x_col is None and y_col is None:
                title = "Distribution"
            elif x_col is not None and y_col is not None:
                title = f"{y_col} Share by {x_col}"
            else:
                title = f"{y_col} Distribution"
        elif kind == "histogram":
            if x_col is not None:
                title = f"{x_col} Distribution"
            else:
                title = "Distribution"
        elif kind == "scatter":
            if x_col is None and y_col is None:
                title = "Scatter plot"
            elif x_col is not None and y_col is not None:
                title = f"{x_col} vs {y_col}"
            else:
                title = "Scatter plot"
        elif kind == "heatmap":
            title = "Correlation Heatmap"

    # Get all column names
    all_cols = set(df.columns)

    # ----- Bar chart -----
    # Check for missing columns
    all_cols = set(df.columns)
    if x_col is not None and x_col not in all_cols:
        raise ValueError(f"Category column '{x_col}' was not found in the dataset.")
    if y_col is not None and y_col not in all_cols:
        raise ValueError(f"Value column '{y_col}' was not found in the dataset.")

    if kind == "bar":
        if x_col is None and y_col is None:
            import plotly.express as px
            fig = px.bar(df, title=title, color_discrete_sequence=palette)
            fig.update_layout(title=dict(text=title, font=dict(size=17, color=theme["ink"])))
            if y_label is not None:
                fig.update_layout(yaxis_title=y_label)
            from dashboard import ChartSpec
        elif y_col is None:
            # Count mode with X column
            title = f"Record Count by {x_col}" if title is None else title
            import plotly.express as px
            fig = px.bar(df, x=x_col, title=title, color_discrete_sequence=palette)
            fig.update_layout(title=dict(text=title, font=dict(size=17, color=theme["ink"])))
            if y_label is not None:
                fig.update_layout(yaxis_title=y_label)
            from dashboard import ChartSpec
            return ChartSpec(title=title, figure=fig, kind="bar")
            return ChartSpec(title=title, figure=fig, kind="bar")
        elif y_col is not None and y_col in all_cols:
            import plotly.express as px
            fig = px.bar(df, y=y_col, title=title, color_discrete_sequence=palette)
            fig.update_layout(title=dict(text=title, font=dict(size=17, color=theme["ink"])))
            if y_label is not None:
                fig.update_layout(yaxis_title=y_label)
            from dashboard import ChartSpec
            return ChartSpec(title=title, figure=fig, kind="bar")
        else:
            raise ValueError("Bar chart requires a Y column or no columns for count chart")

    # ----- Line chart -----
    if kind == "line":
        # Auto-detect column types if not provided
        if column_types is None:
            column_types = {"numeric": [], "currency": [], "percentage": [], "categorical": [], "datetime": [], "boolean": []}
            for col in df.columns:
                if col in ['Order ID', 'Order Date']:  # Simplified datetime detection
                    column_types['datetime'].append(col)
                elif col in ['Region', 'Product']:  # Categorical
                    column_types['categorical'].append(col)
                elif col in ['Revenue', 'Units']:  # Numeric
                    column_types['numeric'].append(col)
        
        if x_col is not None and x_col in all_cols and y_col is not None and y_col in all_cols:
            x_is_date = x_col in column_types.get("datetime", [])
            x_is_numeric = x_col in column_types.get("numeric", []) + column_types.get("currency", []) + column_types.get("percentage", [])
            if not (x_is_date or x_is_numeric):
                raise ValueError("Line chart requires a date column or numeric X column")
            import plotly.express as px
            fig = px.line(df, x=x_col, y=y_col, title=title, color_discrete_sequence=palette)
            fig.update_layout(title=dict(text=title, font=dict(size=17, color=theme["ink"])))
            if y_label is not None:
                fig.update_layout(yaxis_title=y_label)
            from dashboard import ChartSpec
            return ChartSpec(title=title, figure=fig, kind="line")
        else:
            raise ValueError("Line chart requires both X and Y columns")
        if x_col is not None and x_col in all_cols:
            if column_types is not None:
                x_is_date = x_col in column_types.get("datetime", [])
                x_is_numeric = x_col in column_types.get("numeric", []) + column_types.get("currency", []) + column_types.get("percentage", [])
            if not (x_is_date or x_is_numeric):
                raise ValueError("Line chart requires a date column or numeric X column")

    # ----- Pie chart -----
    if kind == "pie":
        if x_col is not None and x_col in all_cols and y_col is not None and y_col in all_cols:
            aggregated = df.groupby(x_col, as_index=False)[y_col].sum()
            if len(aggregated) > 8:
                raise ValueError("8 segments or fewer")
            numeric_for_pie = column_types.get("numeric", []) + column_types.get("currency", []) + column_types.get("percentage", []) if column_types else []
            if y_col not in numeric_for_pie:
                raise ValueError("Pie chart requires a numeric Y column")
            import plotly.express as px
            fig = px.pie(aggregated, names=x_col, values=y_col, hole=0.42, title=title, color_discrete_sequence=palette)
            fig.update_layout(title=dict(text=title, font=dict(size=17, color=theme["ink"])))
            if y_label is not None:
                fig.update_layout(yaxis_title=y_label)
            from dashboard import ChartSpec
            return ChartSpec(title=title, figure=fig, kind="pie")
        else:
            raise ValueError("Pie chart requires X and Y columns")

    # ----- Histogram chart -----
    if kind == "histogram":
        if x_col is not None and x_col in all_cols:
            # Check if column is numeric using pandas dtype
            if not pd.api.types.is_numeric_dtype(df[x_col]):
                raise ValueError("Histogram column is not numeric")
            import plotly.express as px
            fig = px.histogram(df, x=x_col, nbins=35, marginal="box", title=title, color_discrete_sequence=palette)
            fig.update_layout(title=dict(text=title, font=dict(size=17, color=theme["ink"])))
            if y_label is not None:
                fig.update_layout(yaxis_title=y_label)
            from dashboard import ChartSpec
            return ChartSpec(title=title, figure=fig, kind="histogram")
        else:
            raise ValueError("Histogram requires a numeric X column")

    # ----- Scatter chart -----
    if kind == "scatter":
        if x_col is not None and x_col in all_cols and y_col is not None and y_col in all_cols:
            if column_types is not None:
                if y_col not in column_types.get("numeric", []) + column_types.get("currency", []) + column_types.get("percentage", []):
                    raise ValueError("Scatter chart requires a numeric Y column")
            import plotly.express as px
            fig = px.scatter(df, x=x_col, y=y_col, title=title, color_discrete_sequence=palette)
            fig.update_traces(marker=dict(color=theme['accent'], opacity=0.65, size=7))
            fig.update_layout(title=dict(text=title, font=dict(size=17, color=theme['ink'])))
            if y_label is not None:
                fig.update_layout(yaxis_title=y_label)
            from dashboard import ChartSpec
            return ChartSpec(title=title, figure=fig, kind="scatter")
        elif y_col is None:
            raise ValueError("both an X and a Y")
        else:
            raise ValueError("Scatter chart requires both X and Y columns")
            fig = px.scatter(df, x=x_col, y=y_col, title=title, color_discrete_sequence=palette)
            fig.update_traces(marker=dict(color=theme["accent"], opacity=0.65, size=7))
            fig.update_layout(title=dict(text=title, font=dict(size=17, color=theme["ink"])))
            if y_label is not None:
                fig.update_layout(yaxis_title=y_label)
            from dashboard import ChartSpec
            return ChartSpec(title=title, figure=fig, kind="scatter")
        if y_col is not None and y_col in all_cols:
            if column_types is not None and y_col not in column_types.get("numeric", []) + column_types.get("currency", []) + column_types.get("percentage", []):
                raise ValueError("Scatter chart requires a numeric Y column")

    # ----- Heatmap chart -----
    if kind == "heatmap":
        numeric_for_heatmap = column_types.get("numeric", []) + column_types.get("currency", []) + column_types.get("percentage", []) if column_types else []
        if len(numeric_for_heatmap) < 3:
            raise ValueError("Heatmap requires at least 3 numeric columns")
        corr = df[numeric_for_heatmap[:12]].corr(numeric_only=True)
        import plotly.express as px
        fig = px.imshow(corr, text_auto=".2f", aspect="auto",
            color_continuous_scale=["#e0f2fe", "#d97706", "#c2410c"], title=title)
        fig.update_layout(title=dict(text=title, font=dict(size=17, color=theme["ink"])))
        from dashboard import ChartSpec
        return ChartSpec(title=title, figure=fig, kind="heatmap")

    raise ValueError(f"Unsupported chart kind: {kind}")

def filter_dataframe(df: pd.DataFrame, column_types: dict[str, list[str]]) -> pd.DataFrame:
    """Render sidebar filters (category + date) and return the filtered data."""
    filtered = df.copy()
    st.sidebar.header("Filters")

    categorical = column_types.get("categorical", []) + column_types.get("boolean", [])
    for column in categorical[:8]:
        values = sorted([str(v) for v in filtered[column].unique()])
        selected = st.sidebar.multiselect(
            f"{column}", options=values, default=values, key=f"filter_{column}"
        )
        filtered = filtered[filtered[column].isin(selected)]

    datetime = column_types.get("datetime", [])
    for column in datetime[:2]:
        values = sorted([str(v) for v in filtered[column].unique()])
        selected = st.sidebar.multiselect(
            f"{column}", options=values, default=values, key=f"filter_{column}_date"
        )
        filtered = filtered[filtered[column].isin(selected)]
    return filtered

# ---------------------------------------------------------------------------
# Streamlit UI helpers (restored from v2 for app.py imports)
# ---------------------------------------------------------------------------

def inject_styles(theme=None):
    """Inject CSS using the client's selected color theme."""
    theme = theme or get_default_theme()
    accent = theme["accent"]
    accent_dark = theme["accent_dark"]
    gradient_rgb = theme["gradient_rgb"]
    sidebar_from = theme["sidebar_from"]
    sidebar_to = theme["sidebar_to"]
    surface_soft = theme["surface_soft"]
    ink = theme["ink"]
    muted = theme["muted"]
    success = theme["success"]
    warning = theme["warning"]

    css_parts = []
    css_parts.append("<style>")

    # :root block
    css_parts.append(":root {")
    css_parts.append("--surface: #ffffff;")
    css_parts.append("--surface-soft: " + surface_soft + ";")
    css_parts.append("--card-bg: rgba(255,255,255,.94);")
    css_parts.append("--card-border: rgba(148, 163, 184, .28);")
    css_parts.append("--ink: " + ink + ";")
    css_parts.append("--muted: " + muted + ";")
    css_parts.append("--accent: " + accent + ";")
    css_parts.append("--accent-dark: " + accent_dark + ";")
    css_parts.append("--success: " + success + ";")
    css_parts.append("--warning: " + warning + ";")
    css_parts.append("}")

    # .stApp block
    css_parts.append(".stApp {")
    css_parts.append("    background:")
    css_parts.append("        linear-gradient(135deg, rgba(" + gradient_rgb + ",.12), transparent 28rem),")
    css_parts.append("        linear-gradient(180deg, " + surface_soft + " 0%, #eef2f7 100%);")
    css_parts.append("    color: var(--ink);")
    css_parts.append("    font-family: Inter, \"Segoe UI\", system-ui, -apple-system, sans-serif;")
    css_parts.append("}")

    # .block-container
    css_parts.append(".block-container { padding-top: 1.3rem; padding-bottom: 2.4rem; max-width: 1480px; }")

    # [data-testid="stSidebar"]
    css_parts.append('[data-testid="stSidebar"] {')
    css_parts.append("    background: linear-gradient(180deg, " + sidebar_from + " 0%, " + sidebar_to + " 100%);")
    css_parts.append("    color: #fff;")
    css_parts.append("    border-right: 1px solid rgba(255,255,255,.08);")
    css_parts.append("}")
    css_parts.append('[data-testid="stSidebar"] * { color: inherit; }')

    # [data-testid="stSidebar"] [data-testid="stFileUploader"]
    css_parts.append('[data-testid="stSidebar"] [data-testid="stFileUploader"] {')
    css_parts.append("    border: 1px solid rgba(255,255,255,.24);")
    css_parts.append("    background: rgba(255,255,255,.08);")
    css_parts.append("    border-radius: 8px;")
    css_parts.append("    padding: .55rem;")
    css_parts.append("    color: #fff;")
    css_parts.append("}")
    css_parts.append('[data-testid="stSidebar"] [data-testid="stFileUploader"] div,')
    css_parts.append('[data-testid="stSidebar"] [data-testid="stFileUploader"] span,')
    css_parts.append('[data-testid="stSidebar"] [data-testid="stFileUploader"] label {')
    css_parts.append("    color: #fff !important;")
    css_parts.append("    font-weight: 500;")
    css_parts.append("}")

    # .hero
    css_parts.append(".hero { padding: 1.3rem 0 1.05rem; border-bottom: 1px solid rgba(148,163,184,.22); margin-bottom: .4rem; }")
    css_parts.append(".hero h1 { font-size: clamp(2rem, 4vw, 3.4rem); line-height: 1.05; margin: 0; color: var(--ink); }")
    css_parts.append(".hero p { color: var(--muted); font-size: 1.05rem; margin-top: .65rem; max-width: 58rem; }")

    # .dashboard-banner
    css_parts.append(".dashboard-banner {")
    css_parts.append("    background: linear-gradient(135deg, " + accent + " 0%, " + accent_dark + " 100%);")
    css_parts.append("    color: #fff;")
    css_parts.append("    border-radius: 12px;")
    css_parts.append("    padding: 1.1rem 1.35rem;")
    css_parts.append("    margin-bottom: 1.1rem;")
    css_parts.append("    box-shadow: 0 14px 36px rgba(" + gradient_rgb + ",.28);")
    css_parts.append("}")
    css_parts.append(".dashboard-banner h3 { margin: 0; font-size: 1.35rem; font-weight: 750; color: #fff; }")
    css_parts.append(".dashboard-banner p { margin: .35rem 0 0; font-size: .92rem; color: rgba(255,255,255,.88); }")

    # .metric-card
    css_parts.append(".metric_card {")
    css_parts.append("    border: 1px solid var(--card-border);")
    css_parts.append("    background: var(--card-bg);")
    css_parts.append("    border-radius: 12px;")
    css_parts.append("    padding: 1rem 1.1rem;")
    css_parts.append("    box-shadow: 0 12px 32px rgba(15,23,42,.08);")
    css_parts.append("    min-height: 112px;")
    css_parts.append("    transition: transform .15s ease, box-shadow .15s ease;")
    css_parts.append("}")
    css_parts.append(".metric_card:hover {")
    css_parts.append("    transform: translateY(-2px);")
    css_parts.append("    box-shadow: 0 16px 40px rgba(15,23,42,.12);")
    css_parts.append("}")
    css_parts.append(".metric_card .label { color: var(--muted); font-size: .82rem; text-transform: uppercase; letter-spacing: .08em; }")
    css_parts.append(".metric_card .value { color: var(--ink); font-size: 1.85rem; font-weight: 700; margin-top: .3rem; overflow-wrap: anywhere; }")
    css_parts.append(".metric_card .note { color: var(--muted); font-size: .9rem; margin-top: .2rem; }")

    # .chart-accent-bar
    css_parts.append(".chart-accent-bar {")
    css_parts.append("    height: 5px;")
    css_parts.append("    border-radius: 10px 10px 0 0;")
    css_parts.append("    margin-top: .65rem;")
    css_parts.append("}")

    # div[data-testid="stPlotlyChart"]
    css_parts.append('div[data-testid="stPlotlyChart"] {')
    css_parts.append("    border: 1px solid rgba(148,163,184,.22);")
    css_parts.append("    border-radius: 0 0 12px 12px;")
    css_parts.append("    background: rgba(255,255,255,.95);")
    css_parts.append("    padding: .25rem;")
    css_parts.append("    margin-bottom: 1.1rem;")
    css_parts.append("    box-shadow: 0 10px 28px rgba(15,23,42,.06);")
    css_parts.append("}")

    # .section-title
    css_parts.append(".section-title { font-size: 1.35rem; font-weight: 760; margin: 1.55rem 0 .7rem; color: var(--ink); }")

    # .insight
    css_parts.append(".insight {")
    css_parts.append("    border-left: 4px solid " + accent + ";")
    css_parts.append("    background: rgba(255,255,255,.88);")
    css_parts.append("    border-radius: 8px;")
    css_parts.append("    padding: .8rem 1rem;")
    css_parts.append("    margin-bottom: .65rem;")
    css_parts.append("    color: #1d2939;")
    css_parts.append("    box-shadow: 0 8px 24px rgba(15,23,42,.05);")
    css_parts.append("}")

    # .warning
    css_parts.append(".warning { border-left-color: " + warning + "; }")

    # div[data-testid="stDataFrame"]
    css_parts.append('div[data-testid="stDataFrame"] {')
    css_parts.append("    border: 1px solid rgba(148,163,184,.28);")
    css_parts.append("    border-radius: 8px;")
    css_parts.append("    overflow: hidden;")
    css_parts.append("    box-shadow: 0 10px 26px rgba(15,23,42,.05);")
    css_parts.append("}")

    # .stTabs [data-baseweb="tab-list"]
    css_parts.append('.stTabs [data-baseweb="tab-list"] {')
    css_parts.append("    gap: .35rem;")
    css_parts.append("    background: rgba(255,255,255,.78);")
    css_parts.append("    border: 1px solid rgba(148,163,184,.24);")
    css_parts.append("    border-radius: 8px;")
    css_parts.append("    padding: .35rem;")
    css_parts.append("}")

    # .stTabs [data-baseweb="tab"]
    css_parts.append('.stTabs [data-baseweb="tab"] {')
    css_parts.append("    border-radius: 7px; color: #475569; font-weight: 650; padding: .6rem .85rem;")
    css_parts.append("}")

    # .stTabs [aria-selected="true"]
    css_parts.append('.stTabs [aria-selected="true"] {')
    css_parts.append("    background: " + sidebar_from + "; color: #ffffff;")
    css_parts.append("}")

    # div[data-testid="stFileUploader"]
    css_parts.append('div[data-testid="stFileUploader"] {')
    css_parts.append("    background: rgba(255,255,255,.92);")


# ---------------------------------------------------------------------------
# Streamlit UI helpers (restored from v2 for app.py imports)
# ---------------------------------------------------------------------------

def render_card(label, value, note="", accent="#2563eb"):
    """Render a single KPI metric card with a themed accent stripe."""
    import html as html_lib
    css = (
        '<div style="border:1px solid #e2e8f0;border-top:4px solid ' + accent + ';'
        'border-radius:12px;padding:14px 16px;background:#fff;'
        'box-shadow:0 8px 22px rgba(15,23,42,.07);'
        'font-family:Inter,Segoe UI,system-ui,sans-serif;">'
        '<div style="color:#64748b;font-size:11px;text-transform:uppercase;letter-spacing:.08em;">'
        + html_lib.escape(label) + '</div>'
        '<div style="color:#111827;font-size:26px;font-weight:700;margin-top:6px;">'
        + html_lib.escape(value) + '</div>'
        '<div style="color:#64748b;font-size:12px;margin-top:4px;">'
        + html_lib.escape(note) + '</div></div>'
    )
    st.markdown(css, unsafe_allow_html=True)


def render_metric_cards(kpis, theme=None):
    """Render a responsive grid of KPI cards using the client color palette."""
    theme = theme or get_default_theme()
    palette = theme["palette"]
    cols = st.columns(min(4, max(1, len(kpis))))
    for idx, (label, metric) in enumerate(kpis.items()):
        with cols[idx % len(cols)]:
            render_card(label, metric["value"], metric.get("note", ""), palette[idx % len(palette)])


def render_dashboard_banner(theme, theme_name, branding=None):
    """Dashboard header with client logo, name, and active color theme."""
    branding = branding or {}
    company = branding.get("company_name") or "Client Dashboard"
    accent, accent_dark = theme["accent"], theme["accent_dark"]

    logo_tag = ""
    logo_bytes = branding.get("logo_bytes")
    if logo_bytes:
        ext = (branding.get("logo_name") or "logo.png").split(".")[-1].lower()
        mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp"}.get(ext, "image/png")
        import base64
        b64 = base64.b64encode(logo_bytes).decode()
        logo_tag = (
            '<img src="data:' + mime + ';base64,' + b64 + '" alt="logo" '
            'style="height:54px;max-width:120px;object-fit:contain;'
            'background:rgba(255,255,255,.18);border-radius:8px;padding:6px;'
            '"/>'
        )

    import html as html_lib

    banner_html = (
        '<div style="display:flex;align-items:center;gap:14px; max-height: 108px; min-height: 96px;'
        'background:linear-gradient(135deg,' + accent + ' 0%,' + accent_dark + ' 100%);'
        'border-radius:12px;padding:16px 20px;'
        'box-shadow:0 12px 30px rgba(0,0,0,.15);font-family:Inter,Segoe UI,system-ui,sans-serif;">'
        + logo_tag +
        '<div>'
        '<h3 style="margin:0;color:#fff;font-size:20px;font-weight:700;">' + html_lib.escape(company) + '</h3>'
        '<p style="margin:8px 0 0;color:rgba(255,255,255,.92);font-size:14px;line-height:1.45;">'
        'Theme: <strong>' + html_lib.escape(theme_name) + '</strong> &nbsp;|&nbsp; '
        'Branded dashboard - change colors or logo anytime from the sidebar.</p>'
        '</div></div>'
    )
    st.markdown(banner_html, unsafe_allow_html=True)


def render_charts(charts, theme=None, two_column=True):
    """Render charts with themed accent bars; optional two-column layout."""
    if not charts:
        st.warning("No valid chart combinations were detected for this dataset.")
        return
    theme = theme or get_default_theme()
    palette = theme["palette"]

    def _draw(chart, accent, index):
        st.markdown('<div style="height:12px;background:' + accent + ';border-radius:6px 6px 0 0;"></div>')
        st.plotly_chart(chart, use_container_width=True, key="plotly_" + str(index) + "_" + chart.title.replace(" ", "_"))

    if not two_column:
        for idx, chart in enumerate(charts):
            _draw(chart, palette[idx % len(palette)], idx)
        return

    for i in range(0, len(charts), 2):
        pair = charts[i : i + 2]
        cols = st.columns(2 if len(pair) == 2 else 1)
        for j, chart in enumerate(pair):
            idx = i + j
            with cols[j]:
                _draw(chart, palette[idx % len(palette)], idx)


def select_client_branding():
    """Ask client for company name, logo, and color scheme (preset or custom hex)."""
    import os
    st.sidebar.markdown("---")
    st.sidebar.subheader("Client Branding")
    st.sidebar.caption("Add the client's name, logo, and brand colors for a white-label dashboard.")

    company_name = st.sidebar.text_input("Company / client name", placeholder="e.g. Acme Retail Ltd", key="client_company")
    logo_file = st.sidebar.file_uploader("Company logo", type=["png", "jpg", "jpeg", "webp"], key="client_logo")
    if logo_file is not None:
        st.sidebar.image(logo_file, width=110, caption="Logo preview")

    st.sidebar.markdown("**Color scheme**")
    names = list(COLOR_THEMES.keys()) + ["Custom Brand Colors"]
    choice = st.sidebar.selectbox("Color theme", names, key="client_color_theme")

    if choice == "Custom Brand Colors":
        pick_primary = st.sidebar.color_picker("Primary brand color", "#2563eb", key="pick_primary")
        pick_secondary = st.sidebar.color_picker("Secondary color", "#0891b2", key="pick_secondary")
        pick_tertiary = st.sidebar.color_picker("Third accent", "#059669", key="pick_tertiary")
        with st.sidebar.expander("Or type hex codes manually"):
            hex_primary = st.text_input("Primary hex", pick_primary, placeholder="#2563eb", key="hex_primary")
            hex_secondary = st.text_input("Secondary hex", pick_secondary, placeholder="#0891b2", key="hex_secondary")
            hex_tertiary = st.text_input("Third hex", pick_tertiary, placeholder="#059669", key="hex_tertiary")
        from dashboard import build_custom_theme
        import re
        theme = build_custom_theme(
            re.match(r"#[0-9A-Fa-f]{6}", hex_primary) or hex_primary,
            re.match(r"#[0-9A-Fa-f]{6}", hex_secondary) or hex_secondary,
            re.match(r"#[0-9A-Fa-f]{6}", hex_tertiary) or hex_tertiary,
        )
        theme_label = "Custom (" + theme["accent"] + ")"
    else:
        theme = COLOR_THEMES[choice]
        theme_label = choice

    st.sidebar.markdown(
        '<div style="margin:.35rem 0 .85rem;">' + _theme_swatches(theme) + '</div>'
        '<div style="font-size:.78rem;color:#94a3b8;">Primary: ' + theme["accent"] + '</div>',
        unsafe_allow_html=True,
    )

    branding = {
        "company_name": company_name.strip() or "Client Dashboard",
        "logo_bytes": logo_file.getvalue() if logo_file is not None else None,
        "logo_name": logo_file.name if logo_file is not None else "",
    }
    display_name = company_name.strip() or theme_label
    return theme, display_name, branding


def _theme_swatches(theme):
    palette = theme["palette"]
    return "".join(
        '<span title="' + c + '" style="display:inline-block;width:30px;height:30px;border-radius:8px;'
        'background:' + c + ';margin-right:6px;border:2px solid rgba(255,255,255,.9);'
        'box-shadow:0 2px 6px rgba(0,0,0,.15);"></span>'
        for c in palette[:5]
    )
