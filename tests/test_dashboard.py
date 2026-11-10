"""Tests for dashboard.py: chart generation options and the custom builder."""

from __future__ import annotations

import pandas as pd
import pytest

from data_cleaning import clean_data, detect_column_types
from dashboard import (
    CHART_GUIDE,
    CHART_TYPE_LABELS,
    available_chart_types,
    build_custom_chart,
    generate_charts,
    get_default_theme,
    _sort_aggregate,
)


def _prepared(sales_df):
    cleaned, _ = clean_data(sales_df)
    return cleaned, detect_column_types(cleaned)


def test_available_chart_types_full_dataset():
    df = pd.DataFrame(
        {
            "Revenue": [1.0, 2.0, 3.0],
            "Units": [4.0, 5.0, 6.0],
            "Margin": [0.1, 0.2, 0.3],
            "Region": ["a", "b", "c"],
            "Date": pd.to_datetime(["2024-01-01", "2024-02-01", "2024-03-01"]),
        }
    )
    kinds = available_chart_types(detect_column_types(df))
    assert set(kinds) == {"line", "bar", "pie", "histogram", "scatter", "heatmap"}


def test_available_chart_types_text_only():
    # High-cardinality free text -> no measures, dates, or categories to chart.
    n = 60
    df = pd.DataFrame(
        {"a": [f"txt{i}" for i in range(n)], "b": [f"val{i}" for i in range(n)]}
    )
    types = detect_column_types(df)
    assert available_chart_types(types) == []


def test_available_chart_types_two_measures_no_heatmap():
    df = pd.DataFrame({"Revenue": [1.0, 2.0], "Units": [3.0, 4.0], "Region": ["a", "b"]})
    kinds = available_chart_types(detect_column_types(df))
    assert "scatter" in kinds
    assert "heatmap" not in kinds


def test_chart_guide_covers_all_selectable_types():
    guides = {entry["chart"] for entry in CHART_GUIDE}
    # Guide uses friendlier names; make sure every selectable type is explained.
    assert {"Bar", "Line", "Pie / Donut", "Histogram", "Scatter"} <= guides
    assert "Correlation heatmap" in guides
    for entry in CHART_GUIDE:
        assert entry["use_when"] and entry["avoid_when"]


def test_generate_charts_filters_by_type(sales_df):
    _, types = _prepared(sales_df)
    only_bars = generate_charts(sales_df, types, get_default_theme(), chart_types=["bar"])
    assert only_bars
    assert all(chart.kind == "bar" for chart in only_bars)


def test_generate_charts_empty_when_no_types_selected(sales_df):
    _, types = _prepared(sales_df)
    assert generate_charts(sales_df, types, get_default_theme(), chart_types=[]) == []


def test_heatmap_survives_many_other_charts():
    """Regression: a global chart cap used to drop the heatmap entirely."""
    rng_df = pd.DataFrame(
        {
            **{f"Cat {i}": [f"g{j}" for j in range(30)] for i in range(4)},
            "Revenue": range(30),
            "Units": range(30, 60),
            "Margin": [x / 100 for x in range(30)],
            "Date": pd.date_range("2024-01-01", periods=30, freq="D"),
        }
    )
    types = detect_column_types(rng_df)
    charts = generate_charts(rng_df, types, get_default_theme())
    kinds = {chart.kind for chart in charts}
    assert "heatmap" in kinds
    # Per-type caps keep the dashboard bounded.
    assert len(charts) <= 20


def test_generate_charts_top_n_limits_categories(sales_df):
    _, types = _prepared(sales_df)
    charts = generate_charts(sales_df, types, get_default_theme(), chart_types=["bar"], top_n=3)
    assert charts
    for chart in charts:
        trace = chart.figure.data[0]
        # v-bars expose categories on x, h-bars on y
        cats = trace.x if trace.x is not None else trace.y
        assert len(cats) <= 3


def test_sort_aggregate_orders():
    frame = pd.DataFrame({"cat": ["b", "a", "c"], "val": [1, 3, 2]})
    assert list(_sort_aggregate(frame, "cat", "val", "desc")["cat"]) == ["a", "c", "b"]
    assert list(_sort_aggregate(frame, "cat", "val", "asc")["cat"]) == ["b", "c", "a"]
    assert list(_sort_aggregate(frame, "cat", "val", "alpha")["cat"]) == ["a", "b", "c"]


def test_build_custom_chart_bar_with_title_and_labels(sales_df):
    cleaned, _ = _prepared(sales_df)
    spec = build_custom_chart(
        cleaned, "Bar", "Region", "Revenue", agg="sum",
        title="Revenue by Region (custom)", theme=get_default_theme(),
        x_label="Region", y_label="USD",
    )
    assert spec.kind == "bar"
    assert spec.title == "Revenue by Region (custom)"
    assert spec.figure.layout.title.text == "Revenue by Region (custom)"
    assert spec.figure.layout.yaxis.title.text == "USD"


def test_build_custom_chart_automatic_title(sales_df):
    cleaned, _ = _prepared(sales_df)
    spec = build_custom_chart(cleaned, "Bar", "Region", "Revenue", agg="mean", theme=get_default_theme())
    assert spec.title == "Mean of Revenue by Region"


def test_build_custom_chart_missing_column_raises(sales_df):
    cleaned, _ = _prepared(sales_df)
    with pytest.raises(ValueError, match="was not found in the dataset"):
        build_custom_chart(cleaned, "Bar", "Not A Column", "Revenue")


def test_build_custom_chart_histogram_on_text_raises(sales_df):
    cleaned, _ = _prepared(sales_df)
    with pytest.raises(ValueError, match="not numeric"):
        build_custom_chart(cleaned, "Histogram", "Region")


def test_build_custom_chart_scatter_requires_y(sales_df):
    cleaned, _ = _prepared(sales_df)
    with pytest.raises(ValueError, match="both an X and a Y"):
        build_custom_chart(cleaned, "Scatter", "Revenue")


def test_build_custom_chart_pie_rejects_many_segments():
    df = pd.DataFrame(
        {"Segment": [f"s{i % 12}" for i in range(60)], "Revenue": range(60)}
    )
    types = detect_column_types(df)
    assert "pie" in available_chart_types(types)
    with pytest.raises(ValueError, match="8 segments or fewer"):
        build_custom_chart(df, "Pie / Donut", "Segment", "Revenue")


def test_build_custom_chart_line_needs_date_or_numeric_x(sales_df):
    cleaned, _ = _prepared(sales_df)
    # Region is categorical text -> unusable X for a line chart
    with pytest.raises(ValueError, match="date column"):
        build_custom_chart(cleaned, "Line", "Region", "Revenue")
    # Order Date works
    spec = build_custom_chart(cleaned, "Line", "Order Date", "Revenue", theme=get_default_theme())
    assert spec.kind == "line"


def test_build_custom_chart_count_mode(sales_df):
    cleaned, _ = _prepared(sales_df)
    spec = build_custom_chart(cleaned, "Bar", "Region", None, theme=get_default_theme())
    assert spec.title == "Record Count by Region"
