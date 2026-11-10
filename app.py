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

import pandas as pd
import streamlit as st

from analytics_engine import analyze_dataset, build_kpis, generate_pivot_tables
from ai_insights import generate_ai_insights
from dashboard import (
    CHART_GUIDE,
    filter_dataframe,
    generate_charts,
    inject_styles,
    render_card,
    render_charts,
    render_dashboard_banner,
    render_metric_cards,
    select_client_branding,
)
from data_cleaning import clean_data, detect_column_types
from data_loader import list_sheets, normalize_headers, read_uploaded_file, select_sheet
from export_module import (
    dataframe_to_csv,
    dataframe_to_excel,
    export_summary_report,
    make_custom_pdf_report,
    make_ppt_report,
)
from transformations import apply_transforms

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

    # --- Input system: read file and (optionally) pick a sheet ---
    workbook = read_uploaded_file(uploaded_file)
    sheet_name = None
    if isinstance(workbook, dict) and len(workbook) > 1:
        with st.sidebar:
            sheet_name = st.selectbox("Workbook sheet", list_sheets(workbook))
    raw_df = select_sheet(workbook, sheet_name)

    if raw_df is None or raw_df.empty:
        st.error("The selected file or sheet is empty.")
        st.stop()

    # Client branding: company name, logo, preset or custom hex colors.
    theme, theme_name, branding = select_client_branding()
    inject_styles(theme)

    # --- Cleaning + analysis pipeline ---
    raw_df = normalize_headers(raw_df)
    raw_types = detect_column_types(raw_df)
    cleaned_df, cleaning_report = clean_data(raw_df)
    column_types = detect_column_types(cleaned_df)
    filtered_df = filter_dataframe(cleaned_df, column_types)

    # --- Apply transformation steps (deferred to Data Tools tab) ---
    # Transformations are applied after column selection in the Data Tools tab.
    # For now, use filtered_df as the base dataframe.
    transformed_df = filtered_df
    applied_labels = []
    errors = []

    summary = analyze_dataset(transformed_df, column_types)
    kpis = build_kpis(transformed_df, summary, column_types)
    pivots = generate_pivot_tables(transformed_df, column_types)
    charts = generate_charts(transformed_df, column_types, theme)
    ai = generate_ai_insights(transformed_df, column_types)
    insights, recommendations = ai["key_insights"], ai["recommendations"]

    tabs = st.tabs(
        ["Dataset", "Data Tools", "Executive Summary", "Dashboard", "Pivot Tables", "AI Insights", "Downloads"]
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

    # --- Tab 2: Data Tools ---
    with tabs[1]:
        _section("Column Selection")
        # Initialize/refresh column selection state when dataset changes
        if "selected_columns" not in st.session_state or st.session_state.get("dataset_hash") != str(hash(raw_df.to_string())):
            st.session_state.selected_columns = list(raw_df.columns)
            st.session_state.dataset_hash = str(hash(raw_df.to_string()))
        # Column selection UI
        _section("Column Selection")
        c1, c2 = st.columns([3, 1])
        with c1:
            st.caption(f"Showing {len(st.session_state.selected_columns)} of {len(raw_df.columns)} columns")
        with c2:
            if st.button("Select All", help="Select all columns"):
                st.session_state.selected_columns = list(raw_df.columns)
                st.rerun()
        selected = st.multiselect(
            "Select columns to retain",
            options=list(raw_df.columns),
            default=st.session_state.selected_columns,
            key="column_selector_v1",
            help="Choose which columns to include in the cleaned dataset and downstream outputs.",
        )
        # Update session state when user changes selection
        st.session_state.selected_columns = selected
        # Display validation message if empty selection
        if not selected:
            st.warning("No columns selected. At least one column is required for analysis and exports.")
        # Apply column selection: filter both raw and cleaned dataframes
        # Preserve the original uploaded dataset; do not mutate it
        selected_columns_set = set(selected)
        filtered_raw = raw_df[[col for col in raw_df.columns if col in selected_columns_set]].copy() if selected else raw_df.head(0)
        filtered_cleaned = cleaned_df[[col for col in cleaned_df.columns if col in selected_columns_set]].copy() if selected else cleaned_df.head(0)
        # cleaned_selected is the cleaned data with selected columns, used in transformation step config
        cleaned_selected = filtered_cleaned.copy()
        # When columns are selected, apply the filter to the cleaning pipeline as well
        # We need to re-clean with only the selected columns, preserving the cleaning steps

        # --- Transformation Steps UI ---
        st.subheader("Transformation Steps")
        if "transform_steps" not in st.session_state:
            st.session_state.transform_steps = []

        # Display configured steps in order
        if st.session_state.transform_steps:
            st.caption(f"{len(st.session_state.transform_steps)} step(s) configured")
            for i, step in enumerate(st.session_state.transform_steps):
                with st.expander(f"Step {i+1}: {step}", expanded=False):
                    op = step.get("op", "") if isinstance(step, dict) else step
                    if op.startswith("select"):
                        st.caption("Select columns operation")
                    elif op.startswith("rename"):
                        st.caption("Rename column operation")
                    elif op.startswith("split"):
                        st.caption("Split column operation")
                    elif op.startswith("merge"):
                        st.caption("Merge columns operation")
                    elif op.startswith("range"):
                        st.caption("Range filter operation")
                    elif op.startswith("join"):
                        st.caption("Join operation")
                    if st.button(f"Remove step {i+1}", key=f"remove_step_{i}"):
                        st.session_state.transform_steps.pop(i)
                        st.rerun()
        else:
            st.caption("No transformation steps configured")

        # --- Step Configuration ---
        st.caption("Add Transformation Step")
        step_type = st.selectbox("Step type", ["select", "rename", "split", "merge", "range", "join"], key="step_selector")

        # Configuration per step type
        cfg = {}
        if step_type == "select":
            cfg["columns"] = st.multiselect("Columns to retain", options=list(raw_df.columns) if selected else [], key="step_select_cols")
        elif step_type == "rename":
            cols = [c for c in cleaned_selected.columns] if selected else []
            cfg["old"] = st.selectbox("Column to rename", options=cols, key="step_rename_col") if cols else ""
            cfg["new"] = st.text_input("New column name", key="step_rename_new")
        elif step_type == "split":
            cfg["column"] = st.selectbox("Column to split", options=list(cleaned_selected.columns) if selected else [], key="step_split_col") if selected else ""
            cfg["sep"] = st.text_input("Separator", value=",", key="step_split_sep")
        elif step_type == "merge":
            cfg["columns"] = st.multiselect("Columns to merge", options=list(cleaned_selected.columns) if selected else [], key="step_merge_cols") if selected else []
            cfg["sep"] = st.text_input("Separator", value=" ", key="step_merge_sep")
            cfg["new_name"] = st.text_input("Target column name", key="step_merge_new_name")
        elif step_type == "range":
            cfg["column"] = st.selectbox("Numeric column", options=[c for c in cleaned_selected.columns if pd.api.types.is_numeric_dtype(cleaned_selected[c])] if selected else [], key="step_range_col") if selected else ""
            c1, c2 = st.columns(2)
            with c1:
                cfg["min"] = st.number_input("Minimum", value=0.0, key="step_range_min")
            with c2:
                cfg["max"] = st.number_input("Maximum", value=100.0, key="step_range_max")
        elif step_type == "join":
            st.caption("Upload a second dataset to join with")
            join_file = st.file_uploader("Join file", type=["xlsx", "xls", "csv"], key="join_file_uploader")
            if join_file is not None:
                right_df = pd.read_csv(join_file) if join_file.name.endswith(".csv") else pd.read_excel(join_file)
                cfg["right"] = right_df
                join_keys = [c for c in cleaned_selected.columns if c in right_df.columns] if selected else []
                cfg["left_key"] = st.selectbox("Left key column", options=join_keys, key="step_join_left") if join_keys else ""
                cfg["right_key"] = st.selectbox("Right key column", options=list(right_df.columns), key="step_join_right") if right_df.columns.tolist() else ""
                cfg["how"] = st.selectbox("Join type", options=["left", "inner"], key="step_join_how")

        c1, c2 = st.columns(2)
        with c1:
            if st.button("Add Step", type="primary", key="add_step_btn"):
                # Validate configuration
                valid = True
                op = {"op": step_type, **cfg}
                if step_type == "select":
                    if not cfg.get("columns"):
                        st.error("Please select at least one column.")
                        valid = False
                elif step_type == "rename":
                    if not cfg.get("old") or not cfg.get("new"):
                        st.error("Please specify both old and new column names.")
                        valid = False
                elif step_type == "split":
                    if not cfg.get("column") or not cfg.get("sep"):
                        st.error("Please specify column and separator.")
                        valid = False
                elif step_type == "merge":
                    if len(cfg.get("columns", [])) < 2:
                        st.error("Please select at least two columns to merge.")
                        valid = False
                elif step_type == "range":
                    if not cfg.get("column"):
                        st.error("Please select a numeric column.")
                        valid = False
                elif step_type == "join":
                    if not cfg.get("right") or not cfg.get("left_key") or not cfg.get("right_key"):
                        st.error("Please configure all join parameters.")
                        valid = False
                if valid:
                    st.session_state.transform_steps.append(op)
                    st.rerun()
        with c2:
            if st.button("Clear Steps"):
                st.session_state.transform_steps = []
                st.rerun()

        # --- Apply transformations ---
        # Ensure cleaned_selected is always defined before use
        if selected and len(st.session_state.get("selected_columns", [])) > 0:
            selected_columns_set = set(st.session_state.get("selected_columns", []))
            cleaned_selected = cleaned_df[[col for col in cleaned_df.columns if col in selected_columns_set]].copy()
        else:
            cleaned_selected = pd.DataFrame()
        
        if selected and st.session_state.transform_steps:
            try:
                transformed_selected, applied_labels, errors = apply_transforms(cleaned_selected, st.session_state.transform_steps)
            except Exception as e:
                st.error(f"Transformation error: {e}. Showing untransformed data.")
                transformed_selected = cleaned_selected
                applied_labels = []
                errors = []
        elif selected:
            transformed_selected = cleaned_selected
            applied_labels = []
            errors = []
        else:
            # Empty selection - use empty dataframes
            raw_selected = pd.DataFrame()
            cleaned_selected = pd.DataFrame()
            column_types_selected = detect_column_types(raw_selected) if raw_selected is not None else {}
            transformed_selected = pd.DataFrame()
            applied_labels = []
            errors = []    # --- Propagate transformations to main pipeline ---
    # Compute filtered_selected: preserves BOTH sidebar filters and column selection
    selected_columns_set = set(st.session_state.get("selected_columns", []))
    if selected_columns_set:
        # Start with filtered_df (has sidebar filters), keep only selected columns
        filtered_selected = filtered_df[[col for col in filtered_df.columns if col in selected_columns_set]].copy()
    else:
        # No column selection: just use filtered_df with sidebar filters preserved
        filtered_selected = filtered_df
    # Apply transformation steps if configured, overriding the base transformed_df
    if "transform_steps" in st.session_state and st.session_state.transform_steps:
        try:
            transformed_df, applied_labels, errors = apply_transforms(filtered_selected, st.session_state.transform_steps)
        except Exception as e:
            st.error(f"Transformation error: {e}. Showing untransformed data.")
            transformed_df = filtered_selected
            applied_labels = []
            errors = []
    else:
        transformed_df = filtered_selected

    with tabs[2]:

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
    with tabs[3]:
        render_dashboard_banner(theme, theme_name, branding)
        render_metric_cards(kpis, theme)
        
        # Chart guide
        st.subheader("Chart Selection Guide")
        st.caption("Choose the right chart type for your data")
        chart_guide_df = pd.DataFrame(CHART_GUIDE)
        st.dataframe(chart_guide_df, use_container_width=True, hide_index=True)
        
        # Chart type selection
        st.subheader("Chart Type Selection")
        available = available_chart_types(column_types)
        col1, col2 = st.columns([2, 1])
        with col1:
            selected_chart_types = st.multiselect(
                "Select chart types to display",
                options=available,
                default=available,
                help="Select which chart types to show based on your data's column types"
            )
        with col2:
            st.caption(f"{len(selected_chart_types)} selected")
        
        # Custom chart builder
        st.subheader("Custom Chart Builder")
        st.caption("Build a custom chart with your chosen columns and aggregation")
        
        # Chart kind selector
        chart_kind = st.selectbox(
            "Chart Type",
            options=list(CHART_TYPE_LABELS.keys()),
            index=0,
            help="Select the type of chart to build"
        )
        
        # X and Y column selectors
        numeric_cols = column_types.get("numeric", []) + column_types.get("currency", []) + column_types.get("percentage", [])
        categorical_cols = column_types.get("categorical", [])
        datetime_cols = column_types.get("datetime", [])
        
        col1, col2 = st.columns(2)
        with col1:
            x_col = st.selectbox("X Column", options=[None] + list(df.columns), index=0)
        with col2:
            y_col = st.selectbox("Y Column", options=[None] + numeric_cols, index=0)
        
        # Aggregation selector
        agg = st.selectbox(
            "Aggregation",
            options=["sum", "mean", "median", "count"],
            index=0,
            help="Aggregation function for bar/line charts"
        )
        
        # Build chart button
        if st.button("Build Custom Chart", type="primary"):
            if x_col is None and y_col is None:
                st.error("Please select at least an X column or Y column.")
            else:
                try:
                    spec = build_custom_chart(
                        df, chart_kind, x_col, y_col,
                        agg=agg,
                        theme=theme,
                        column_types=column_types,
                    )
                    st.success(f"Chart built: {spec.title}")
                    # Display the chart
                    import plotly.express as px
                    fig = spec.figure
                    st.plotly_chart(fig, use_container_width=True)
                except ValueError as e:
                    st.error(f"Error building chart: {e}")
        
        # Show applicable chart types info
        if selected_chart_types:
            st.info(f"Based on your data columns, applicable chart types are: {', '.join(selected_chart_types)}")

        # Render the default charts with filtered types
        if selected_chart_types:
            filtered_charts = [c for c in charts if c.kind in selected_chart_types]
        else:
            filtered_charts = charts
        render_charts(filtered_charts, theme)

    # --- Tab 4: Pivot Tables ---
    with tabs[4]:
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
    with tabs[5]:
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
    with tabs[6]:
        _section("Download Reports")

        report_mode = st.radio(
            "Client report content",
            options=["Summary only", "Tables", "Charts", "Tables + Charts"],
            index=3,
            horizontal=True,
        )
        include_tables = report_mode in {"Tables", "Tables + Charts"}
        include_charts = report_mode in {"Charts", "Tables + Charts"}

        excel_bytes = dataframe_to_excel(transformed_df, pivots)
        csv_bytes = dataframe_to_csv(transformed_df)
        summary_bytes = export_summary_report(summary, cleaning_report, kpis, insights, recommendations, pivots)
        pdf_bytes = make_custom_pdf_report(
            summary, cleaning_report, insights, recommendations, pivots, charts, include_tables, include_charts
        )
        ppt_bytes = make_ppt_report(
            summary, cleaning_report, insights, recommendations, pivots, charts, include_tables, include_charts
        )

        st.markdown("**Data exports**")
        d1, d2, d3 = st.columns(3)
        with d1:
            st.download_button(
                "Transformed Excel",
                excel_bytes,
                file_name="transformed_analytics_workbook.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        with d2:
            st.download_button(
                "Transformed CSV", csv_bytes, file_name="transformed_dataset.csv", mime="text/csv"
            )
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

        st.caption("Choose whether the PDF/PPT deliverable includes pivot tables, charts, both, or summary only.")


if __name__ == "__main__":
    main()
