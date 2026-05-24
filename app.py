from __future__ import annotations

import pandas as pd
import streamlit as st

from utils.analyzer import analyze_dataset, build_kpis
from utils.chart_engine import generate_charts
from utils.data_cleaner import clean_data, detect_column_types
from utils.helpers import (
    dataframe_to_csv,
    dataframe_to_excel,
    make_pdf_report,
    read_uploaded_file,
    render_card,
)
from utils.insight_engine import generate_insights, generate_recommendations
from utils.pivot_engine import generate_pivot_tables


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
