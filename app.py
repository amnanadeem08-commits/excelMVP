from __future__ import annotations

import re
from dataclasses import dataclass
from io import BytesIO
from typing import Any

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


# ---- Embedded utils/data_cleaner.py ----
CURRENCY_RE = re.compile(r"^\s*[\$€£₹¥]?\s*-?\d{1,3}(,\d{3})*(\.\d+)?\s*$|^\s*[\$€£₹¥]?\s*-?\d+(\.\d+)?\s*$")
PERCENT_RE = re.compile(r"^\s*-?\d+(\.\d+)?\s*%\s*$")


def _clean_column_names(columns: pd.Index) -> list[str]:
    seen: dict[str, int] = {}
    cleaned = []
    for col in columns:
        name = re.sub(r"\s+", " ", str(col).strip())
        name = name if name and name.lower() != "nan" else "Unnamed"
        count = seen.get(name, 0)
        seen[name] = count + 1
        cleaned.append(name if count == 0 else f"{name}_{count + 1}")
    return cleaned


def _looks_like_bool(series: pd.Series) -> bool:
    values = {str(v).strip().lower() for v in series.dropna().unique()}
    if not values:
        return False
    bool_values = {"true", "false", "yes", "no", "y", "n", "0", "1"}
    return values.issubset(bool_values) and len(values) <= 2


def _to_bool(series: pd.Series) -> pd.Series:
    mapping = {
        "true": True,
        "yes": True,
        "y": True,
        "1": True,
        "false": False,
        "no": False,
        "n": False,
        "0": False,
    }
    return series.astype(str).str.strip().str.lower().map(mapping).astype("boolean")


def _looks_like_currency(series: pd.Series) -> bool:
    sample = series.dropna().astype(str).head(200)
    return len(sample) > 0 and sample.map(lambda value: bool(CURRENCY_RE.match(value))).mean() >= 0.75


def _looks_like_percent(series: pd.Series) -> bool:
    sample = series.dropna().astype(str).head(200)
    return len(sample) > 0 and sample.map(lambda value: bool(PERCENT_RE.match(value))).mean() >= 0.75


def _currency_to_numeric(series: pd.Series) -> pd.Series:
    cleaned = series.astype(str).str.replace(r"[\$€£₹¥,\s]", "", regex=True)
    return pd.to_numeric(cleaned, errors="coerce")


def _percent_to_numeric(series: pd.Series) -> pd.Series:
    cleaned = series.astype(str).str.replace("%", "", regex=False).str.strip()
    return pd.to_numeric(cleaned, errors="coerce") / 100


def detect_column_types(df: pd.DataFrame) -> dict[str, list[str]]:
    """Infer business-friendly column types beyond pandas dtypes."""
    types = {
        "numeric": [],
        "categorical": [],
        "boolean": [],
        "datetime": [],
        "currency": [],
        "percentage": [],
        "text": [],
    }

    row_count = max(len(df), 1)
    for column in df.columns:
        series = df[column]
        non_null = series.dropna()

        if non_null.empty:
            types["text"].append(column)
            continue

        if pd.api.types.is_bool_dtype(series) or _looks_like_bool(series):
            types["boolean"].append(column)
            continue

        if pd.api.types.is_datetime64_any_dtype(series):
            types["datetime"].append(column)
            continue

        if pd.api.types.is_numeric_dtype(series):
            lower_name = str(column).lower()
            if any(token in lower_name for token in ["rate", "percent", "percentage", "margin"]):
                types["percentage"].append(column)
            else:
                types["numeric"].append(column)
            continue

        if _looks_like_percent(series):
            types["percentage"].append(column)
            continue

        if _looks_like_currency(series) or any(token in str(column).lower() for token in ["revenue", "sales", "price", "cost", "amount"]):
            numeric_try = _currency_to_numeric(series)
            if numeric_try.notna().mean() >= 0.65:
                types["currency"].append(column)
                continue

        datetime_try = pd.to_datetime(series, errors="coerce", infer_datetime_format=True)
        if datetime_try.notna().mean() >= 0.8:
            types["datetime"].append(column)
            continue

        unique_ratio = non_null.nunique(dropna=True) / row_count
        if non_null.nunique(dropna=True) <= 30 or unique_ratio <= 0.35:
            types["categorical"].append(column)
        else:
            types["text"].append(column)

    return types


