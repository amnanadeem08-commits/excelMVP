"""Tests for analytics_engine.py: KPIs, pivots, growth, statistics."""

from __future__ import annotations

import pandas as pd
import pytest

from analytics_engine import (
    analyze_dataset,
    best_numeric_column,
    build_kpis,
    compute_growth,
    generate_pivot_tables,
    numeric_measures,
)
from data_cleaning import clean_data, detect_column_types


def _prepared(sales_df):
    cleaned, _ = clean_data(sales_df)
    return cleaned, detect_column_types(cleaned)


def test_best_numeric_column_prefers_business_words(sales_df):
    cleaned, types = _prepared(sales_df)
    # "Revenue" outranks "Units" by PRIORITY_METRIC_WORDS
    assert best_numeric_column(cleaned, types) == "Revenue"
    assert "Revenue" in numeric_measures(cleaned, types)
    assert "Units" in numeric_measures(cleaned, types)


def test_best_numeric_column_none_without_measures():
    df = pd.DataFrame({"name": ["a", "b"], "city": ["x", "y"]})
    assert best_numeric_column(df, detect_column_types(df)) is None


def test_best_numeric_column_skips_identifier_columns():
    """Numeric ID / constant columns must never become the headline metric."""
    df = pd.DataFrame(
        {
            "Customer ID": [101, 102, 103, 104, 105],
            "Row Number": [1, 2, 3, 4, 5],
            "Units": [3.0, 5.0, 2.0, 8.0, 1.0],
        }
    )
    types = detect_column_types(df)
    assert best_numeric_column(df, types) == "Units"


def test_best_numeric_column_none_when_only_identifiers():
    df = pd.DataFrame({"Customer ID": [1, 2, 3, 4], "Code": [10, 20, 30, 40]})
    types = detect_column_types(df)
    assert best_numeric_column(df, types) is None


def test_build_kpis_structure(sales_df):
    cleaned, types = _prepared(sales_df)
    summary = analyze_dataset(cleaned, types)
    kpis = build_kpis(cleaned, summary, types)

    assert "Records" in kpis and kpis["Records"]["value"] == "60"
    assert "Data Quality" in kpis
    assert "Total Revenue" in kpis and kpis["Total Revenue"]["note"] == "Sum of Revenue"
    assert "Average Revenue" in kpis
    for metric in kpis.values():
        assert "value" in metric and "note" in metric


def test_build_kpis_formats_percentage_measure():
    """Rate measures show an averaged percentage, never a meaningless total."""
    df = pd.DataFrame({"Margin": [0.12, 0.25, 0.30], "Region": ["a", "b", "c"]})
    types = detect_column_types(df)
    kpis = build_kpis(df, analyze_dataset(df, types), types)
    assert not any(key.startswith("Total") for key in kpis)
    avg_key = next(key for key in kpis if key.startswith("Average"))
    assert kpis[avg_key]["value"] == "22.3%"  # mean(0.12, 0.25, 0.30) as a percentage


def test_measure_semantics_classification():
    """EXECUTIVE_STORY §4: totals only suit additive measures."""
    from analytics_engine import measure_semantics

    assert measure_semantics("Revenue") == "additive"
    assert measure_semantics("Units Shipped") == "additive"
    assert measure_semantics("Age") == "continuous"
    assert measure_semantics("Unit Price") == "continuous"
    assert measure_semantics("Customer Satisfaction") == "continuous"
    assert measure_semantics("Margin") == "rate"
    assert measure_semantics("Any Column", {"percentage": ["Any Column"]}) == "rate"


def test_build_kpis_continuous_measure_has_no_total():
    """A total of ages is misleading: continuous measures show Average + Median."""
    df = pd.DataFrame({"Age": [25, 35, 45, 55], "Department": ["HR", "IT", "HR", "IT"]})
    types = detect_column_types(df)
    kpis = build_kpis(df, analyze_dataset(df, types), types)
    assert not any(key.startswith("Total") for key in kpis)
    assert kpis["Average Age"]["value"] == "40.00"
    assert kpis["Median Age"]["value"] == "40.00"


