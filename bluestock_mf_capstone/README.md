# Bluestock Mutual Fund Capstone

This folder is a submission-ready scaffold for the mutual fund analytics capstone.

## Layout

- `data/raw/` — downloaded source CSVs
- `data/processed/` — cleaned CSV outputs
- `data/db/` — SQLite database outputs
- `notebooks/` — EDA, analytics, and advanced analysis notebooks
- `scripts/` — ETL, NAV fetch, metrics, and recommender scripts
- `sql/` — schema and reusable queries
- `dashboard/` — Power BI or Tableau deliverable
- `reports/` — final report and presentation assets

## Included scripts

- `scripts/etl_pipeline.py`
- `scripts/live_nav_fetch.py`
- `scripts/compute_metrics.py`
- `scripts/recommender.py`

## Notes

- `.db` files are ignored by Git; share `sql/schema.sql` instead of committing the database file.
- The current scaffold reuses the working ETL logic already present in this repo.
- Populate the notebook, dashboard, report, and slide assets as you finalize the capstone.
