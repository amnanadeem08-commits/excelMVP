# Excel Dashboard Studio

**GitHub:** https://github.com/amnanadeem08-commits/excelMVP

A freelance-ready, Python-based tool (formerly *Excel Automation & AI Reporting Tool*) that automates the work a client would normally do by hand in Excel. Upload a spreadsheet and the app reads it, cleans and structures the data, generates pivot-table analytics and KPIs, builds an interactive dashboard, lets you reshape the data safely, surfaces AI-style insights, and exports client-ready Excel, PDF, and PowerPoint reports.

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

### 3. Analytics and pivot-style summaries
- Auto pivot-table equivalents via pandas `groupby`: measure by category (sum / mean / median / count), measure by month, and record counts
- Every category pivot includes **`share_pct`** — each row's share of the full dataset total
- Automatic **KPI selection with validation**: identifier-like columns (Order ID, Row Number, SKU, ...) and constant columns are excluded from the headline metric
- KPI cards with clear labels ("Total Revenue", "Average Revenue") and measure-aware formatting (percentages render as `12.3%`, growth renders as `▲ 12.3%` / `▼ 12.3%`)

### 4. Dashboard (Streamlit + Plotly)
- KPI cards (Records, Data Quality, headline metric, Growth / Top Segment)
- **KPI semantics**: totals only for additive measures (revenue, quantity); continuous measures (age, ratings, prices) show Average + Median instead of a meaningless total; rates render as averaged percentages
- **KPI Settings sidebar**: override the automatic headline metric and aggregation (Auto / Total / Average / Median)
- **Themes**: Light Professional, Dark, and six client palettes; themes drive surfaces, cards, chart backgrounds, and text (not just accents)
- Six interactive chart types: bar, line, pie/donut, histogram, scatter, correlation heatmap
- **Chart selection guide** — in-app table explaining when each chart should (and should not) be used
- **Chart controls** — show/hide chart types, choose category sorting (descending / ascending / alphabetical), and set top-N categories
- **Custom chart builder** — pick the chart type, X/Y columns, aggregation (sum/mean/median/count/min/max), a custom title, and axis labels, with clear error messages when a selection is unsuitable
- Sidebar filters for category and date range; filters exclude everything → a clear error explains what to fix
- Client branding: company name, logo, and preset or custom hex color themes

### 5. Data Tools (safe, user-controlled transformations)
Steps are recorded, replayed in order, and shown as a numbered log. Your original file is never modified, and **Clear all steps** reverts everything. Implemented now:
- **Column selection** — keep only the columns you choose
- **Rename** one column
- **Split** a column into parts on a separator (original column kept)
- **Merge** several columns into one new column
- **Numeric range filter** — keep rows within a min/max band on any measure
- **Join a second spreadsheet** (left or inner) on a key column, e.g. a price list onto sales data

Everything in Data Tools flows into every tab and into the exports. See *Limitations* below for what is not implemented.

### 6. Export system
- **CSV and Excel (current view)** — reflect the active filters and Data Tools steps; the Excel workbook includes one sheet per pivot table
- Structured multi-sheet Excel summary report (Overview, KPIs, Cleaning Report, Insights, Recommendations, pivots)
- **Client PDF and PowerPoint** — built on demand from the Downloads tab (chart image rendering takes about a minute the first time, then results are reused until the data or options change); chart images are rendered once and shared between both files
- Reports carry the product name, generation date, and data period; the deck includes a Data Quality & Methodology slide and consistent footers
- **Export status is visible**: the app reports how many chart images were embedded and warns when kaleido/Chrome cannot render them
- CSV/Excel exports guard against spreadsheet formula injection (text cells starting with `=`, `+`, `@` are quoted; a leading `-` is preserved so negative values stay intact)
- PDF pivot headings stay attached to their tables (no orphaned headings across page breaks)

### 7. AI insight layer (the "brain")
`generate_ai_insights(df)` turns cleaned data into a structured, client-ready report:
1. **Dataset Summary** — auto-detects the dataset type (sales, finance, HR, inventory, marketing) and explains it in plain business language.
2. **Key Insights** — top/worst performing category, trend (growth/decline), key patterns.
3. **Problems / Anomalies** — unusual spikes/drops vs. the average trend, abnormal values, missing-data patterns.
4. **Recommendations** — actionable suggestions.

Rule-based by default so it works offline with any Excel file; optionally upgrades to an LLM when `OPENAI_API_KEY` is set (see below).

## Specification documents

Product requirements live at the repository root and drive the implementation:

- [DESIGN.md](DESIGN.md) — dashboard UX, themes, accessibility, chart/KPI rules
- [PRESENTATION.md](PRESENTATION.md) — PowerPoint storytelling and slide design
- [EXECUTIVE_STORY.md](EXECUTIVE_STORY.md) — evidence-based insights and recommendations
- [EXPORT.md](EXPORT.md) — export quality and fidelity requirements
- [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) — integration plan
- [REQUIREMENTS_MAP.md](REQUIREMENTS_MAP.md) — requirement → code map with implemented/partial/missing status and test evidence
- [ADD_TO_EXCEL_MVP_PROMPT.md](ADD_TO_EXCEL_MVP_PROMPT.md) — provenance of the specification set

## Project Structure

