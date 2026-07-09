"""Excel Automation & AI Reporting Tool - Streamlit UI.

Thin orchestration layer. All logic lives in dedicated modules:
- data_loader.py     : read files, multiple sheets, structure detection
- data_cleaning.py   : pandas cleaning engine + column type detection
- analytics_engine.py: pivot-table automation, KPIs, growth
- dashboard.py       : Plotly charts, KPI cards, filters, styling
- ai_insights.py     : business-language explanation, insights, recommendations
- export_module.py   : Excel / CSV / summary / PDF / PPT exports

Run with:  streamlit run app.py
"""

from __future__ import annotations

import os
import pandas as pd
import streamlit as st

from analytics_engine import analyze_dataset, build_kpis, generate_pivot_tables
from ai_insights import generate_ai_insights
from dashboard import (
    filter_dataframe,
    generate_charts,
    inject_styles,
    render_card,
    render_dashboard_banner,
    render_metric_cards,
    select_dashboard_controls,
    select_client_branding,
)
from dashboard_modes import render_mode_selector, render_smart_dashboard
from data_cleaning import clean_data, detect_column_types
from data_loader import normalize_headers, read_uploaded_file
from workbook import load_or_create, render_workbook_chrome
from export_module import (
    dataframe_to_csv,
    dataframe_to_excel,
    export_summary_report,
    generate_export_validation_report,
    make_custom_pdf_report,
    make_ppt_report,
)

