"""Tests for export_module.py: CSV, Excel, summary report, PDF and PPT."""

from __future__ import annotations

from io import BytesIO

import pandas as pd

from analytics_engine import PivotTable, analyze_dataset, build_kpis, generate_pivot_tables
from data_cleaning import clean_data, detect_column_types
from export_module import (
    dataframe_to_csv,
    dataframe_to_excel,
    export_summary_report,
    make_custom_pdf_report,
    make_ppt_report,
)
from ai_insights import generate_ai_insights
from dashboard import generate_charts, get_default_theme


def _pipeline(sales_df):
    cleaned, report = clean_data(sales_df)
    types = detect_column_types(cleaned)
    summary = analyze_dataset(cleaned, types)
    kpis = build_kpis(cleaned, summary, types)
    pivots = generate_pivot_tables(cleaned, types)
    ai = generate_ai_insights(cleaned, types)
    charts = generate_charts(cleaned, types, get_default_theme())
    return cleaned, types, summary, report, kpis, pivots, ai, charts


def test_dataframe_to_csv_roundtrip(sales_df):
    raw = dataframe_to_csv(sales_df)
    assert isinstance(raw, bytes)
    parsed = pd.read_csv(BytesIO(raw))
    assert len(parsed) == len(sales_df)
    assert list(parsed.columns) == list(sales_df.columns)


def test_dataframe_to_excel_contains_cleaned_and_pivots(sales_df):
    cleaned, _, _, _, _, pivots, _, _ = _pipeline(sales_df)
    payload = dataframe_to_excel(cleaned, pivots)
    book = pd.ExcelFile(BytesIO(payload))
    assert book.sheet_names[0] == "Cleaned Data"
    assert len(book.sheet_names) == 1 + len(pivots)
    assert len(book.parse("Cleaned Data")) == len(cleaned)


def test_dataframe_to_excel_sanitizes_invalid_sheet_names():
    """Pivot titles from column names with Excel-invalid chars must not crash."""
    df = pd.DataFrame({"Cost/Unit:2024": [1.0, 2.0, 3.0], "Region": ["a", "b", "c"]})
    types = detect_column_types(df)
    pivots = generate_pivot_tables(df, types)
    assert pivots, "pivot with invalid characters expected"
    payload = dataframe_to_excel(df, pivots)
    book = pd.ExcelFile(BytesIO(payload))
    for name in book.sheet_names:
        assert len(name) <= 31
        for ch in "\\/:*?[]":
            assert ch not in name


def test_dataframe_to_excel_deduplicates_truncated_sheet_names():
    a = PivotTable(title="Revenue by Very Long Category Name AA", slug="a", data=pd.DataFrame({"x": [1]}))
    b = PivotTable(title="Revenue by Very Long Category Name BB", slug="b", data=pd.DataFrame({"x": [2]}))
    payload = dataframe_to_excel(pd.DataFrame({"y": [1]}), [a, b])
    book = pd.ExcelFile(BytesIO(payload))
    assert len(book.sheet_names) == len(set(book.sheet_names))


def test_export_summary_report_sheets(sales_df):
    cleaned, types, summary, report, kpis, pivots, ai, _ = _pipeline(sales_df)
    payload = export_summary_report(
        summary, report, kpis, ai["key_insights"], ai["recommendations"], pivots
    )
    book = pd.ExcelFile(BytesIO(payload))
    for expected in ("Overview", "KPIs", "Cleaning Report", "Insights", "Recommendations"):
        assert expected in book.sheet_names
    overview = book.parse("Overview")
    assert "Metric" in overview.columns and "Value" in overview.columns


def test_pdf_report_includes_chart_images(sales_df):
    """PDF must embed real rendered chart PNGs (kaleido) when charts are requested."""
    _, types, summary, report, _, pivots, ai, charts = _pipeline(sales_df)
    assert charts, "pipeline should produce charts"
    payload = make_custom_pdf_report(
        summary,
        report,
        ai["key_insights"],
        ai["recommendations"],
        pivots,
        charts[:2],
        include_tables=True,
        include_charts=True,
    )
    assert payload[:4] == b"%PDF"
    # ReportLab embeds each chart PNG as an image XObject.
    assert payload.count(b"/Subtype /Image") >= 1, "expected embedded chart images in PDF"


def test_pdf_report_summary_only_has_no_images(sales_df):
    _, types, summary, report, _, pivots, ai, charts = _pipeline(sales_df)
    payload = make_custom_pdf_report(
        summary, report, ai["key_insights"], ai["recommendations"], pivots, charts,
        include_tables=False, include_charts=False,
    )
    assert payload[:4] == b"%PDF"
    assert payload.count(b"/Subtype /Image") == 0


def test_ppt_report_includes_picture_shapes(sales_df):
    """PPTX must contain real picture shapes for exported charts."""
    from pptx import Presentation
    from pptx.enum.shapes import MSO_SHAPE_TYPE

    _, types, summary, report, _, pivots, ai, charts = _pipeline(sales_df)
    payload = make_ppt_report(
        summary, report, ai["key_insights"], ai["recommendations"], pivots, charts[:2],
        include_tables=True, include_charts=True,
    )
    prs = Presentation(BytesIO(payload))
    pictures = [
        shape
        for slide in prs.slides
        for shape in slide.shapes
        if shape.shape_type == MSO_SHAPE_TYPE.PICTURE
    ]
    assert len(prs.slides) >= 2, "expected cover + insights slides"
    assert len(pictures) >= 1, "expected at least one chart image slide"
