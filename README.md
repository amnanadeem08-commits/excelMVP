# Excel Automation & AI Reporting Tool

**GitHub:** https://github.com/amnanadeem08-commits/excelMVP

A freelance-ready, Python-based tool that automates the work a client would normally do by hand in Excel. Upload a spreadsheet and the app reads it, cleans and structures the data, generates pivot-table analytics and KPIs, builds an interactive dashboard, surfaces AI-style insights, and exports client-ready Excel, PDF, and PowerPoint reports.

Built for real freelance use cases: small-business reporting, sales analysis dashboards, and HR/finance Excel automation jobs on Fiverr/Upwork.

## Features

### 1. Excel input system
- Upload `.xlsx`, `.xls`, and `.csv` files
- Multi-sheet Excel support with a sheet selector
- Automatic structure detection (rows, columns, column roles, missing values)

### 2. Data cleaning engine (pandas)
- Standardizes column names (trim, de-duplicate)
- Removes duplicate rows and fully empty columns
- Handles missing values intelligently (median for numbers, mode for categories, fill for dates)
- Detects date / number / text / currency / percentage / boolean columns and fixes their types
- Caps extreme outliers and returns a transparent cleaning report

### 3. Automation layer
- Auto-generates pivot-table equivalents using pandas `groupby` (by category and by month)
- Auto-calculates KPIs: total, average, growth %, and top categories

### 4. Dashboard module (Streamlit + Plotly)
- KPI cards (Total, Average, Growth %, Data Quality)
- Bar charts (top categories/products) and pie share charts
- Line charts (trends over time)
- Distribution, scatter, and correlation visuals
- Sidebar filters for category and date range

### 5. Export system
- Cleaned dataset to Excel and CSV
- Structured multi-sheet Excel summary report (overview, KPIs, cleaning, insights, recommendations, pivots)
- High-resolution chart images embedded into deliverables
- Branded client PDF report and PowerPoint deck

### 6. AI insight layer (the "brain")
`generate_ai_insights(df)` turns cleaned data into a structured, client-ready report:
1. **Dataset Summary** - auto-detects the dataset type (sales, finance, HR, inventory, marketing) and explains what it represents in plain business language.
2. **Key Insights** - top/worst performing category or product, trend (growth/decline), and key patterns.
3. **Problems / Anomalies** - unusual spikes/drops vs. the average trend, abnormal values, and missing-data patterns (e.g. "Sales dropped by 35% in March compared to the average trend").
4. **Recommendations** - 3-5 actionable suggestions (e.g. "Focus marketing on Product A as it contributes 42% of total revenue").

Rule-based by default so it works offline with any Excel file; optionally upgrades to an LLM when `OPENAI_API_KEY` is set (see below). The pipeline builds a pandas summary, converts it to a structured prompt, sends it to the LLM (OpenAI/Claude placeholder), and returns the four sections.

## Build Phases

### Phase 1 - Core Excel Automation (applied)
- Read Excel/CSV files, including multi-sheet workbooks.
- Clean messy spreadsheet data with pandas.
- Detect column roles and generate pivot-table-style summaries.
- Calculate executive KPIs and chart-ready summaries.

### Phase 2 - Dynamic Dashboard Builder (applied)
- Add left-sidebar theme controls with preset and custom brand palettes.
- Add client branding controls for company name and logo.
- Add dashboard focus modes: AI Recommended, Executive Summary, Sales / Revenue, Operations, and Finance.
- Add chart density and layout controls so the same dataset can become a compact dashboard or a deeper analysis view.
- Add an AI dashboard brief that surfaces the leading insight, anomaly to watch, and recommended action.

### Phase 3 - AI Analyst Layer (next)
- Expand the LLM prompt to include user-selected business goals.
- Let the user choose insight tone: executive, analyst, sales, finance, or operations.
- Add "Ask this dataset" chat for follow-up questions about the uploaded file.
- Save AI notes into exported PDF/PPT reports.

### Phase 4 - Excel Macro-Style Workflow (next)
- Add repeatable workflow templates such as sales report, HR report, inventory report, and finance report.
- Add one-click "refresh analysis" behavior for newly uploaded monthly files.
- Export pivot sheets and chart sheets in an Excel workbook that feels like a macro-generated report.
- Optionally add VBA macro export stubs for clients who require native Excel buttons.

### Phase 5 - Client Delivery Polish (next)
- Add saved theme presets per client.
- Add report cover pages with client branding.
- Add upload history and saved dashboard configuration.
- Deploy on Streamlit Cloud or a small VPS for client demos.

## Project Structure

```text
excelMVP/
|-- app.py                # Streamlit UI (thin orchestration layer)
|-- data_loader.py        # File input, multi-sheet, structure detection
|-- data_cleaning.py      # Pandas cleaning engine + column type detection
|-- analytics_engine.py   # Pivot automation, KPIs, growth calculations
|-- dashboard.py          # Plotly charts, KPI cards, filters, styling
|-- ai_insights.py        # Business-language explanation, insights, AI stub
|-- export_module.py      # Excel / CSV / summary / PDF / PPT exports
|-- requirements.txt
|-- README.md
|-- reports/  uploads/  assets/
```

## Setup

```powershell
cd D:\excelMVP
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```powershell
streamlit run app.py
```

Then open the URL Streamlit prints (default `http://localhost:8501`).

## How To Use

1. Upload an Excel or CSV file from the sidebar or main page.
2. For multi-sheet Excel files, pick the sheet to analyze.
3. Review the dataset preview, detected column types, and cleaning report.
4. Use the sidebar filters to slice by category and date.
5. Explore the Executive Summary, Dashboard, Pivot Tables, and AI Insights tabs.
6. In Downloads, choose the report content (summary only / tables / charts / both) and download the cleaned data, the Excel summary report, the client PDF, or the PowerPoint deck.

## Optional: Enable real AI narratives

The app works fully offline with a rule-based insight engine. To enable LLM-written explanations:

1. `pip install openai` (or uncomment it in `requirements.txt`).
2. Set an environment variable before running:

```powershell
$env:OPENAI_API_KEY = "your-key"
streamlit run app.py
```

If the key or package is missing, the app silently falls back to the rule-based engine, so it never breaks.

## Customization Notes (for freelance jobs)

- **Branding:** Change titles/colors in `export_module.py` (PDF/PPT theme) and `dashboard.py` (`inject_styles`).
- **Cleaning behavior:** Tune missing-value strategy and outlier sensitivity in `data_cleaning.py`.
- **Primary metric:** Adjust `PRIORITY_METRIC_WORDS` in `analytics_engine.py` to control which column drives KPIs.
- **Charts:** Add chart types in `dashboard.py` (`generate_charts`).

## Deployment (Streamlit Community Cloud)

1. Push the project to GitHub.
2. Go to `https://share.streamlit.io` and connect your repo.
3. Set the main file path to `app.py` and deploy.

## Notes

- Charts avoid Plotly OLS trendlines, so `statsmodels` is not required.
- Chart image export requires `kaleido` (already in `requirements.txt`).
- The tool is designed for exploratory business analytics and executive reporting, not regulated financial or medical decision-making.