def _fix_types(df: pd.DataFrame, detected: dict[str, list[str]], report: dict[str, Any]) -> pd.DataFrame:
    clean = df.copy()
    for column in detected.get("boolean", []):
        if not pd.api.types.is_bool_dtype(clean[column]):
            clean[column] = _to_bool(clean[column])
            report["columns_corrected"] += 1

    for column in detected.get("currency", []):
        clean[column] = _currency_to_numeric(clean[column])
        report["columns_corrected"] += 1

    for column in detected.get("percentage", []):
        if not pd.api.types.is_numeric_dtype(clean[column]):
            clean[column] = _percent_to_numeric(clean[column])
            report["columns_corrected"] += 1

    for column in detected.get("datetime", []):
        before_missing = clean[column].isna().sum()
        clean[column] = pd.to_datetime(clean[column], errors="coerce")
        invalid_dates = max(int(clean[column].isna().sum() - before_missing), 0)
        report["invalid_dates_fixed"] += invalid_dates
        report["columns_corrected"] += 1

    for column in detected.get("numeric", []):
        if not pd.api.types.is_numeric_dtype(clean[column]):
            converted = pd.to_numeric(clean[column], errors="coerce")
            if converted.notna().mean() >= 0.75:
                clean[column] = converted
                report["columns_corrected"] += 1

    return clean


