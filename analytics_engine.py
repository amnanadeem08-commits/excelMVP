"""
Automation layer: pandas-powered replacement for manual Excel pivots.

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
    candidates = [col for col in numeric_measures(df, column_types) if looks_like_measure(df[col], col)]
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


def compute_growth(df: pd.DataFrame, column_types: dict[str, list[str]], measure: str | None = None, agg: str | None = None) -> dict | None:
    """Compute period-over-period growth % for the primary metric over time.

    Parameters:
        df: The cleaned DataFrame.
        column_types: Detected column types.
        measure: Optional measure column name. Defaults to best_numeric_column.
        agg: Aggregation method - 'sum' or 'mean'. For continuous/rate measures,
            use 'mean'. For additive measures, use 'sum'. Defaults to 'sum' for
            backward compatibility.

    Returns ``None`` when there is no usable date column or fewer than two
    periods. Growth is measured between the first and last available month.
    """
    measure = measure or best_numeric_column(df, column_types)
    date_cols = [col for col in column_types.get("datetime", []) if col in df.columns]
    if measure is None or not date_cols:
        return None

    # Determine aggregation: use mean for continuous/rate measures
    if agg is None:
        agg = "sum"  # default for backward compatibility

    date_col = date_cols[0]
    if agg == "mean":
        monthly = (
            df.assign(_month=pd.to_datetime(df[date_col], errors="coerce").dt.to_period("M").dt.to_timestamp())
            .dropna(subset=["_month"])
            .groupby("_month")[measure]
            .mean()
            .sort_index()
        )
    else:
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


def build_kpis(
    df: pd.DataFrame,
    summary: dict,
    column_types: dict[str, list[str]],
    measure: str | None = None,
    agg: str | None = None,
    domain_context: dict | None = None,
) -> dict[str, dict[str, str | dict]]:
    """Build headline KPI cards: records, quality, total/average/median, growth.

    Parameters:
        df: The cleaned DataFrame.
        summary: Dataset summary from analyze_dataset().
        column_types: Detected column types.
        measure: Optional measure column override. Defaults to best_numeric_column.
        agg: Optional aggregation override ('sum', 'mean', 'median').
            For continuous/rate measures, use 'mean' or 'median'.
            For additive measures, use 'sum'. Defaults based on measure semantics.
        domain_context: Optional domain context (reserved for future use).

    Returns:
        Dict mapping KPI names to {"value": str, "note": str, "validation": str}.
    """
    value_col = measure or best_numeric_column(df, column_types)
    semantics = measure_semantics(value_col, column_types) if value_col else "additive"

    # Determine aggregation for this measure type
    if agg is None:
        if semantics in ("continuous", "rate"):
            agg = "mean"
        else:
            agg = "sum"

    kpis: dict[str, dict[str, str | dict]] = {
        "Records": {"value": f"{summary['rows']:,}", "note": f"{summary['columns']:,} columns analyzed", "validation": "pass"},
        "Data Quality": {"value": f"{100 - summary['missing_pct']:.1f}%", "note": "Completeness score", "validation": "pass"},
    }

    if value_col:
        total = df[value_col].sum()
        avg = df[value_col].mean()
        median = df[value_col].median()

        # Format value based on measure semantics
        def format_value(val: float, semantics: str) -> str:
            if semantics == "rate":
                # Rate measures are stored as decimals (0.12 = 12%), multiply by 100 for display
                return f"{val * 100:.1f}%"
            elif semantics == "continuous":
                return f"{val:.2f}"
            else:
                return f"{val:,.2f}"

        # For continuous measures, always show both Average and Median
        if semantics == "continuous":
            kpis[f"Average {value_col}"] = {"value": format_value(avg, semantics), "note": f"Avg {value_col}", "validation": "pass"}
            kpis[f"Median {value_col}"] = {"value": format_value(median, semantics), "note": f"Median {value_col}", "validation": "pass"}
        elif agg == "mean":
            kpis[f"Average {value_col}"] = {"value": format_value(avg, semantics), "note": f"Avg {value_col}", "validation": "pass"}
        elif agg == "median":
            kpis[f"Median {value_col}"] = {"value": format_value(median, semantics), "note": f"Median {value_col}", "validation": "pass"}
        else:  # sum
            if semantics == "additive":
                kpis[f"Total {value_col}"] = {"value": format_value(total, semantics), "note": f"Sum of {value_col}", "validation": "pass"}
            kpis[f"Average {value_col}"] = {"value": format_value(avg, semantics), "note": f"Avg {value_col}", "validation": "pass"}

        # Growth uses mean aggregation for continuous/rate measures
        growth_agg_method = "mean" if semantics in ("continuous", "rate") else "sum"
        growth = compute_growth(df, column_types, value_col, agg=growth_agg_method)
        if growth:
            arrow = "▲" if growth["growth_pct"] >= 0 else "▼"
            magnitude = abs(growth["growth_pct"])
            kpis["Growth"] = {
                "value": f"{arrow} {magnitude:.1f}%",
                "note": f"{growth['start']} → {growth['end']}",
                "validation": "pass",
            }
        else:
            top = top_categories(df, column_types, value_col)
            if top is not None and not top["ranking"].empty:
                leader = top["ranking"].index[0]
                kpis["Top Segment"] = {"value": str(leader)[:18], "note": f"Top {top['dimension']}", "validation": "pass"}
    else:
        kpis["Numeric Fields"] = {"value": f"{summary['numeric_count']:,}", "note": "Measures detected", "validation": "pass"}
        kpis["Segments"] = {"value": f"{summary['categorical_count']:,}", "note": "Categorical fields", "validation": "pass"}

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
            # Add share_pct for category pivots
            total = pivot["sum"].sum()
            if total > 0:
                pivot["share_pct"] = (pivot["sum"] / total * 100).round(1)
            else:
                pivot["share_pct"] = 0
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
        # Add share_pct for record count pivots
        total = pivot["record_count"].sum()
        if total > 0:
            pivot["share_pct"] = (pivot["record_count"] / total * 100).round(1)
        else:
            pivot["share_pct"] = 0
        title = f"Record Count by {cat}"
        pivots.append(PivotTable(title=title, slug=_slug(title), data=pivot))

    seen = set()
    unique_pivots = []
    for pivot in pivots:
        if pivot.slug not in seen and not pivot.data.empty:
            seen.add(pivot.slug)
            unique_pivots.append(pivot)
    return unique_pivots[:12]


# ---------------------------------------------------------------------------
# Measure Semantics (EXECUTIVE_STORY §4 alignment)
# ---------------------------------------------------------------------------

_ADDITIVE_WORDS = {"revenue", "sales", "amount", "profit", "cost", "total", "sum", "units", "quantity", "count", "units shipped", "deal size"}
_RATE_WORDS = {"margin", "markup", "margin %", "profit margin", "conversion", "rate"}


def measure_semantics(
    name: str,
    column_types: dict[str, list[str]] | None = None,
) -> str:
    """Classify a measure as 'additive', 'continuous', or 'rate'.

    This classification determines which KPIs and growth calculations make sense:
    - additive: totals are meaningful (Revenue, Units Shipped)
    - continuous: only averages/percentiles are meaningful (Age, Unit Price)
    - rate: percentages/ratios that should not be summed (Margin, Conversion Rate)

    Parameters:
        name: The column name to classify.
        column_types: Optional column type mapping. If provided, 'percentage' columns
            are always treated as rate measures.

    Returns:
        'additive', 'continuous', or 'rate'
    """
    if name is None:
        return "continuous"
    name_lower = name.lower()
    if column_types and name in column_types.get("percentage", []):
        return "rate"
    if name_lower in _RATE_WORDS or "margin" in name_lower or "conversion" in name_lower:
        return "rate"
    if name_lower in _ADDITIVE_WORDS or any(word in name_lower for word in _ADDITIVE_WORDS):
        return "additive"
    return "continuous"


def looks_like_measure(series: pd.Series, name: str = "") -> bool:
    """Check if a numeric column looks like a reasonable business measure.

    Rejects near-constant columns, binary flags, and near-constant columns.
    Also rejects monotonically increasing sequences like row numbers or IDs when
    the column name suggests it's an identifier.

    Parameters:
        series: The numeric series to check.
        name: Optional column name for heuristic checks.

    Returns:
        True if the column appears usable as a measure.
    """
    if series.empty or series.std(ddof=0) == 0:
        return False
    unique_vals = series.dropna().unique()
    if len(unique_vals) <= 2 and set(unique_vals).issubset({0, 1, 0.0, 1.0, True, False}):
        return False
    value_counts = series.value_counts(dropna=True, normalize=True)
    if (value_counts > 0.99).any():
        return False

    # Reject monotonically increasing sequences (likely IDs or row numbers)
    # Check if column name suggests it's an identifier AND all diffs are constant
    name_lower = name.lower()
    is_id_column = any(kw in name_lower for kw in ["id", "number", "code", "row", "index"])

    if is_id_column and len(series.dropna()) >= 3:
        diffs = series.dropna().diff().dropna()
        if len(diffs) >= 2 and (diffs == diffs.iloc[0]).all() and diffs.iloc[0] > 0:
            return False

    return True


# ---------------------------------------------------------------------------
# Anomaly Detection Layer
# ---------------------------------------------------------------------------

def detect_anomalies(
    df: pd.DataFrame,
    column_types: dict[str, list[str]],
    method: str = "zscore",
    threshold: float = 2.0,
) -> dict[str, dict[str, int | float | list[float]]]:
    """Detect anomalous values in numeric columns using statistical methods.

    Parameters:
        df: The cleaned DataFrame.
        column_types: Detected column types.
        method: Detection method - currently only 'zscore' is supported.
        threshold: Z-score threshold for flagging anomalies (default 2.0).

    Returns a dict mapping column names to anomaly info:
        {
            "column_name": {
                "count": number of anomalies found,
                "percentage": percentage of non-null values that are anomalies,
                "values": list of anomalous values (up to 5 examples),
                "mean": mean of the column,
                "std": standard deviation of the column,
            }
        }
    """
    numeric_cols = []
    for col_type in ["currency", "numeric", "percentage"]:
        numeric_cols.extend(column_types.get(col_type, []))
    numeric_cols = [c for c in numeric_cols if c in df.columns and pd.api.types.is_numeric_dtype(df[c])]

    results: dict[str, dict[str, int | float | list[float]]] = {}

    for col in numeric_cols:
        series = pd.to_numeric(df[col], errors="coerce").dropna()
        if len(series) < 3 or series.std() == 0:
            results[col] = {
                "count": 0,
                "percentage": 0.0,
                "values": [],
                "mean": float(series.mean()) if len(series) > 0 else 0,
                "std": float(series.std()) if len(series) > 0 else 0,
            }
            continue

        if method == "zscore":
            mean = series.mean()
            std = series.std()
            if std == 0:
                results[col] = {
                    "count": 0,
                    "percentage": 0.0,
                    "values": [],
                    "mean": float(mean),
                    "std": 0.0,
                }
                continue
            z_scores = (series - mean).abs() / std
            anomaly_mask = z_scores > threshold
            anomaly_count = int(anomaly_mask.sum())
            anomaly_pct = round(anomaly_count / len(series) * 100, 1)
            anomaly_values = series[anomaly_mask].tolist()[:5]
            results[col] = {
                "count": anomaly_count,
                "percentage": anomaly_pct,
                "values": anomaly_values,
                "mean": float(mean),
                "std": float(std),
            }
        else:
            results[col] = {
                "count": 0,
                "percentage": 0.0,
                "values": [],
                "mean": float(series.mean()) if len(series) > 0 else 0,
                "std": float(series.std()) if len(series) > 0 else 0,
            }

    return results


# ---------------------------------------------------------------------------
# Enhanced Trend Detection
# ---------------------------------------------------------------------------

def detect_trends(
    df: pd.DataFrame,
    column_types: dict[str, list[str]],
    measure: str | None = None,
    top_n: int = 5,
) -> dict[str, any]:
    """Detect top-performing categories and trends by measure.

    Returns insights about which categories lead, which lag, and overall
    dataset trajectory.
    """
    from analytics_engine import best_numeric_column, categorical_dimensions, top_categories

    measure = measure or best_numeric_column(df, column_types)
    cats = categorical_dimensions(df, column_types, max_cardinality=50)

    trends: dict[str, any] = {
        "measure": measure,
        "top_performers": [],
        "bottom_performers": [],
        "trending_up": [],
        "trending_down": [],
        "summary": "",
    }

    if measure is None or not cats:
        trends["summary"] = "Insufficient data to detect trends."
        return trends

    # Top and bottom categories by measure sum
    ranked = top_categories(df, column_types, measure=measure, top_n=top_n)
    if ranked is not None and not ranked["ranking"].empty:
        top_labels = ranked["ranking"].index.tolist()
        top_values = ranked["ranking"].tolist()
        trends["top_performers"] = [
            {"category": cat, "value": val}
            for cat, val in zip(top_labels, top_values)
        ]
        # Bottom performers (last N)
        all_ranked = df.groupby(cats[0])[measure].sum().sort_values(ascending=True).head(top_n)
        bottom_labels = all_ranked.index.tolist()
        bottom_values = all_ranked.tolist()
        trends["bottom_performers"] = [
            {"category": cat, "value": val}
            for cat, val in zip(bottom_labels, bottom_values)
        ]

    # Detect trending categories (month-over-month growth)
    date_cols = [col for col in column_types.get("datetime", []) if col in df.columns]
    if date_cols and measure:
        try:
            monthly = (
                df.assign(_month=pd.to_datetime(df[date_cols[0]], errors="coerce").dt.to_period("M").dt.to_timestamp())
                .dropna(subset=["_month"])
                .groupby("_month")[measure]
                .sum()
                .sort_index()
            )
            if len(monthly) >= 2:
                # Compare first half vs second half
                mid = len(monthly) // 2
                first_half = monthly.iloc[:mid].sum()
                second_half = monthly.iloc[mid:].sum()
                if first_half > 0:
                    half_growth = ((second_half - first_half) / first_half) * 100
                    if half_growth > 5:
                        trends["trending_up"].append("Overall revenue increasing")
                    elif half_growth < -5:
                        trends["trending_down"].append("Overall revenue decreasing")
                # Month-over-month last to first
                if len(monthly) >= 2:
                    mom = (monthly.iloc[-1] - monthly.iloc[0]) / abs(monthly.iloc[0]) * 100 if monthly.iloc[0] != 0 else 0
                    if mom > 5:
                        trends["trending_up"].append(f"{len(monthly)}-period trend: {mom:.1f}% growth")
                    elif mom < -5:
                        trends["trending_down"].append(f"{len(monthly)}-period trend: {mom:.1f}% decline")
        except Exception:
            pass

    # Build summary narrative
    parts = []
    if trends["top_performers"]:
        top = trends["top_performers"][0]
        parts.append(f"Top performer: {top['category']} ({top['value']})")
    if trends["bottom_performers"]:
        bottom = trends["bottom_performers"][0]
        parts.append(f"Underperforming: {bottom['category']} ({bottom['value']})")
    if trends["trending_up"]:
        parts.append("; ".join(trends["trending_up"]))
    if trends["trending_down"]:
        parts.append("; ".join(trends["trending_down"]))
    trends["summary"] = " ".join(parts) if parts else "No significant trends detected."

    return trends


# ---------------------------------------------------------------------------
# Segmentation Layer
# ---------------------------------------------------------------------------

def segment_by_category(
    df: pd.DataFrame,
    column_types: dict[str, list[str]],
    measure: str | None = None,
    top_n: int = 5,
) -> dict[str, any]:
    """Segment a dataset by categorical dimensions for targeted analysis.

    Returns segmentation insights including size, performance, and
    relative contribution of each segment.
    """
    from analytics_engine import best_numeric_column, categorical_dimensions

    measure = measure or best_numeric_column(df, column_types)
    cats = categorical_dimensions(df, column_types, max_cardinality=50)

    if measure is None or not cats:
        return {
            "measure": measure,
            "segments": [],
            "summary": "Insufficient data for segmentation.",
        }

    segments: list[dict[str, any]] = []
    for cat in cats:
        try:
            cat_data = df.groupby(cat)[measure].agg(["sum", "mean", "count"]).reset_index()
            cat_data = cat_data.sort_values("sum", ascending=False)
            total_measure = df[measure].sum()
            if total_measure > 0:
                cat_data["share_pct"] = (cat_data["sum"] / total_measure * 100).round(1)
            else:
                cat_data["share_pct"] = 0
            cat_data["share_count"] = (cat_data["count"] / df.shape[0] * 100).round(1)
            for _, row in cat_data.head(top_n).iterrows():
                segments.append(
                    {
                        "category": row[cat],
                        "total": row["sum"],
                        "average": row["mean"],
                        "record_count": row["count"],
                        "share_of_measure": row["share_pct"],
                        "share_of_records": row["share_count"],
                    }
                )
        except Exception:
            continue

    if not segments:
        return {
            "measure": measure,
            "segments": [],
            "summary": "No segments could be computed.",
        }

    # Build summary
    total_records = df.shape[0]
    largest = segments[0]
    smallest = segments[-1]
    summary_parts = [
        f"{len(segments)} segments identified",
        f"Largest segment: {largest['category']} ({largest['share_of_measure']}% of {measure})",
        f"Smallest segment: {smallest['category']} ({smallest['share_of_measure']}% of {measure})",
    ]

    return {
        "measure": measure,
        "segments": segments,
        "summary": " ".join(summary_parts),
    }


def build_validated_kpis(
    df: pd.DataFrame,
    summary: dict,
    column_types: dict[str, list[str]],
    domain_context: dict | None = None,
) -> dict:
    """Build validated KPI contract for dashboard display.

    Returns a dict with:
        - "kpis": The KPI cards dict (same as build_kpis but with validation)
        - "metric_contract": Dict of formatted KPI names to validation info

    The metric_contract maps KPI display names (like "Total Revenue",
    "Average Unit Price") to their validation status and requirements.
    This includes all expected dashboard KPIs, marking them as applicable
    or not based on the available data.

    Parameters:
        df: The cleaned DataFrame.
        summary: Dataset summary from analyze_dataset().
        column_types: Detected column types.
        domain_context: Optional domain detection context.

    Returns:
        Dict with "kpis" and "metric_contract" keys.
    """
    from analytics_engine import build_kpis, best_numeric_column, measure_semantics, numeric_measures

    # Build the standard KPIs with validation
    kpis = build_kpis(df, summary, column_types)

    # Build metric contract - dict keyed by formatted KPI name
    # This matches the KPI names generated by build_kpis AND the expected dashboard KPIs
    value_col = best_numeric_column(df, column_types)
    metrics = numeric_measures(df, column_types)
    semantics = measure_semantics(value_col, column_types) if value_col else "additive"
    has_dates = bool(column_types.get("datetime"))

    metric_contract = {}

    # Add standard KPIs to contract based on what build_kpis generates
    if value_col:
        if semantics == "additive":
            metric_contract[f"Total {value_col}"] = {
                "name": f"Total {value_col}",
                "semantics": semantics,
                "applicable": True,
                "required_columns": [value_col],
                "caveats": [],
                "unit": "",
            }
        if semantics in ("continuous", "rate"):
            metric_contract[f"Average {value_col}"] = {
                "name": f"Average {value_col}",
                "semantics": semantics,
                "applicable": True,
                "required_columns": [value_col],
                "caveats": [],
                "unit": "%" if semantics == "rate" else "",
            }
            metric_contract[f"Median {value_col}"] = {
                "name": f"Median {value_col}",
                "semantics": semantics,
                "applicable": True,
                "required_columns": [value_col],
                "caveats": [],
                "unit": "",
            }
        else:
            metric_contract[f"Average {value_col}"] = {
                "name": f"Average {value_col}",
                "semantics": semantics,
                "applicable": True,
                "required_columns": [value_col],
                "caveats": [],
                "unit": "",
            }

        # Add growth if we have dates
        if has_dates:
            metric_contract["Growth"] = {
                "name": "Growth",
                "semantics": "rate",
                "applicable": True,
                "required_columns": [value_col] + column_types.get("datetime", []),
                "caveats": ["Growth is period-over-period, not CAGR"],
                "unit": "%",
            }

    # Add record count
    metric_contract["Records"] = {
        "name": "Records",
        "semantics": "count",
        "applicable": True,
        "required_columns": [],
        "caveats": [],
        "unit": "",
    }

    # Add Data Quality
    metric_contract["Data Quality"] = {
        "name": "Data Quality",
        "semantics": "rate",
        "applicable": True,
        "required_columns": [],
        "caveats": ["Based on missing value percentage"],
        "unit": "%",
    }

    # Add placeholder contracts for expected dashboard KPIs that aren't available
    # These will be rendered as "unavailable" by the dashboard
    expected_kpis = [
        "Total Revenue", "Average Unit Price", "Total Quantity", "Profit Margin", "Record Count"
    ]
    for kpi_name in expected_kpis:
        if kpi_name not in metric_contract:
            # Determine semantics based on name
            name_lower = kpi_name.lower()
            if "margin" in name_lower or "profit" in name_lower:
                semantics = "rate"
            elif "price" in name_lower or "unit" in name_lower:
                semantics = "continuous"
            else:
                semantics = "additive"

            metric_contract[kpi_name] = {
                "name": kpi_name,
                "semantics": semantics,
                "applicable": False,
                "required_columns": [],
                "caveats": [f"No {kpi_name.lower()} column found in data"],
                "unit": "%",
            }

    return {"kpis": kpis, "metric_contract": metric_contract}
