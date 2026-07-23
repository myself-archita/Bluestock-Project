# NIFTY 100 Financial Intelligence Platform

This submission is a compact, self-contained prototype built from the sprint brief.

## Included

- ETL helpers for Excel loading and ticker/year normalisation
- Data quality validation and SQLite schema/loader
- Profitability, leverage, CAGR, cash flow, and peer percentile analytics
- Screener engine with YAML-driven filters and scoring
- FastAPI service and Streamlit dashboard entry point
- Tests for the core normalisation and ratio logic

## Run

```bash
python -m pip install -r requirements.txt
python scripts/generate_sample_data.py
python scripts/build_db.py
streamlit run app.py
```

## API

```bash
uvicorn src.api.main:app --reload
```

## Notes

The original brief refers to 92 companies and 12 source files. This package includes a reproducible scaffold plus synthetic sample generation so the project can be reviewed, run, and expanded without external dependencies.
## Sprint 4 dashboard

Run the eight-screen Streamlit dashboard from the project directory:

```bash
streamlit run src/dashboard/app.py
```

Screens: Home (KPI overview and sector mix), Company Profile (multi-year financials), Screener (preset filters and CSV export), Peer Comparison (radar benchmark), Trend Analysis (metric overlays), Sector Analysis (company scatter and medians), Capital Allocation (treemap), and Annual Reports (report availability).

Generate valuation outputs with:

```bash
python -m src.analytics.valuation
```

Outputs are written to `output/valuation_summary.xlsx` and `output/valuation_flags.csv`. The data layer caches database queries for 10 minutes and displays `N/A` for missing values so partial company histories remain usable.
