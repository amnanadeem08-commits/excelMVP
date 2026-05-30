"""Data cleaning engine (Pandas).

Handles the heavy lifting that a freelancer would otherwise do by hand in
Excel: standardize column names, detect column types, fix data types,
remove duplicates/empty columns, fill missing values intelligently, and cap
extreme outliers. Every run returns a transparent cleaning report.

CUSTOMIZE:
- Tune the missing-value strategy in ``clean_data`` (median vs mean vs mode).
- Adjust outlier sensitivity by changing the IQR multiplier (default 1.5).
- Add domain keywords to the currency/percentage detectors below.
"""

from __future__ import annotations

import re
from typing import Any

import numpy as np
import pandas as pd


CURRENCY_RE = re.compile(
    r"^\s*[\$€£₹¥]?\s*-?\d{1,3}(,\d{3})*(\.\d+)?\s*$|^\s*[\$€£₹¥]?\s*-?\d+(\.\d+)?\s*$"
)
PERCENT_RE = re.compile(r"^\s*-?\d+(\.\d+)?\s*%\s*$")

# CUSTOMIZE: keywords that hint a text column is really money or a rate.
CURRENCY_KEYWORDS = ["revenue", "sales", "price", "cost", "amount", "profit", "total"]
PERCENT_KEYWORDS = ["rate", "percent", "percentage", "margin"]


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
    """Infer business-friendly column types beyond raw pandas dtypes."""
    types: dict[str, list[str]] = {
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
            if any(token in lower_name for token in PERCENT_KEYWORDS):
                types["percentage"].append(column)
            else:
                types["numeric"].append(column)
            continue

        if _looks_like_percent(series):
            types["percentage"].append(column)
            continue

        if _looks_like_currency(series) or any(token in str(column).lower() for token in CURRENCY_KEYWORDS):
            numeric_try = _currency_to_numeric(series)
            if numeric_try.notna().mean() >= 0.65:
                types["currency"].append(column)
                continue

        datetime_try = pd.to_datetime(series, errors="coerce")
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
    """Clean an uploaded dataset and return ``(clean_df, cleaning_report)``."""
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

    # 1. Standardize column names (trim, collapse whitespace, de-duplicate).
    clean.columns = _clean_column_names(clean.columns)

    # 2. Trim text values and normalize empty placeholders to NA.
    object_columns = clean.select_dtypes(include=["object", "string"]).columns
    for column in object_columns:
        clean[column] = clean[column].astype("string").str.strip()
        clean[column] = clean[column].replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})

    # 3. Drop completely empty columns.
    empty_columns = [column for column in clean.columns if clean[column].isna().all()]
    clean = clean.drop(columns=empty_columns)
    report["empty_columns_removed"] = len(empty_columns)

    # 4. Remove duplicate rows.
    duplicates = int(clean.duplicated().sum())
    clean = clean.drop_duplicates().reset_index(drop=True)
    report["duplicates_removed"] = duplicates
    report["rows_removed"] += duplicates

    # 5. Detect + fix data types (currency, percent, dates, numbers, booleans).
    detected = detect_column_types(clean)
    clean = _fix_types(clean, detected, report)
    detected = detect_column_types(clean)

    # 6. Handle missing values intelligently per detected type.
    missing_before = int(clean.isna().sum().sum())
    numeric_like = set(
        detected.get("numeric", []) + detected.get("currency", []) + detected.get("percentage", [])
    )
    for column in clean.columns:
        if clean[column].isna().sum() == 0:
            continue
        if column in numeric_like:
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

    # 7. Cap extreme outliers (only when they are a small share of the data).
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