st.set_page_config(
    page_title="Excel Automation & AI Reporting Tool",
    page_icon=":bar_chart:",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _section(title: str) -> None:
    st.subheader(title)


def _insight(text: str, warning: bool = False) -> None:
    if warning:
        st.warning(text)
    else:
        st.info(text)


def _get_upload():
    """Render upload widgets (sidebar + main) and return the uploaded file."""
    with st.sidebar:
        st.subheader("Upload Panel")
        uploaded = st.file_uploader(
            "Drop an Excel or CSV file",
            type=["xlsx", "xls", "csv"],
            accept_multiple_files=False,
        )
        st.caption("Supported formats: .xlsx, .xls, .csv")

    if uploaded is None:
        _section("Upload Dataset")
        uploaded = st.file_uploader(
            "Upload an Excel or CSV file",
            type=["xlsx", "xls", "csv"],
            accept_multiple_files=False,
            key="main_upload",
        )
        st.info("Upload a dataset to start the automated analytics workflow.")
    return uploaded


def main() -> None:
    inject_styles()

    st.title("Excel Automation & AI Reporting Tool")
    st.caption(
        "Upload a spreadsheet to automatically clean the data, generate pivot-table "
        "analytics, build an interactive dashboard, surface AI-style insights, and export "
        "client-ready Excel, PDF, and PowerPoint reports."
    )

    uploaded_file = _get_upload()
    if uploaded_file is None:
        st.stop()

    # --- Workbook workspace: load file, manage sheets, ribbon + tabs ---
    parsed_workbook = read_uploaded_file(uploaded_file)
    workbook_manager = load_or_create(uploaded_file, parsed_workbook)
    workbook_manager = render_workbook_chrome(workbook_manager)
    raw_df = workbook_manager.select_active_via_loader()

    if raw_df is None or raw_df.empty:
        st.warning(
            f"Sheet **{workbook_manager.active_sheet}** is empty. "
            "Add data, switch to another sheet, or duplicate a populated sheet to continue."
        )
        st.stop()

    # Client branding: company name, logo, preset or custom hex colors.
    theme, theme_name, branding = select_client_branding()
    dashboard_config = select_dashboard_controls()
    inject_styles(theme)

    # --- Cleaning + analysis pipeline ---
    raw_df = normalize_headers(raw_df)
    raw_types = detect_column_types(raw_df)
    cleaned_df, cleaning_report = clean_data(raw_df)
    column_types = detect_column_types(cleaned_df)
    filtered_df = filter_dataframe(cleaned_df, column_types)

    summary = analyze_dataset(filtered_df, column_types)
    kpis = build_kpis(filtered_df, summary, column_types)
    pivots = generate_pivot_tables(filtered_df, column_types)
    charts = generate_charts(filtered_df, column_types, theme)
    ai = generate_ai_insights(filtered_df, column_types)
    insights, recommendations = ai["key_insights"], ai["recommendations"]

    tabs = st.tabs(
        ["Dataset", "Executive Summary", "Dashboard", "Pivot Tables", "AI Insights", "Downloads"]
    )

    # --- Tab 1: Dataset ---
    with tabs[0]:
        _section("Dataset Preview")
        c1, c2, c3 = st.columns(3)
        with c1:
            render_card("Rows", f"{len(raw_df):,}", "Original dataset")
        with c2:
            render_card("Columns", f"{raw_df.shape[1]:,}", "Detected fields")
        with c3:
            render_card("Filtered Rows", f"{len(filtered_df):,}", "After sidebar filters")

        st.dataframe(raw_df.head(150), use_container_width=True)

        _section("Column Information")
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

        _section("Cleaning Report")
        st.dataframe(pd.DataFrame([cleaning_report]), use_container_width=True, hide_index=True)
        st.dataframe(cleaned_df.head(150), use_container_width=True)

    # --- Tab 2: Executive Summary ---
    with tabs[1]:
        _section("Executive Summary")
        render_metric_cards(kpis, theme)

        _section("Plain-Language Overview")
        _insight(ai["dataset_summary"])

        _section("Statistical Analysis")
        if summary["statistics"].empty:
            st.caption("No numeric columns are available for statistical profiling.")
        else:
            st.dataframe(summary["statistics"], use_container_width=True)

        if not summary["correlations"].empty:
            _section("Correlation Matrix")
            st.dataframe(summary["correlations"], use_container_width=True)

        if summary["date_ranges"]:
            _section("Date Ranges")
            st.dataframe(pd.DataFrame(summary["date_ranges"]), use_container_width=True, hide_index=True)

    # --- Tab 3: Dashboard ---
    with tabs[2]:
        render_dashboard_banner(theme, theme_name, branding)
        selected_mode = render_mode_selector()
        mode_artifacts = render_smart_dashboard(
            filtered_df,
            mode_key=selected_mode,
            column_types=column_types,
            theme=theme,
            charts=charts,
            pivots=pivots,
            ai=ai,
            dashboard_config=dashboard_config,
            workbook_id=workbook_manager.source_name,
            sheet_id=workbook_manager.active_sheet,
        )
        st.caption("Filters still apply from the sidebar; changing mode rerenders the dashboard layout and export mix.")

    # --- Tab 4: Pivot Tables ---
    with tabs[3]:
        _section("Automated Pivot Tables")
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

    # --- Tab 5: AI Business Insights ---
    with tabs[4]:
        badge = "AI-powered (LLM)" if ai["ai_powered"] else "Rule-based engine"
        type_label = ai["dataset_type"].title()
        st.subheader(f"AI Business Insights ({type_label} data · {badge})")

        st.markdown("#### 1. Dataset Summary")
        _insight(ai["dataset_summary"])

        st.markdown("#### 2. Key Insights")
        if not insights:
            st.caption("No key insights could be generated for this dataset.")
        for item in insights:
            _insight(item)

        st.markdown("#### 3. Problems / Anomalies")
        for item in ai["anomalies"]:
            stable = "no significant" in item.lower() or "looks stable" in item.lower()
            _insight(item, warning=not stable)

        st.markdown("#### 4. Recommendations")
        for item in recommendations:
            warn = "warning" in item.lower() or "risk" in item.lower()
            _insight(item, warning=warn)

        if not ai["ai_powered"]:
            st.caption("Tip: set the OPENAI_API_KEY environment variable to generate these sections with an LLM.")

    # --- Tab 6: Downloads ---
    with tabs[5]:
        _section("Download Reports")

        report_mode = st.radio(
            "Client report content",
            options=["Summary only", "Tables", "Charts", "Tables + Charts"],
            index=3,
            horizontal=True,
        )
        include_tables = report_mode in {"Tables", "Tables + Charts"}
        include_charts = report_mode in {"Charts", "Tables + Charts"}

        mode_artifacts = locals().get(
            "mode_artifacts",
            {
                "mode": None,
                "kpis": kpis,
                "insights": insights,
                "recommendations": recommendations,
                "pivots": pivots,
                "charts": charts,
            },
        )
        export_kpis = mode_artifacts["kpis"]
        export_insights = mode_artifacts["insights"]
        export_recommendations = mode_artifacts["recommendations"]
        export_pivots = mode_artifacts["pivots"]
        export_charts = mode_artifacts["charts"]
        mode_label = mode_artifacts["mode"].label if mode_artifacts.get("mode") else "Default Dashboard"

        skip_heavy_exports = os.environ.get("EXCELMVP_SKIP_HEAVY_EXPORTS") == "1"
        export_charts_for_files = [] if skip_heavy_exports else export_charts
        excel_bytes = dataframe_to_excel(
            cleaned_df,
            pivots=export_pivots,
            charts=export_charts_for_files,
            summary=summary,
            kpis=export_kpis,
            insights=export_insights,
            recommendations=export_recommendations,
        )
        csv_bytes = dataframe_to_csv(cleaned_df)
        summary_bytes = export_summary_report(summary, cleaning_report, export_kpis, export_insights, export_recommendations, export_pivots)
        if skip_heavy_exports:
            pdf_bytes = b""
            ppt_bytes = b""
        else:
            pdf_bytes = make_custom_pdf_report(
                summary, cleaning_report, export_insights, export_recommendations, export_pivots, export_charts, include_tables, include_charts
            )
            ppt_bytes = make_ppt_report(
                summary, cleaning_report, export_insights, export_recommendations, export_pivots, export_charts, include_tables, include_charts
            )
        st.caption(f"Downloads use the current Smart Dashboard Mode where possible: {mode_label}.")

        st.markdown("**Data exports**")
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
            st.download_button(
                "Summary Report (Excel)",
                summary_bytes,
                file_name="summary_report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        st.markdown("**Client deliverables**")
        d4, d5 = st.columns(2)
        with d4:
            st.download_button("Client PDF", pdf_bytes, file_name="client_analytics_report.pdf", mime="application/pdf")
        with d5:
            st.download_button(
                "Client PPT",
                ppt_bytes,
                file_name="client_analytics_deck.pptx",
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            )

        validation_report = (
            b'{"skipped_heavy_exports": true}'
            if skip_heavy_exports
            else generate_export_validation_report(
                cleaned_df,
                summary,
                cleaning_report,
                export_kpis,
                export_insights,
                export_recommendations,
                export_pivots,
                export_charts,
                include_tables,
                include_charts,
            )
        )
        st.download_button(
            "Export Validation Report",
            validation_report,
            file_name="export_validation_report.json",
            mime="application/json",
        )

        st.caption("Choose whether the PDF/PPT deliverable includes pivot tables, charts, both, or summary only.")


if __name__ == "__main__":
    main()
