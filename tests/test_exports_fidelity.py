"""Export fidelity tests (EXPORT.md): injection guard, formats, content matrix."""

from __future__ import annotations

from io import BytesIO

import pandas as pd
import pytest

from analytics_engine import analyze_dataset, generate_pivot_tables
from data_cleaning import clean_data, detect_column_types
from export_module import (
    _report_subtitle,
    dataframe_to_csv,
    dataframe_to_excel,
    export_summary_report,
    make_custom_pdf_report,
    make_ppt_report,
)
from ai_insights import generate_ai_insights

TODAY_PREFIX = pd.Timestamp.today().date().isoformat()[:10]


def test_report_subtitle_has_generation_date_and_period():
    summary = {"date_ranges": [{"column": "Date", "start": "2024-01-01", "end": "2024-03-31"}]}
    subtitle = _report_subtitle(summary)
    assert TODAY_PREFIX in subtitle
    assert "2024-01-01 → 2024-03-31" in subtitle


def test_report_subtitle_without_dates():
    assert TODAY_PREFIX in _report_subtitle({"date_ranges": []})


def test_csv_formula_injection_guard():
    """String cells starting with =, +, @ are neutralized; negatives untouched."""
    df = pd.DataFrame(
        {
            "Name": ["=HYPERLINK(evil)", "+1+1", "@handle", "-50% discount", "Ünïcode Ümsatz"],
            "Value": [1.0, 2.0, 3.0, 4.0, 5.0],
        }
    )
    text = dataframe_to_csv(df).decode("utf-8")
    assert "'=HYPERLINK(evil)" in text
    assert "'+1+1" in text
    assert "'@handle" in text
    assert "-50% discount" in text  # leading '-' deliberately preserved
    assert "Ünïcode Ümsatz" in text  # UTF-8 preserved


def test_excel_formula_guard_applies_to_text_cells():
    import openpyxl

    df = pd.DataFrame({"Name": ["=SUM(A1:A9)", "Normal"], "Value": [1.0, 2.0]})
    payload = dataframe_to_excel(df)
    ws = openpyxl.load_workbook(BytesIO(payload))["Cleaned Data"]
    assert ws.cell(row=2, column=1).value == "'=SUM(A1:A9)"
    assert ws.cell(row=3, column=1).value == "Normal"


def test_excel_column_widths_are_set():
    import openpyxl

    df = pd.DataFrame({"A very long header column name": ["x"], "n": [1.0]})
    ws = openpyxl.load_workbook(BytesIO(dataframe_to_excel(df)))["Cleaned Data"]
    width_a = ws.column_dimensions["A"].width
    assert width_a and width_a >= 10


def test_excel_pivot_sheets_guard_and_sanitize():
    import openpyxl

    df = pd.DataFrame({"=Tricky/Name": [1.0, 2.0, 3.0], "Region": ["EU:West", "EU:East", "US:East"]})
    types = detect_column_types(df)
    pivots = generate_pivot_tables(df, types)
    book = openpyxl.load_workbook(BytesIO(dataframe_to_excel(df, pivots)))
    for name in book.sheetnames:
        assert len(name) <= 31
        for ch in "\\/:*?[]":
            assert ch not in name


def test_unicode_and_long_labels_survive_csv_and_excel():
    df = pd.DataFrame(
        {
            "Ümsatz (€)": [100.0, 200.0],
            "Sehr_lange_Kategorie_mit_viel_Text_und_mehr_Text_als_nötig": ["a", "b"],
            "日本語": ["東京", "大阪"],
        }
    )
    parsed = pd.read_csv(BytesIO(dataframe_to_csv(df)))
    assert list(parsed.columns) == list(df.columns)
    book = pd.ExcelFile(BytesIO(dataframe_to_excel(df)))
    assert len(book.parse(book.sheet_names[0])) == 2


def test_empty_dataframe_exports_headers_only():
    empty = pd.DataFrame({"a": [], "b": []})
    csv_text = dataframe_to_csv(empty).decode("utf-8")
    assert csv_text.strip() == "a,b"
    book = pd.ExcelFile(BytesIO(dataframe_to_excel(empty)))
    assert book.parse("Cleaned Data").empty


def test_pdf_builds_for_dataset_without_any_chart():
    """No suitable numeric measures -> PDF still valid, zero images."""
    df = pd.DataFrame({"name": [f"person {i}" for i in range(40)], "city": [f"c{i}" for i in range(40)]})
    types = detect_column_types(df)
    summary = analyze_dataset(df, types)
    ai = generate_ai_insights(df, types)
    pivots = generate_pivot_tables(df, types)
    payload = make_custom_pdf_report(
        summary, {"duplicates_removed": 0}, ai["key_insights"], ai["recommendations"],
        pivots, [], include_tables=True, include_charts=True,
    )
    assert payload[:4] == b"%PDF"
    assert payload.count(b"/Subtype /Image") == 0


def test_ppt_contains_methodology_slide_scope_and_footers():
    """PRESENTATION.md §2/§3: sequence, methodology slide, footers, no dupes."""
    from pptx import Presentation

    rng_df = pd.DataFrame(
        {
            "Order Date": pd.to_datetime(["2024-01-05", "2024-02-05", "2024-03-05"] * 4),
            "Region": ["North", "South", "East"] * 4,
            "Revenue": [100.0, 200.0, 300.0] * 4,
        }
    )
    cleaned, report = clean_data(rng_df)
    types = detect_column_types(cleaned)
    summary = analyze_dataset(cleaned, types)
    ai = generate_ai_insights(cleaned, types)
    pivots = generate_pivot_tables(cleaned, types)

    payload = make_ppt_report(
        summary, report, ai["key_insights"], ai["recommendations"], pivots, [],
        include_tables=False, include_charts=False,
    )
    prs = Presentation(BytesIO(payload))
    texts = [
        shape.text_frame.text
        for slide in prs.slides
        for shape in slide.shapes
        if shape.has_text_frame and shape.text_frame.text.strip()
    ]
    joined = "\n".join(texts)

    assert "Data Quality & Methodology" in joined
    assert "Data scope" in joined                      # title slide, not duplicated recommendations
    assert joined.count("Recommended actions") == 1    # exactly one recommendations panel
    assert "Excel Dashboard Studio" in joined          # footers
    assert TODAY_PREFIX in joined                      # generation date
    assert "no causal or predictive claims" in joined  # honest caveat
    # Cleaning steps are calculation-backed
    assert f"{report['duplicates_removed']} duplicate row(s) removed." in joined


def test_summary_report_still_has_all_sections():
    df = pd.DataFrame({"Revenue": [1.0, 2.0], "Region": ["a", "b"]})
    cleaned, report = clean_data(df)
    types = detect_column_types(cleaned)
    summary = analyze_dataset(cleaned, types)
    ai = generate_ai_insights(cleaned, types)
    book = pd.ExcelFile(BytesIO(export_summary_report(summary, report, {}, ai["key_insights"], ai["recommendations"], [])))
    for expected in ("Overview", "Cleaning Report", "Insights", "Recommendations"):
        assert expected in book.sheet_names
