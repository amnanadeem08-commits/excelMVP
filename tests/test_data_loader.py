"""Tests for data_loader.py: file reading, sheets, headers, structure."""

from __future__ import annotations

import pandas as pd
import pytest

from data_loader import (
    detect_structure,
    list_sheets,
    normalize_headers,
    read_uploaded_file,
    select_sheet,
)


def test_read_csv_returns_dataframe(csv_upload):
    workbook = read_uploaded_file(csv_upload)
    assert isinstance(workbook, pd.DataFrame)
    assert len(workbook) == 60
    assert "Revenue" in workbook.columns


def test_read_excel_returns_sheet_dict(xlsx_upload):
    workbook = read_uploaded_file(xlsx_upload)
    assert isinstance(workbook, dict)
    assert list_sheets(workbook) == ["Sales", "Recent"]
    assert len(workbook["Sales"]) == 60
    assert len(workbook["Recent"]) == 10


def test_read_unsupported_type_raises(csv_upload):
    csv_upload.name = "data.txt"
    with pytest.raises(ValueError, match="Unsupported file type"):
        read_uploaded_file(csv_upload)


def test_select_sheet_defaults_to_first(xlsx_upload):
    workbook = read_uploaded_file(xlsx_upload)
    assert len(select_sheet(workbook, None)) == 60
    assert len(select_sheet(workbook, "Recent")) == 10


def test_select_sheet_passes_through_single_dataframe(csv_upload):
    workbook = read_uploaded_file(csv_upload)
    assert select_sheet(workbook, "anything") is workbook
    assert list_sheets(workbook) == ["Sheet1"]


def test_normalize_headers_strips_whitespace(sales_df):
    df = sales_df[["Order ID", "Region", "Revenue"]].copy()
    df.columns = ["  Order ID ", "Region  ", "Revenue"]
    cleaned = normalize_headers(df)
    assert list(cleaned.columns) == ["Order ID", "Region", "Revenue"]
    # does not mutate the original frame
    assert list(df.columns)[0].startswith("  ")


def test_detect_structure_reports_shape_and_roles(sales_df):
    structure = detect_structure(sales_df)
    assert structure["rows"] == 60
    assert structure["columns"] == 6
    assert structure["has_dates"] is True
    assert structure["has_measures"] is True
    assert structure["missing_total"] == 0
    assert 0 <= structure["missing_pct"] <= 100