```text
excelMVP/
|-- app.py                # Streamlit UI (thin orchestration layer)
|-- data_loader.py        # File input, multi-sheet, structure detection
|-- data_cleaning.py      # Pandas cleaning engine + column type detection
|-- analytics_engine.py   # Pivot automation, KPIs, growth calculations
|-- dashboard.py          # Chart generation, chart guide/controls, custom builder, styling
|-- transformations.py    # Validated data transformation steps (pure pandas)
|-- ai_insights.py        # Business-language explanation, insights, AI stub
|-- export_module.py      # Excel / CSV / summary / PDF / PPT exports
|-- requirements.txt
|-- pytest.ini            # pytest config (testpaths, pythonpath)
|-- tests/                # 79 tests covering every module + an app smoke test
|-- reports/  uploads/  assets/
```

## Setup

```powershell
cd D:\excelMVP
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

**Note on chart image export (PDF/PPT):** the project uses `kaleido` v1, which renders Plotly charts with a locally installed Chrome or Edge. If neither is available, kaleido will tell you; you can install its own copy with:

```powershell
python -c "import kaleido; kaleido.get_chrome_sync()"
```

## Run

```powershell
streamlit run app.py
```

Then open the URL Streamlit prints (default `http://localhost:8501`).

## How To Use

1. Upload an Excel or CSV file from the sidebar or main page.
2. For multi-sheet Excel files, pick the sheet to analyze.
3. **Dataset tab** — review the preview, detected column types, and cleaning report.
4. Use the **sidebar filters** to slice by category and date.
5. **Executive Summary** — KPI cards, plain-language overview, statistics, correlations.
6. **Dashboard** — open the *Chart selection guide*, adjust *Chart controls* (types, sorting, top-N), and optionally build a custom chart.
7. **Pivot Tables** — automated grouped summaries with share-of-total percentages; download any pivot as CSV.
8. **Data Tools** — apply column selection, rename, split, merge, range filters, or join a second file; watch the numbered step log.
9. **AI Insights** — summary, insights, anomalies, recommendations.
10. **Downloads** — grab the CSV/Excel current view and the summary workbook instantly; click **Build PDF & PowerPoint** once for the client deliverables (choose summary / tables / charts / both).

## Tests

```powershell
python -m pytest
```

The suite (100+ tests) covers file input, cleaning, type detection, KPI semantics and overrides, pivots and share percentages, insights, every transformation step, themes, chart generation options, the custom chart builder, export fidelity (formula guard, unicode, empty data, methodology slide content, real embedded chart images in PDF/PPT), and full-app smoke tests that run the Streamlit UI with a simulated upload — including a dark-theme switch check.

## Limitations: implemented vs. not implemented

**Implemented and verified**
- Cleaning, type detection, pivots with share %, validated KPIs, six chart types, chart guide/controls/builder, sidebar filters, the six Data Tools transformations listed above, CSV/Excel/summary exports, PDF/PPT exports with embedded chart images, optional LLM narratives.

**Not implemented (future enhancements — do not promise these to clients yet)**
- **Native Excel PivotTable objects / Power Query** — pivots are pandas `groupby` equivalents exported as plain sheets, not clickable Excel PivotTables, and there are no reusable transformation recipes or scheduled refreshes.
- **Live/interactive charts in PDF/PPT** — charts are exported as static high-resolution images.
- **Joins** — one second file at a time, left/inner only; no databases, no multi-key fuzzy matching.
- **File formats** — `.xlsx`, `.xls`, `.csv` only (no `.xlsb`, JSON, or Parquet).
- The tool is designed for exploratory business analytics and executive reporting, not regulated financial or medical decision-making.

## Optional: Enable real AI narratives

The app works fully offline with a rule-based insight engine. To enable LLM-written explanations:

1. `pip install openai` (or uncomment it in `requirements.txt`).
2. Set an environment variable before running:

```powershell
$env:OPENAI_API_KEY = "your-key"
streamlit run app.py
```

If the key or package is missing, the app silently falls back to the rule-based engine, so it never breaks. The key is read from the environment only and is never printed, logged, or embedded in exports.

## Customization Notes (for freelance jobs)

- **Branding:** Change titles/colors in `export_module.py` (PDF/PPT theme) and `dashboard.py` (`inject_styles`, `COLOR_THEMES`).
- **Cleaning behavior:** Tune missing-value strategy and outlier sensitivity in `data_cleaning.py`.
- **Primary metric:** Adjust `PRIORITY_METRIC_WORDS` (and `ID_COLUMN_TOKENS`) in `analytics_engine.py` to control which column drives KPIs.
- **Charts:** Add chart types in `dashboard.py` (`generate_charts`, `CHART_TYPE_LABELS`) and edit the in-app guide in `CHART_GUIDE`.
- **Transformations:** Add a new Data Tools operation by writing `_op_<kind>` in `transformations.py` and registering it in `_OPERATORS`.

## Deployment (Streamlit Community Cloud)

1. Push the project to GitHub.
2. Go to `https://share.streamlit.io` and connect your repo.
3. Set the main file path to `app.py` and deploy.
4. For PDF/PPT exports on the cloud, the deployment environment needs a Chromium/Chrome available to kaleido (local runs use your installed Chrome/Edge automatically).

## Notes

- Charts avoid Plotly OLS trendlines, so `statsmodels` is not required.
- Chart image export requires `kaleido>=1.5` plus a local Chrome/Edge (both pinned/documented in `requirements.txt`).
- `scikit-learn` and `scipy` are not used by this project and are not required.