def clean_data(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Clean uploaded data and return a detailed cleaning report."""
    clean = df.copy()
    report: dict[str, Any] = {
        "starting_rows": int(len(clean)),
        "starting_columns": int(clean.shape[1]),
        "rows_removed": 0,
        "empty_columns_removed": 0,
        "duplicates_removed": 0,
        "missing_values_fixed": 0,
        "columns_corrected": 0,
        "outliers_capped": 0,
        "invalid_dates_fixed": 0,
        "final_rows": 0,
        "final_columns": 0,
    }

    clean.columns = _clean_column_names(clean.columns)

    object_columns = clean.select_dtypes(include=["object", "string"]).columns
    for column in object_columns:
        clean[column] = clean[column].astype("string").str.strip()
        clean[column] = clean[column].replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})

    empty_columns = [column for column in clean.columns if clean[column].isna().all()]
    clean = clean.drop(columns=empty_columns)
    report["empty_columns_removed"] = len(empty_columns)

    duplicates = int(clean.duplicated().sum())
    clean = clean.drop_duplicates().reset_index(drop=True)
    report["duplicates_removed"] = duplicates
    report["rows_removed"] += duplicates

    detected = detect_column_types(clean)
    clean = _fix_types(clean, detected, report)
    detected = detect_column_types(clean)

    missing_before = int(clean.isna().sum().sum())
    for column in clean.columns:
        if clean[column].isna().sum() == 0:
            continue
        if column in detected.get("numeric", []) or column in detected.get("currency", []) or column in detected.get("percentage", []):
            median = clean[column].median()
            mean = clean[column].mean()
            fill_value = median if pd.notna(median) else mean
            clean[column] = clean[column].fillna(fill_value)
        elif column in detected.get("datetime", []):
            clean[column] = clean[column].ffill().bfill()
        elif column in detected.get("boolean", []):
            mode = clean[column].mode(dropna=True)
            clean[column] = clean[column].fillna(mode.iloc[0] if not mode.empty else False)
        else:
            mode = clean[column].mode(dropna=True)
            clean[column] = clean[column].fillna(mode.iloc[0] if not mode.empty else "Unknown")

    missing_after = int(clean.isna().sum().sum())
    report["missing_values_fixed"] = max(missing_before - missing_after, 0)

    numeric_columns = clean.select_dtypes(include=[np.number]).columns
    for column in numeric_columns:
        q1 = clean[column].quantile(0.25)
        q3 = clean[column].quantile(0.75)
        iqr = q3 - q1
        if pd.isna(iqr) or iqr == 0:
            continue
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        mask = (clean[column] < lower) | (clean[column] > upper)
        count = int(mask.sum())
        if count > 0 and count / max(len(clean), 1) <= 0.05:
            clean[column] = clean[column].clip(lower=lower, upper=upper)
            report["outliers_capped"] += count

    report["final_rows"] = int(len(clean))
    report["final_columns"] = int(clean.shape[1])
    report["rows_removed"] = report["starting_rows"] - report["final_rows"]

    return clean, report


# ---- Embedded utils/analyzer.py ----
def analyze_dataset(df: pd.DataFrame, column_types: dict[str, list[str]]) -> dict:
    numeric_cols = list(dict.fromkeys(column_types.get("numeric", []) + column_types.get("currency", []) + column_types.get("percentage", [])))
    numeric_cols = [col for col in numeric_cols if col in df.columns and pd.api.types.is_numeric_dtype(df[col])]

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


def _best_numeric_column(df: pd.DataFrame, column_types: dict[str, list[str]]) -> str | None:
    candidates = column_types.get("currency", []) + column_types.get("numeric", []) + column_types.get("percentage", [])
    candidates = [col for col in candidates if col in df.columns and pd.api.types.is_numeric_dtype(df[col])]
    if not candidates:
        return None
    priority_words = ["revenue", "sales", "amount", "profit", "cost", "price", "total"]
    for word in priority_words:
        for col in candidates:
            if word in col.lower():
                return col
    return max(candidates, key=lambda col: float(df[col].abs().sum()))


def build_kpis(df: pd.DataFrame, summary: dict, column_types: dict[str, list[str]]) -> dict[str, dict[str, str]]:
    value_col = _best_numeric_column(df, column_types)
    kpis: dict[str, dict[str, str]] = {
        "Records": {"value": f"{summary['rows']:,}", "note": f"{summary['columns']:,} columns analyzed"},
        "Data Quality": {"value": f"{100 - summary['missing_pct']:.1f}%", "note": "Completeness score"},
        "Numeric Fields": {"value": f"{summary['numeric_count']:,}", "note": "Measures detected"},
        "Segments": {"value": f"{summary['categorical_count']:,}", "note": "Categorical fields"},
    }
    if value_col:
        total = df[value_col].sum()
        avg = df[value_col].mean()
        kpis["Primary Metric"] = {"value": f"{total:,.2f}", "note": f"Sum of {value_col}; avg {avg:,.2f}"}
    return kpis


# ---- Embedded utils/pivot_engine.py ----
@dataclass
class PivotTable:
    title: str
    slug: str
    data: pd.DataFrame


def _slug(text: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in text).strip("_")


def _numeric_measures(df: pd.DataFrame, column_types: dict[str, list[str]]) -> list[str]:
    cols = column_types.get("currency", []) + column_types.get("numeric", []) + column_types.get("percentage", [])
    return [col for col in dict.fromkeys(cols) if col in df.columns and pd.api.types.is_numeric_dtype(df[col])]


def generate_pivot_tables(df: pd.DataFrame, column_types: dict[str, list[str]], top_n: int = 10) -> list[PivotTable]:
    pivots: list[PivotTable] = []
    numeric_cols = _numeric_measures(df, column_types)
    categorical_cols = [
        col
        for col in column_types.get("categorical", []) + column_types.get("boolean", [])
        if col in df.columns and 1 < df[col].nunique(dropna=True) <= 50
    ]
    date_cols = [col for col in column_types.get("datetime", []) if col in df.columns]

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

    for cat in categorical_cols[:4]:
        pivot = df.groupby(cat, dropna=False).size().reset_index(name="record_count").sort_values("record_count", ascending=False).head(top_n)
        title = f"Record Count by {cat}"
        pivots.append(PivotTable(title=title, slug=_slug(title), data=pivot))

    seen = set()
    unique_pivots = []
    for pivot in pivots:
        if pivot.slug not in seen and not pivot.data.empty:
            seen.add(pivot.slug)
            unique_pivots.append(pivot)
    return unique_pivots[:12]


# ---- Embedded utils/chart_engine.py ----
@dataclass
class ChartSpec:
    title: str
    figure: object


PLOTLY_TEMPLATE = "plotly_white"


def _measures(df: pd.DataFrame, column_types: dict[str, list[str]]) -> list[str]:
    cols = column_types.get("currency", []) + column_types.get("numeric", []) + column_types.get("percentage", [])
    return [col for col in dict.fromkeys(cols) if col in df.columns and pd.api.types.is_numeric_dtype(df[col])]


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
    charts: list[ChartSpec] = []
    numeric_cols = _measures(df, column_types)
    categorical_cols = [
        col
        for col in column_types.get("categorical", []) + column_types.get("boolean", [])
        if col in df.columns and 1 < df[col].nunique(dropna=True) <= 50
    ]
    date_cols = [col for col in column_types.get("datetime", []) if col in df.columns]

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

    for measure in numeric_cols[:4]:
        if df[measure].nunique(dropna=True) > 5:
            title = f"{measure} Distribution"
            fig = px.histogram(df, x=measure, nbins=35, marginal="box", title=title)
            charts.append(ChartSpec(title, _format(fig, title)))

    if len(numeric_cols) >= 2:
        x_col, y_col = numeric_cols[:2]
        title = f"{x_col} vs {y_col}"
        sample = df[[x_col, y_col]].dropna()
        if len(sample) > 0:
            if len(sample) > 3000:
                sample = sample.sample(3000, random_state=42)
            fig = px.scatter(sample, x=x_col, y=y_col, title=title)
            charts.append(ChartSpec(title, _format(fig, title)))

    if len(numeric_cols) >= 3:
        corr = df[numeric_cols[:12]].corr(numeric_only=True)
        title = "Correlation Heatmap"
        fig = px.imshow(corr, text_auto=".2f", aspect="auto", color_continuous_scale="RdBu_r", title=title)
        charts.append(ChartSpec(title, _format(fig, title)))

    return charts[:14]


# ---- Embedded utils/insight_engine.py ----
def _measures(df: pd.DataFrame, column_types: dict[str, list[str]]) -> list[str]:
    cols = column_types.get("currency", []) + column_types.get("numeric", []) + column_types.get("percentage", [])
    return [col for col in dict.fromkeys(cols) if col in df.columns and pd.api.types.is_numeric_dtype(df[col])]


def generate_insights(df: pd.DataFrame, summary: dict, column_types: dict[str, list[str]], pivots: list) -> list[str]:
    insights: list[str] = []
    measures = _measures(df, column_types)
    categorical = [
        col
        for col in column_types.get("categorical", []) + column_types.get("boolean", [])
        if col in df.columns and df[col].nunique(dropna=True) > 1
    ]

    insights.append(
        f"The dataset contains {summary['rows']:,} records across {summary['columns']:,} columns with a {100 - summary['missing_pct']:.1f}% completeness score."
    )

    for cat in categorical[:3]:
        top = df[cat].astype(str).value_counts(dropna=False).head(5)
        if len(top) >= 2:
            concentration = top.iloc[0] / max(top.sum(), 1) * 100
            insights.append(f"{cat} is led by '{top.index[0]}', representing {concentration:.1f}% of the top five observed categories.")

    for measure in measures[:3]:
        series = df[measure].dropna()
        if series.empty:
            continue
        skew = series.skew()
        if abs(skew) > 1:
            direction = "right-skewed" if skew > 0 else "left-skewed"
            insights.append(f"{measure} is {direction}, so averages may be influenced by extreme values.")
        if series.max() > series.mean() + 3 * series.std(ddof=0):
            insights.append(f"{measure} has unusually high peak values that deserve review for opportunities or data quality issues.")

    date_cols = [col for col in column_types.get("datetime", []) if col in df.columns]
    if date_cols and measures:
        date_col = date_cols[0]
        measure = measures[0]
        monthly = (
            df.assign(_month=pd.to_datetime(df[date_col], errors="coerce").dt.to_period("M").dt.to_timestamp())
            .dropna(subset=["_month"])
            .groupby("_month")[measure]
            .sum()
            .sort_index()
        )
        if len(monthly) >= 3:
            change = monthly.iloc[-1] - monthly.iloc[0]
            direction = "increasing" if change > 0 else "declining"
            insights.append(f"{measure} is {direction} over the available monthly timeline from {monthly.index[0].date()} to {monthly.index[-1].date()}.")

    if summary["correlations"].shape[0] >= 2:
        corr = summary["correlations"].where(lambda x: x.abs() < 1).stack().dropna()
        if not corr.empty:
            best_pair = corr.abs().idxmax()
            value = corr.loc[best_pair]
            insights.append(f"{best_pair[0]} and {best_pair[1]} show the strongest detected relationship with correlation {value:.2f}.")

    return insights[:10]


def generate_recommendations(df: pd.DataFrame, summary: dict, column_types: dict[str, list[str]], insights: list[str]) -> list[str]:
    recommendations: list[str] = []
    measures = _measures(df, column_types)
    categorical = column_types.get("categorical", [])

    if summary["missing_pct"] > 5:
        recommendations.append("Data quality warning: missing values exceed 5%, so source-system validation should be reviewed before executive reporting.")
    else:
        recommendations.append("The dataset is clean enough for directional decision-making; continue monitoring missing values as new files arrive.")

    if measures and categorical:
        measure = measures[0]
        cat = categorical[0]
        grouped = df.groupby(cat)[measure].sum().sort_values(ascending=False)
        if len(grouped) >= 3:
            recommendations.append(f"Prioritize the top-performing {cat} segments for growth planning because they drive the largest share of {measure}.")
            recommendations.append(f"Investigate low-performing {cat} segments to separate fixable execution gaps from naturally smaller markets.")

    if column_types.get("datetime") and measures:
        recommendations.append("Review trend charts monthly and compare recent movement against business events, campaigns, or operational changes.")

    if len(measures) >= 2:
        recommendations.append("Use the strongest correlations as hypothesis generators, then validate with domain knowledge before making policy changes.")

    recommendations.append("Export the cleaned workbook and pivot tables as a repeatable analytics pack for finance, operations, or leadership reviews.")
    return recommendations[:8]


# ---- Embedded utils/helpers.py ----
def read_uploaded_file(uploaded_file) -> pd.DataFrame | dict[str, pd.DataFrame]:
    name = uploaded_file.name.lower()
    if name.endswith(".csv"):
        return pd.read_csv(uploaded_file)
    if name.endswith((".xlsx", ".xls")):
        excel = pd.ExcelFile(uploaded_file)
        return {sheet: excel.parse(sheet) for sheet in excel.sheet_names}
    raise ValueError("Unsupported file type")


def dataframe_to_csv(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def dataframe_to_excel(df: pd.DataFrame, pivots: list[Any] | None = None) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Cleaned Data")
        for pivot in pivots or []:
            sheet_name = pivot.title[:31].replace("/", "-").replace("\\", "-")
            pivot.data.to_excel(writer, index=False, sheet_name=sheet_name)
    return output.getvalue()


def render_card(label: str, value: str, note: str = "") -> None:
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


def make_pdf_report(summary: dict, cleaning_report: dict, insights: list[str], recommendations: list[str]) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("Excel AI Analytics Assistant - Executive Summary", styles["Title"]),
        Spacer(1, 12),
        Paragraph("Dataset Overview", styles["Heading2"]),
    ]

    overview = [
        ["Rows", f"{summary['rows']:,}"],
        ["Columns", f"{summary['columns']:,}"],
        ["Missing %", f"{summary['missing_pct']:.2f}%"],
        ["Numeric Fields", f"{summary['numeric_count']:,}"],
        ["Categorical Fields", f"{summary['categorical_count']:,}"],
    ]
    story.append(_styled_table(overview))
    story.extend([Spacer(1, 12), Paragraph("Cleaning Report", styles["Heading2"])])
    story.append(_styled_table([[key.replace("_", " ").title(), str(value)] for key, value in cleaning_report.items()]))

    story.extend([Spacer(1, 12), Paragraph("AI-Style Insights", styles["Heading2"])])
    for insight in insights:
        story.append(Paragraph(f"- {insight}", styles["BodyText"]))
        story.append(Spacer(1, 4))

    story.extend([Spacer(1, 10), Paragraph("Recommendations", styles["Heading2"])])
    for recommendation in recommendations:
        story.append(Paragraph(f"- {recommendation}", styles["BodyText"]))
        story.append(Spacer(1, 4))

    doc.build(story)
    return buffer.getvalue()


def _styled_table(rows: list[list[str]]) -> Table:
    table = Table(rows, hAlign="LEFT", colWidths=[180, 300])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEF4FF")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#172033")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D0D5DD")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("PADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return table


st.set_page_config(
    page_title="Excel AI Analytics Assistant",
    page_icon=":bar_chart:",
    layout="wide",
    initial_sidebar_state="expanded",
)


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --card-bg: rgba(255,255,255,.78);
            --card-border: rgba(99, 102, 241, .18);
            --ink: #172033;
            --muted: #667085;
            --accent: #2563eb;
        }
        .stApp {
            background:
                radial-gradient(circle at top left, rgba(37,99,235,.12), transparent 28rem),
                linear-gradient(180deg, #f8fafc 0%, #eef4ff 100%);
            color: var(--ink);
        }
        [data-testid="stSidebar"] {
            background: #101828;
            color: #fff;
        }
        [data-testid="stSidebar"] * {
            color: inherit;
        }
        .hero {
            padding: 1.25rem 0 .8rem;
        }
        .hero h1 {
            font-size: clamp(2rem, 4vw, 3.4rem);
            line-height: 1.05;
            margin: 0;
            letter-spacing: 0;
        }
        .hero p {
            color: var(--muted);
            font-size: 1.05rem;
            margin-top: .65rem;
            max-width: 58rem;
        }
        .metric-card {
            border: 1px solid var(--card-border);
            background: var(--card-bg);
            border-radius: 8px;
            padding: 1rem 1.1rem;
            box-shadow: 0 10px 28px rgba(16,24,40,.07);
            min-height: 112px;
        }
        .metric-card .label {
            color: var(--muted);
            font-size: .82rem;
            text-transform: uppercase;
            letter-spacing: .08em;
        }
        .metric-card .value {
            color: var(--ink);
            font-size: 1.85rem;
            font-weight: 750;
            margin-top: .3rem;
            overflow-wrap: anywhere;
        }
        .metric-card .note {
            color: var(--muted);
            font-size: .9rem;
            margin-top: .2rem;
        }
        .section-title {
            font-size: 1.35rem;
            font-weight: 760;
            margin: 1.4rem 0 .55rem;
        }
        .insight {
            border-left: 4px solid #2563eb;
            background: rgba(255,255,255,.72);
            border-radius: 8px;
            padding: .8rem 1rem;
            margin-bottom: .65rem;
            color: #1d2939;
        }
        .warning {
            border-left-color: #f97316;
        }
        div[data-testid="stDataFrame"] {
            border: 1px solid rgba(16,24,40,.08);
            border-radius: 8px;
            overflow: hidden;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_metric_cards(kpis: dict[str, dict[str, str]]) -> None:
    cols = st.columns(min(4, max(1, len(kpis))))
    for idx, (label, metric) in enumerate(kpis.items()):
        with cols[idx % len(cols)]:
            render_card(label, metric["value"], metric.get("note", ""))


def filter_dataframe(df: pd.DataFrame, column_types: dict[str, list[str]]) -> pd.DataFrame:
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


def main() -> None:
    inject_styles()

    st.markdown(
        """
        <div class="hero">
            <h1>Excel AI Analytics Assistant</h1>
            <p>Upload a spreadsheet and get automated cleaning, executive KPIs, pivot tables,
            visual analytics, and business-friendly recommendations in one dashboard.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.subheader("Upload Panel")
        uploaded_file = st.file_uploader(
            "Drop an Excel or CSV file",
            type=["xlsx", "xls", "csv"],
            accept_multiple_files=False,
        )
        st.caption("Supported formats: .xlsx, .xls, .csv")

    if uploaded_file is None:
        st.markdown('<div class="section-title">Upload Dataset</div>', unsafe_allow_html=True)
        uploaded_file = st.file_uploader(
            "Upload an Excel or CSV file",
            type=["xlsx", "xls", "csv"],
            accept_multiple_files=False,
            key="main_upload",
        )
        st.info("Upload a dataset to start the analytics workflow.")
        if uploaded_file is None:
            st.stop()

    workbook = read_uploaded_file(uploaded_file)
    sheet_name = None
    if isinstance(workbook, dict):
        with st.sidebar:
            sheet_name = st.selectbox("Workbook sheet", list(workbook.keys()))
        raw_df = workbook[sheet_name]
    else:
        raw_df = workbook

    if raw_df.empty:
        st.error("The selected file or sheet is empty.")
        st.stop()

    raw_df.columns = [str(col).strip() for col in raw_df.columns]
    raw_types = detect_column_types(raw_df)
    cleaned_df, cleaning_report = clean_data(raw_df)
    column_types = detect_column_types(cleaned_df)
    filtered_df = filter_dataframe(cleaned_df, column_types)

    summary = analyze_dataset(filtered_df, column_types)
    kpis = build_kpis(filtered_df, summary, column_types)
    pivots = generate_pivot_tables(filtered_df, column_types)
    charts = generate_charts(filtered_df, column_types)
    insights = generate_insights(filtered_df, summary, column_types, pivots)
    recommendations = generate_recommendations(filtered_df, summary, column_types, insights)

    tabs = st.tabs(
        [
            "Dataset",
            "Executive Summary",
            "Visual Analytics",
            "Pivot Tables",
            "AI Insights",
            "Downloads",
        ]
    )

    with tabs[0]:
        st.markdown('<div class="section-title">Dataset Preview</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1:
            render_card("Rows", f"{len(raw_df):,}", "Original dataset")
        with c2:
            render_card("Columns", f"{raw_df.shape[1]:,}", "Detected fields")
        with c3:
            render_card("Filtered Rows", f"{len(filtered_df):,}", "After sidebar filters")

        st.dataframe(raw_df.head(150), use_container_width=True)
        st.markdown('<div class="section-title">Column Information</div>', unsafe_allow_html=True)
        column_info = pd.DataFrame(
            {
                "column": raw_df.columns,
                "dtype": [str(raw_df[col].dtype) for col in raw_df.columns],
                "non_null": [int(raw_df[col].notna().sum()) for col in raw_df.columns],
                "missing": [int(raw_df[col].isna().sum()) for col in raw_df.columns],
                "unique": [int(raw_df[col].nunique(dropna=True)) for col in raw_df.columns],
                "detected_type": [
                    next((kind for kind, cols in raw_types.items() if col in cols), "unknown")
                    for col in raw_df.columns
                ],
            }
        )
        st.dataframe(column_info, use_container_width=True, hide_index=True)

        st.markdown('<div class="section-title">Cleaning Report</div>', unsafe_allow_html=True)
        st.dataframe(pd.DataFrame([cleaning_report]), use_container_width=True, hide_index=True)
        st.dataframe(cleaned_df.head(150), use_container_width=True)

    with tabs[1]:
        st.markdown('<div class="section-title">Executive Summary</div>', unsafe_allow_html=True)
        render_metric_cards(kpis)

        st.markdown('<div class="section-title">Statistical Analysis</div>', unsafe_allow_html=True)
        if summary["statistics"].empty:
            st.caption("No numeric columns are available for statistical profiling.")
        else:
            st.dataframe(summary["statistics"], use_container_width=True)

        if not summary["correlations"].empty:
            st.markdown('<div class="section-title">Correlation Matrix</div>', unsafe_allow_html=True)
            st.dataframe(summary["correlations"], use_container_width=True)

        if summary["date_ranges"]:
            st.markdown('<div class="section-title">Date Ranges</div>', unsafe_allow_html=True)
            st.dataframe(pd.DataFrame(summary["date_ranges"]), use_container_width=True, hide_index=True)

    with tabs[2]:
        st.markdown('<div class="section-title">Visual Analytics</div>', unsafe_allow_html=True)
        if not charts:
            st.warning("No valid chart combinations were detected for this dataset.")
        for chart in charts:
            st.plotly_chart(chart.figure, use_container_width=True)

    with tabs[3]:
        st.markdown('<div class="section-title">Smart Pivot Tables</div>', unsafe_allow_html=True)
        if not pivots:
            st.warning("No valid pivot tables were generated from the available columns.")
        for pivot in pivots:
            with st.expander(pivot.title, expanded=True):
                st.dataframe(pivot.data, use_container_width=True, hide_index=True)
                st.download_button(
                    "Download CSV",
                    dataframe_to_csv(pivot.data),
                    file_name=f"{pivot.slug}.csv",
                    mime="text/csv",
                    key=f"pivot-{pivot.slug}",
                )

    with tabs[4]:
        st.markdown('<div class="section-title">AI-Style Insights</div>', unsafe_allow_html=True)
        for item in insights:
            st.markdown(f'<div class="insight">{item}</div>', unsafe_allow_html=True)

        st.markdown('<div class="section-title">Recommendations</div>', unsafe_allow_html=True)
        for item in recommendations:
            css = "insight warning" if "warning" in item.lower() or "risk" in item.lower() else "insight"
            st.markdown(f'<div class="{css}">{item}</div>', unsafe_allow_html=True)

    with tabs[5]:
        st.markdown('<div class="section-title">Download Reports</div>', unsafe_allow_html=True)
        excel_bytes = dataframe_to_excel(cleaned_df, pivots)
        csv_bytes = dataframe_to_csv(cleaned_df)
        pdf_bytes = make_pdf_report(summary, cleaning_report, insights, recommendations)

        d1, d2, d3 = st.columns(3)
        with d1:
            st.download_button(
                "Cleaned Excel",
                excel_bytes,
                file_name="cleaned_analytics_workbook.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        with d2:
            st.download_button("Cleaned CSV", csv_bytes, file_name="cleaned_dataset.csv", mime="text/csv")
        with d3:
            st.download_button("PDF Summary", pdf_bytes, file_name="executive_summary.pdf", mime="application/pdf")

        st.caption("Chart PNG export is available from each Plotly chart toolbar using the camera icon.")


if __name__ == "__main__":
    main()
