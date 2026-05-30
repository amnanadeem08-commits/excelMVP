"""Excel/CSV input system.

Reads uploaded spreadsheets, supports multiple sheets, and detects the
structure of a dataset automatically so the rest of the pipeline can react
to the shape of the data.

CUSTOMIZE: To support more file types (e.g. .json, .parquet), add a branch
in ``read_uploaded_file`` and return either a single DataFrame or a
``{sheet_name: DataFrame}`` mapping for multi-sheet sources.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from data_cleaning import detect_column_types


def read_uploaded_file(uploaded_file) -> pd.DataFrame | dict[str, pd.DataFrame]:
    """Read an uploaded file into a DataFrame or a dict of sheets.

    Returns a single ``DataFrame`` for CSV files and a
    ``{sheet_name: DataFrame}`` dict for Excel workbooks so multi-sheet
    files are fully supported.
    """
    name = uploaded_file.name.lower()
    if name.endswith(".csv"):
        return pd.read_csv(uploaded_file)
    if name.endswith((".xlsx", ".xls")):
        excel = pd.ExcelFile(uploaded_file)
        return {sheet: excel.parse(sheet) for sheet in excel.sheet_names}
    raise ValueError("Unsupported file type. Please upload .xlsx, .xls, or .csv.")


def list_sheets(workbook: pd.DataFrame | dict[str, pd.DataFrame]) -> list[str]:
    """Return the available sheet names (single CSV reports one logical sheet)."""
    if isinstance(workbook, dict):
        return list(workbook.keys())
    return ["Sheet1"]


def select_sheet(
    workbook: pd.DataFrame | dict[str, pd.DataFrame],
    sheet_name: str | None = None,
) -> pd.DataFrame:
    """Pick a sheet from a workbook, defaulting to the first one."""
    if isinstance(workbook, dict):
        if sheet_name is None:
            sheet_name = next(iter(workbook))
        return workbook[sheet_name]
    return workbook


def normalize_headers(df: pd.DataFrame) -> pd.DataFrame:
    """Light header trim so structure detection is stable before deep cleaning."""
    df = df.copy()
    df.columns = [str(col).strip() for col in df.columns]
    return df


def detect_structure(df: pd.DataFrame) -> dict[str, Any]:
    """Automatically describe the structure of a dataset.

    Provides a quick, business-friendly snapshot (rows, columns, detected
    column roles, missing values) without mutating the data.
    """
    column_types = detect_column_types(df)
    total_cells = max(int(df.shape[0] * df.shape[1]), 1)
    missing_total = int(df.isna().sum().sum())
    return {
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "column_types": column_types,
        "missing_total": missing_total,
        "missing_pct": round(missing_total / total_cells * 100, 2),
        "has_dates": bool(column_types.get("datetime")),
        "has_measures": bool(
            column_types.get("numeric")
            or column_types.get("currency")
            or column_types.get("percentage")
        ),
    }
