from __future__ import annotations

import math
import pandas as pd

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
        "ink": "#1e293b",
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
        "ink": "#0f172a",
    },
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
                fig.update_layout(title=dict(text=title, font=dict(size=17, color=theme["ink"])))
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
                charts.append(ChartSpec(title=title, figure=fig, kind="bar"))
            else:
                import plotly.express as px
                fig = px.bar(aggregated, x=measure, y=cat, orientation="v", title=title, color_discrete_sequence=palette)
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
        fig.update_layout(title=dict(text="Correlation Heatmap", font=dict(size=17, color=theme["ink"])))
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
