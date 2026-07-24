# Mutual Fund ETL

Standalone Day 1 project for mutual fund dataset ingestion, live NAV fetching, and basic AMFI code validation.

## Start here

- Read `DAY1_MUTUAL_FUND_ETL_README.md` for setup and run instructions
- Use `run_day1_etl.ps1` to run the full Day 1 flow in one command

## Structure

- `data/` — raw and processed inputs
- `notebooks/` — starter exploration notebook
- `reports/` — validation and audit outputs
- `sql/` — reserved for future SQL work
- `dashboard/` — reserved for visualization work
- `dashboard/` — reserved for visualization work

## Sprint 4 dashboard

Run the eight-screen Streamlit dashboard:

```bash
streamlit run src/dashboard/app.py
```

Screens include Home, Company Profile, Screener with CSV export, Peer Comparison, Trend Analysis, Sector Analysis, Capital Allocation, and Annual Reports.

Generate valuation outputs with:

```bash
python -m src.analytics.valuation
```

Outputs are written to `output/valuation_summary.xlsx` and `output/valuation_flags.csv`.

## Sprint 5 NLP, cash flow, and reports

Generate the Sprint 5 artifacts with:

```bash
python -m src.nlp.parser
python -m src.nlp.pros_cons_generator
python -m src.analytics.cashflow_kpis
python -m src.reports.tearsheet
```

The report modules create company tearsheets, sector reports, and the portfolio summary under `reports/`. The implementation preserves partial histories and uses `N/A`/fallback narrative text when optional source fields are unavailable.
