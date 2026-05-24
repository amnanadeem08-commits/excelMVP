# Excel AI Analytics Assistant

A professional Streamlit MVP for automated Excel and CSV analytics. The app behaves like a lightweight AI-powered Excel assistant: upload a spreadsheet, clean the data, generate executive KPIs, build pivot tables, create Plotly charts, and export analysis-ready reports.

## Features

- Upload `.xlsx`, `.xls`, and `.csv` files
- Excel sheet selector
- Dataset preview, shape, and column profiling
- Smart data type detection for numeric, categorical, boolean, datetime, currency, and percentage columns
- Automated data cleaning for missing values, duplicate rows, empty columns, whitespace, invalid dates, and outliers
- Executive summary and KPI cards
- Automatic statistical analysis and correlation matrix
- Smart pivot table generation
- Interactive Plotly charts
- AI-style business insights and recommendations
- Sidebar filters for categories and date ranges
- Export cleaned Excel, cleaned CSV, pivot tables, and PDF summary report

## Project Structure

```text
excelMVP/
├── app.py
├── README.md
├── requirements.txt
├── utils/
│   ├── __init__.py
│   ├── analyzer.py
│   ├── chart_engine.py
│   ├── data_cleaner.py
│   ├── helpers.py
│   ├── insight_engine.py
│   └── pivot_engine.py
├── reports/
├── uploads/
└── assets/
```

## Requirements

- Python 3.10 or newer
- Streamlit
- pandas
- numpy
- Plotly
- openpyxl
- xlrd
- scikit-learn
- scipy
- kaleido
- reportlab

## Setup

Open a terminal in the project folder:

```powershell
cd D:\excelMVP
```

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

## Run The App

```powershell
streamlit run app.py
```

If you want to use the same local port used during development:

```powershell
streamlit run app.py --server.port 8510
```

Then open:

```text
http://localhost:8510
```

## How To Use

1. Upload an Excel or CSV file from the main page or sidebar.
2. If the file is Excel, choose the workbook sheet.
3. Review the dataset preview and cleaning report.
4. Use sidebar filters to focus the analysis.
5. Open the executive summary, charts, pivots, and insights tabs.
6. Download cleaned datasets, pivot tables, or the PDF summary report.

## Core Modules

- `utils/data_cleaner.py`: data type detection and automated cleaning
- `utils/analyzer.py`: executive summary, KPIs, statistics, and correlations
- `utils/pivot_engine.py`: automatic pivot table creation
- `utils/chart_engine.py`: smart Plotly chart generation
- `utils/insight_engine.py`: business insights and recommendations
- `utils/helpers.py`: file reading, exports, PDF generation, and UI helpers

## Notes

- The app avoids Plotly OLS trendlines so it does not require `statsmodels`.
- Chart PNG export is available from each Plotly chart toolbar.
- The MVP is designed for exploratory business analytics and executive reporting, not regulated financial or medical decision-making.
