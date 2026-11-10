"""Regression coverage for the Excel MVP release stabilization work."""

from __future__ import annotations

from decimal import Decimal
from io import BytesIO
from uuid import UUID

import numpy as np
import pandas as pd
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from ai_insights import generate_ai_insights
from analytics_engine import analyze_dataset, generate_pivot_tables
from dashboard import (
    build_custom_chart,
    generate_charts,
    get_default_theme,
    normalize_chart_data,
)
from data_cleaning import clean_data, detect_column_types
from export_module import (
    export_chart_images,
    make_custom_pdf_report,
    make_ppt_report,
)


def _six_chart_data():
    return pd.DataFrame(
        {
            "Date": pd.date_range("2024-01-01", periods=6, freq="D"),
            "Group": ["A", "A", "B", "B", "C", "C"],
            "X": [1, 2, 3, 4, 5, 6],
            "Y": [2, 4, 3, 8, 6, 9],
            "Z": [9, 8, 7, 6, 5, 4],
        }
    )


def test_chart_normalizer_handles_period_dates_nonfinite_and_extension_scalars():
    frame = pd.DataFrame(
        {
            "period": [pd.Period("2024-01", freq="M"), pd.NaT],
            "date": [pd.Timestamp("2024-01-02"), pd.NaT],
            "number": [np.float64(3.5), np.float64(np.inf)],
            "negative_infinity": [np.float64(-np.inf), np.float64(0)],
            "nullable": [pd.NA, np.int64(7)],
            "decimal": [Decimal("1.25"), Decimal("Infinity")],
            "unsupported": [UUID("12345678-1234-5678-1234-567812345678"), "ok"],
            "longdouble": [np.longdouble("1.25"), np.longdouble("2.5")],
        }
    )
    normalized = normalize_chart_data(frame)
    assert normalized.loc[0, "period"] == "2024-01"
    assert normalized.loc[1, "period"] is None
    assert normalized.loc[0, "date"] == pd.Timestamp("2024-01-02").to_pydatetime()
    assert normalized.loc[1, "date"] is None
    assert normalized.loc[0, "number"] == 3.5
    assert pd.isna(normalized.loc[1, "number"])
    assert pd.isna(normalized.loc[0, "negative_infinity"])
    assert normalized.loc[1, "negative_infinity"] == 0
    assert pd.isna(normalized.loc[0, "nullable"])
    assert normalized.loc[1, "nullable"] == 7
    assert normalized.loc[0, "decimal"] == 1.25
    assert pd.isna(normalized.loc[1, "decimal"])
    assert normalized.loc[0, "unsupported"] == "12345678-1234-5678-1234-567812345678"
    assert normalized.loc[0, "longdouble"] == 1.25


def test_generated_monthly_chart_excludes_invalid_dates_and_period_objects():
    frame = pd.DataFrame(
        {"Date": ["2024-01-02", "2024-02-02", "not a date"], "Revenue": [10.0, 20.0, 999.0]}
    )
    charts = generate_charts(
        frame,
        {"datetime": ["Date"], "numeric": ["Revenue"]},
        get_default_theme(),
        chart_types=["line"],
    )
    assert len(charts) == 1
    assert list(charts[0].figure.data[0].x) == ["2024-01", "2024-02"]
    assert "NaT" not in charts[0].figure.to_json()


def test_empty_and_filtered_datasets_have_explicit_chart_behavior():
    empty = pd.DataFrame({"Region": pd.Series(dtype="object"), "Revenue": pd.Series(dtype="float64")})
    types = {"categorical": ["Region"], "numeric": ["Revenue"]}
    assert generate_charts(empty, types) == []
    with pytest.raises(ValueError, match="empty dataset"):
        build_custom_chart(empty, "Bar", "Region", "Revenue", column_types=types)

    filtered = pd.DataFrame({"Region": ["A"], "Revenue": [5.0]}).iloc[0:0]
    assert generate_charts(filtered, types) == []


def test_custom_bar_uses_selected_x_y_and_aggregation(sales_df):
    cleaned, _ = clean_data(sales_df)
    types = detect_column_types(cleaned)
    spec = build_custom_chart(cleaned, "Bar", "Region", "Revenue", agg="mean", column_types=types)
    means = cleaned.groupby("Region")["Revenue"].mean()
    assert list(spec.figure.data[0].x) == list(means.index)
    assert list(spec.figure.data[0].y) == pytest.approx(list(means.values))