def test_build_kpis_explicit_overrides():
    """User overrides (DESIGN.md §2 step 5) beat automatic selection."""
    df = pd.DataFrame(
        {
            "Revenue": [100.0, 200.0, 300.0],
            "Units": [1.0, 3.0, 5.0],
            "Region": ["a", "b", "c"],
        }
    )
    types = detect_column_types(df)
    kpis = build_kpis(df, analyze_dataset(df, types), types, measure="Units", agg="median")
    assert "Median Units" in kpis and kpis["Median Units"]["value"] == "3.00"
    assert not any(key.startswith("Total Revenue") for key in kpis)


def test_compute_growth_respects_mean_aggregation():
    """Growth for continuous measures compares monthly averages, not sums."""
    df = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2024-01-01", "2024-01-15", "2024-02-10"]),
            "Age": [30.0, 40.0, 60.0],
        }
    )
    growth = compute_growth(df, detect_column_types(df), "Age", agg="mean")
    assert growth is not None
    assert growth["growth_pct"] == pytest.approx(71.4, abs=0.1)  # mean 35 -> 60


def test_build_kpis_growth_shows_magnitude_only():
    """Growth card must not show a double negative (e.g. '▼ -12.3%')."""
    df = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2024-01-01", "2024-02-01", "2024-03-01"]),
            "Revenue": [100.0, 150.0, 60.0],
        }
    )
    types = detect_column_types(df)
    kpis = build_kpis(df, analyze_dataset(df, types), types)
    growth = kpis["Growth"]["value"]
    assert growth.startswith("▼")
    assert "-" not in growth.replace("→", "")  # magnitude only, arrow shows direction


def test_build_kpis_text_only_fallback():
    df = pd.DataFrame({"name": ["a", "b", "c"], "city": ["x", "y", "z"]})
    types = detect_column_types(df)
    kpis = build_kpis(df, analyze_dataset(df, types), types)
    assert "Numeric Fields" in kpis
    assert "Segments" in kpis
    assert "Total" not in kpis


def test_analyze_dataset_statistics_and_dates(sales_df):
    cleaned, types = _prepared(sales_df)
    summary = analyze_dataset(cleaned, types)

    assert summary["rows"] == 60
    assert summary["numeric_count"] >= 2
    assert not summary["statistics"].empty
    assert "median" in summary["statistics"].columns
    assert summary["date_ranges"], "expected a date range for Order Date"
    assert summary["date_ranges"][0]["column"] == "Order Date"
    assert summary["correlations"].shape[0] >= 2


def test_compute_growth_over_two_periods():
    df = pd.DataFrame(
        {
            "Month": pd.to_datetime(["2024-01-01", "2024-02-01", "2024-03-01"]),
            "Revenue": [100.0, 150.0, 300.0],
        }
    )
    types = detect_column_types(df)
    growth = compute_growth(df, types, "Revenue")
    assert growth is not None
    assert growth["growth_pct"] == 200.0  # 100 -> 300
    assert growth["periods"] == 3


def test_compute_growth_none_without_dates():
    df = pd.DataFrame({"Revenue": [1.0, 2.0, 3.0]})
    types = detect_column_types(df)
    assert compute_growth(df, types, "Revenue") is None


def test_generate_pivot_tables_titles_and_uniqueness(sales_df):
    cleaned, types = _prepared(sales_df)
    pivots = generate_pivot_tables(cleaned, types)

    assert pivots, "expected at least one pivot"
    titles = [p.title for p in pivots]
    slugs = [p.slug for p in pivots]
    assert len(titles) == len(set(titles))
    assert len(slugs) == len(set(slugs))
    assert all(not p.data.empty for p in pivots)
    assert any("by Region" in t for t in titles)
    assert any("by Month" in t for t in titles)


def test_category_pivots_include_share_of_total(sales_df):
    """Category pivots carry a share_pct column relative to the full total."""
    cleaned, types = _prepared(sales_df)
    pivots = generate_pivot_tables(cleaned, types)
    by_region = next(p for p in pivots if p.title == "Revenue by Region")
    assert "share_pct" in by_region.data.columns
    expected_total = cleaned["Revenue"].sum()
    top_share = by_region.data.iloc[0]["sum"] / expected_total * 100
    assert by_region.data.iloc[0]["share_pct"] == pytest.approx(round(top_share, 1))
    count_pivot = next(p for p in pivots if p.title.startswith("Record Count by"))
    assert "share_pct" in count_pivot.data.columns


def test_generate_pivot_tables_empty_without_categories():
    df = pd.DataFrame({"Revenue": [1.0, 2.0, 3.0]})
    types = detect_column_types(df)
    assert generate_pivot_tables(df, types) == []
