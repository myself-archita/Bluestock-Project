# Day 1 Mutual Fund ETL

This mini-project is separate from the existing website files in this repo.

## Folder layout

Place the 10 provided CSVs in:

- `data/raw/`

The other folders are ready for outputs:

- `data/processed/`
- `notebooks/`
- `sql/`
- `dashboard/`
- `reports/`

## Install dependencies

```bash
pip install -r requirements.txt
```

## Run the dataset audit

```bash
python data_ingestion.py
```

What it does:

- prints `.shape`, `.dtypes`, and `.head()` for every CSV in `data/raw/`
- flags simple data-quality issues
- checks `fund_master` against `nav_history`
- writes summary files into `reports/`

## Run everything at once

```powershell
.\run_day1_etl.ps1
```

This runs the audit first and then fetches the live NAV snapshots into `data/raw/`.

## Fetch live NAV data

```bash
python live_nav_fetch.py
```

What it does:

- fetches live NAV history from `mfapi.in`
- saves one raw CSV per scheme in `data/raw/`
- writes a combined snapshot and metadata file

## Expected outputs

- `data/raw/live_nav_snapshot.csv`
- `data/raw/live_nav_fetch_metadata.json`
- `reports/day1_ingestion_summary.json`
- `reports/amfi_code_validation.csv`

## Notes

- If your raw dataset filenames differ, rename them so `fund_master` and `nav_history` are easy to identify.
- The scripts are safe to rerun; they overwrite the generated outputs.