def test_app_custom_builder_uses_final_dataframe(monkeypatch, sales_df):
    class NamedUpload(BytesIO):
        name = "sales.csv"
        size = 0

    upload_bytes = sales_df.to_csv(index=False).encode("utf-8")

    def fake_uploader(label, *args, key=None, **kwargs):
        if key != "main_upload":
            return None
        upload = NamedUpload(upload_bytes)
        upload.size = len(upload_bytes)
        return upload

    monkeypatch.setattr(st, "file_uploader", fake_uploader)
    app = AppTest.from_file("app.py", default_timeout=120)
    app.run()

    next(box for box in app.selectbox if box.label == "Step type").select("rename")
    app.run()
    next(box for box in app.selectbox if box.label == "Column to rename").select("Revenue")
    next(box for box in app.text_input if box.label == "New column name").set_value("Sales Revenue")
    next(button for button in app.button if button.label == "Add Step").click()
    app.run()

    next(box for box in app.selectbox if box.label == "X Column").select("Region")
    next(box for box in app.selectbox if box.label == "Y Column").select("Sales Revenue")
    next(button for button in app.button if button.label == "Build Custom Chart").click()
    app.run()
    assert not app.exception, app.exception
    assert any("Chart built:" in item.value for item in app.success)


def test_app_accepts_xlsx_upload(monkeypatch, xlsx_upload):
    def fake_uploader(label, *args, key=None, **kwargs):
        if key != "main_upload":
            return None
        xlsx_upload.seek(0)
        return xlsx_upload

    monkeypatch.setattr(st, "file_uploader", fake_uploader)
    app = AppTest.from_file("app.py", default_timeout=120)
    app.run()
    assert not app.exception, app.exception
    assert app.title and "Excel" in app.title[0].value


def test_all_six_custom_chart_types_build_and_serialize():
    df = _six_chart_data()
    types = detect_column_types(df)
    cases = (
        ("Bar", "Group", "Y"),
        ("Line", "X", "Y"),
        ("Pie / Donut", "Group", "Y"),
        ("Histogram", "Y", None),
        ("Scatter", "X", "Y"),
        ("Correlation heatmap", None, None),
    )
    charts = [build_custom_chart(df, label, x_col, y_col, column_types=types) for label, x_col, y_col in cases]
    assert [chart.kind for chart in charts] == ["bar", "line", "pie", "histogram", "scatter", "heatmap"]
    for chart in charts:
        chart.figure.to_json()


def test_nonfinite_chart_values_are_json_null_not_invalid_tokens():
    frame = pd.DataFrame({"Group": ["A", "A", "B"], "Value": [1.0, np.inf, np.nan]})
    types = {"categorical": ["Group"], "numeric": ["Value"]}
    spec = build_custom_chart(frame, "Bar", "Group", "Value", column_types=types)
    serialized = spec.figure.to_json()
    assert "Infinity" not in serialized
    assert '"NaN"' not in serialized


def test_six_chart_images_embed_in_pdf_and_ppt():
    from pptx import Presentation
    from pptx.enum.shapes import MSO_SHAPE_TYPE

    source = _six_chart_data()
    cleaned, cleaning_report = clean_data(source)
    types = detect_column_types(cleaned)
    charts = [
        build_custom_chart(cleaned, label, x_col, y_col, column_types=types)
        for label, x_col, y_col in (
            ("Bar", "Group", "Y"),
            ("Line", "X", "Y"),
            ("Pie / Donut", "Group", "Y"),
            ("Histogram", "Y", None),
            ("Scatter", "X", "Y"),
            ("Correlation heatmap", None, None),
        )
    ]
    images = export_chart_images(charts)
    assert len(images) == 6
    assert all(image["bytes"].startswith(b"\x89PNG\r\n\x1a\n") for image in images)

    summary = analyze_dataset(cleaned, types)
    ai = generate_ai_insights(cleaned, types)
    pivots = generate_pivot_tables(cleaned, types)
    pdf = make_custom_pdf_report(
        summary, cleaning_report, ai["key_insights"], ai["recommendations"],
        pivots, charts, False, True, chart_images=images,
    )
    assert pdf[:4] == b"%PDF"
    assert pdf.count(b"/Subtype /Image") >= 6

    ppt = make_ppt_report(
        summary, cleaning_report, ai["key_insights"], ai["recommendations"],
        pivots, charts, False, True, chart_images=images,
    )
    presentation = Presentation(BytesIO(ppt))
    pictures = [
        shape for slide in presentation.slides for shape in slide.shapes
        if shape.shape_type == MSO_SHAPE_TYPE.PICTURE
    ]
    assert len(pictures) == 6
