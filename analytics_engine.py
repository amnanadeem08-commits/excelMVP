"""Automation layer: pandas-powered replacement for manual Excel pivots.

Turns raw data into the artifacts an analyst would otherwise build by hand:
- ``generate_pivot_tables``: auto pivot-table equivalents via ``groupby``.
- ``build_kpis``: headline KPIs (total, average, growth %, top category).
- ``analyze_dataset``: statistics, correlations, and date ranges.

CUSTOMIZE:
- Change ``PRIORITY_METRIC_WORDS`` to steer which numeric column is treated
  as the primary business metric (e.g. put "gmv" first).
- Adjust ``top_n`` in ``generate_pivot_tables`` for longer/shorter rankings.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


# CUSTOMIZE: words used to pick the headline metric, highest priority first.
PRIORITY_METRIC_WORDS = ["revenue", "sales", "amount", "profit", "cost", "price", "total"]


@dataclass
class PivotTable:
    """A single automated pivot-table equivalent."""

    title: str
    slug: str
    data: pd.DataFrame


def _slug(text: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in text).strip("_")


def numeric_measures(df: pd.DataFrame, column_types: dict[str, list[str]]) -> list[str]:
    """Return numeric/currency/percentage columns usable as measures."""
    cols = column_types.get("currency", []) + column_types.get("numeric", []) + column_types.get("percentage", [])
    return [col for col in dict.fromkeys(cols) if col in df.columns and pd.api.types.is_numeric_dtype(df[col])]


def categorical_dimensions(df: pd.DataFrame, column_types: dict[str, list[str]], max_cardinality: int = 50) -> list[str]:
    """Return categorical/boolean columns suitable for grouping."""
    return [
        col
        for col in column_types.get("categorical", []) + column_types.get("boolean", [])
        if col in df.columns and 1 < df[col].nunique(dropna=True) <= max_cardinality
    ]


def best_numeric_column(df: pd.DataFrame, column_types: dict[str, list[str]]) -> str | None:
    """Pick the most likely "primary business metric" column."""
    candidates = numeric_measures(df, column_types)
    if not candidates:
        return None
    for word in PRIORITY_METRIC_WORDS:
        for col in candidates:
            if word in col.lower():
                return col
    return max(candidates, key=lambda col: float(df[col].abs().sum()))


def analyze_dataset(df: pd.DataFrame, column_types: dict[str, list[str]]) -> dict:
    """Compute summary statistics, correlations, and date ranges."""
    numeric_cols = numeric_measures(df, column_types)

    missing_total = int(df.isna().sum().sum())
    total_cells = max(int(df.shape[0] * df.shape[1]), 1)
    missing_pct = round(missing_total / total_cells * 100, 2)

    statistics = pd.DataFrame()
    correlations = pd.DataFrame()
    if numeric_cols:
        statistics = df[numeric_cols].describe().T
        statistics["median"] = df[numeric_cols].median(numeric_only=True)
        statistics = statistics[["mean", "median", "std", "min", "25%", "50%", "75%", "max"]].round(3)
    if len(numeric_cols) >= 2:
        correlations = df[numeric_cols].corr(numeric_only=True).round(3)

    date_ranges = []
    for column in column_types.get("datetime", []):
        series = pd.to_datetime(df[column], errors="coerce").dropna()
        if not series.empty:
            date_ranges.append(
                {
                    "column": column,
                    "start": series.min().date().isoformat(),
                    "end": series.max().date().isoformat(),
                    "days": int((series.max() - series.min()).days),
                }
            )

    return {
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "missing_total": missing_total,
        "missing_pct": missing_pct,
        "numeric_count": len(numeric_cols),
        "categorical_count": len(column_types.get("categorical", [])),
        "datetime_count": len(column_types.get("datetime", [])),
        "statistics": statistics,
        "correlations": correlations,
        "date_ranges": date_ranges,
    }


def compute_growth(df: pd.DataFrame, column_types: dict[str, list[str]], measure: str | None = None) -> dict | None:
    """Compute period-over-period growth % for the primary metric over time.

    Returns ``None`` when there is no usable date column or fewer than two
    periods. Growth is measured between the first and last available month.
    """
    measure = measure or best_numeric_column(df, column_types)
    date_cols = [col for col in column_types.get("datetime", []) if col in df.columns]
    if measure is None or not date_cols:
        return None

    date_col = date_cols[0]
    monthly = (
        df.assign(_month=pd.to_datetime(df[date_col], errors="coerce").dt.to_period("M").dt.to_timestamp())
        .dropna(subset=["_month"])
        .groupby("_month")[measure]
        .sum()
        .sort_index()
    )
    if len(monthly) < 2:
        return None

    first, last = float(monthly.iloc[0]), float(monthly.iloc[-1])
    growth_pct = ((last - first) / abs(first) * 100) if first != 0 else 0.0
    prev = float(monthly.iloc[-2])
    mom_pct = ((last - prev) / abs(prev) * 100) if prev != 0 else 0.0
    return {
        "measure": measure,
        "first_value": first,
        "last_value": last,
        "growth_pct": round(growth_pct, 1),
        "mom_pct": round(mom_pct, 1),
        "start": monthly.index[0].date().isoformat(),
        "end": monthly.index[-1].date().isoformat(),
        "periods": int(len(monthly)),
    }


def top_categories(df: pd.DataFrame, column_types: dict[str, list[str]], measure: str | None = None, top_n: int = 5):
    """Return the top categories by the primary metric, if available."""
    measure = measure or best_numeric_column(df, column_types)
    cats = categorical_dimensions(df, column_types)
    if measure is None or not cats:
        return None
    cat = cats[0]
    ranked = df.groupby(cat)[measure].sum().sort_values(ascending=False).head(top_n)
    return {"dimension": cat, "measure": measure, "ranking": ranked}


def build_kpis(df: pd.DataFrame, summary: dict, column_types: dict[str, list[str]]) -> dict[str, dict[str, str]]:
    """Build headline KPI cards: records, quality, total, average, growth."""
    value_col = best_numeric_column(df, column_types)
    kpis: dict[str, dict[str, str]] = {
        "Records": {"value": f"{summary['rows']:,}", "note": f"{summary['columns']:,} columns analyzed"},
        "Data Quality": {"value": f"{100 - summary['missing_pct']:.1f}%", "note": "Completeness score"},
    }

    if value_col:
        total = df[value_col].sum()
        avg = df[value_col].mean()
        kpis["Total"] = {"value": f"{total:,.2f}", "note": f"Sum of {value_col}"}
        kpis["Average"] = {"value": f"{avg:,.2f}", "note": f"Avg {value_col}"}

        growth = compute_growth(df, column_types, value_col)
        if growth:
            arrow = "▲" if growth["growth_pct"] >= 0 else "▼"
            kpis["Growth"] = {
                "value": f"{arrow} {growth['growth_pct']:.1f}%",
                "note": f"{growth['start']} → {growth['end']}",
            }
        else:
            top = top_categories(df, column_types, value_col)
            if top is not None and not top["ranking"].empty:
                leader = top["ranking"].index[0]
                kpis["Top Segment"] = {"value": str(leader)[:18], "note": f"Top {top['dimension']}"}
    else:
        kpis["Numeric Fields"] = {"value": f"{summary['numeric_count']:,}", "note": "Measures detected"}
        kpis["Segments"] = {"value": f"{summary['categorical_count']:,}", "note": "Categorical fields"}

    return kpis


def generate_pivot_tables(df: pd.DataFrame, column_types: dict[str, list[str]], top_n: int = 10) -> list[PivotTable]:
    """Auto-generate pivot-table equivalents using pandas ``groupby``."""
    pivots: list[PivotTable] = []
    numeric_cols = numeric_measures(df, column_types)
    categorical_cols = categorical_dimensions(df, column_types)
    date_cols = [col for col in column_types.get("datetime", []) if col in df.columns]

    # Measure by category (sum / mean / median / count).
    for cat in categorical_cols[:4]:
        for measure in numeric_cols[:3]:
            pivot = (
                df.groupby(cat, dropna=False)[measure]
                .agg(["sum", "mean", "median", "count"])
                .reset_index()
                .sort_values("sum", ascending=False)
                .head(top_n)
            )
            pivot[["sum", "mean", "median"]] = pivot[["sum", "mean", "median"]].round(2)
            title = f"{measure} by {cat}"
            pivots.append(PivotTable(title=title, slug=_slug(title), data=pivot))

    # Measure by month (time-based pivot).
    for date_col in date_cols[:2]:
        month = pd.to_datetime(df[date_col], errors="coerce").dt.to_period("M").astype(str)
        for measure in numeric_cols[:2]:
            pivot = (
                df.assign(Month=month)
                .dropna(subset=["Month"])
                .groupby("Month", dropna=False)[measure]
                .agg(["sum", "mean", "count"])
                .reset_index()
                .sort_values("Month")
            )
            pivot[["sum", "mean"]] = pivot[["sum", "mean"]].round(2)
            title = f"{measure} by Month"
            pivots.append(PivotTable(title=title, slug=_slug(f"{title}_{date_col}"), data=pivot))

    # Record counts by category.
    for cat in categorical_cols[:4]:
        pivot = (
            df.groupby(cat, dropna=False)
            .size()
            .reset_index(name="record_count")
            .sort_values("record_count", ascending=False)
            .head(top_n)
        )
        title = f"Record Count by {cat}"
        pivots.append(PivotTable(title=title, slug=_slug(title), data=pivot))

    seen = set()
    unique_pivots = []
    for pivot in pivots:
        if pivot.slug not in seen and not pivot.data.empty:
            seen.add(pivot.slug)
            unique_pivots.append(pivot)
    return unique_pivots[:12]
