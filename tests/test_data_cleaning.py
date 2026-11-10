"""Tests for data_cleaning.py: type detection and the cleaning pipeline."""

from __future__ import annotations

import pandas as pd

from data_cleaning import clean_data, detect_column_types


def test_detect_column_types_mixed_frame():
    df = pd.DataFrame(
        {
            "Revenue": [100.0, 200.0, 300.0],
            "Price Text": ["$1,234.50", "$99.00", "$10.00"],
            "Margin": ["12%", "8.5%", "30%"],
            "Signed Up": ["yes", "no", "yes"],
            "City": ["Paris", "Berlin", "Madrid"],
            "Joined": ["2024-01-01", "2024-02-01", "2024-03-01"],
        }
    )
    types = detect_column_types(df)
    assert "Revenue" in types["numeric"]
    assert "Price Text" in types["currency"]
    assert "Margin" in types["percentage"]
    assert "Signed Up" in types["boolean"]
    assert "City" in types["categorical"]
    assert "Joined" in types["datetime"]


def test_detect_column_types_empty_frame():
    assert all(len(v) == 0 for v in detect_column_types(pd.DataFrame()).values())


def test_detect_column_types_text_only_frame():
    df = pd.DataFrame({"name": ["a", "b", "c"], "city": ["x", "y", "z"]})
    types = detect_column_types(df)
    assert types["numeric"] == []
    assert set(types["categorical"]) | set(types["text"]) == {"name", "city"}


def test_clean_data_removes_duplicates_and_reports(sales_df):
    dirty = pd.concat([sales_df, sales_df.head(5)], ignore_index=True)
    dirty["Empty Col"] = None
    cleaned, report = clean_data(dirty)

    assert report["starting_rows"] == 65
    assert report["duplicates_removed"] == 5
    assert report["empty_columns_removed"] == 1
    assert report["final_rows"] == 60
    assert "Empty Col" not in cleaned.columns
    assert not cleaned.duplicated().any()
    for key in ("missing_values_fixed", "outliers_capped", "columns_corrected"):
        assert key in report


def test_clean_data_fills_missing_values(sales_df):
    dirty = sales_df.copy()
    dirty.loc[dirty.index[:5], "Revenue"] = None
    dirty.loc[dirty.index[:3], "Region"] = None
    cleaned, report = clean_data(dirty)
    assert cleaned["Revenue"].isna().sum() == 0
    assert cleaned["Region"].isna().sum() == 0
    assert report["missing_values_fixed"] >= 8


def test_clean_data_converts_currency_strings():
    df = pd.DataFrame({"Amount": ["$1,000.00", "$2,000.50", "N/A"]})
    cleaned, _ = clean_data(df)
    assert pd.api.types.is_numeric_dtype(cleaned["Amount"])
    assert cleaned["Amount"].iloc[0] == 1000.0


def test_clean_data_does_not_mutate_input(sales_df):
    before = sales_df.copy()
    clean_data(sales_df)
    pd.testing.assert_frame_equal(sales_df, before)
