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
