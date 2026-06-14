# Bluestock Mutual Fund Capstone

This project analyzes mutual fund performance, investor behavior, and portfolio concentration using cleaned NAV, transaction, and fund master datasets.

## Project Overview

- ETL pipeline cleans raw CSVs and loads the curated outputs into the project structure.
- Analytics notebooks cover EDA, performance metrics, and advanced risk analysis.
- Dashboard assets summarize fund trends, investor segments, SIP activity, and sector allocation.
- Final deliverables include a report, presentation, and reusable Python scripts.

## Setup

1. Install Python 3.10+.
2. Use the bundled project dependencies or create a virtual environment.
3. Install the required packages if needed:
   - `pandas`
   - `numpy`
   - `sqlalchemy`
   - `requests`
   - `python-docx`
   - `reportlab`
4. Open the `bluestock_mf_capstone` folder in your editor or notebook environment.

## How to Run the ETL

Run the master pipeline:

```bash
python run_pipeline.py
```

Or run individual stages:

```bash
python scripts/etl_pipeline.py
python scripts/compute_metrics.py
python scripts/eda_analysis.py
python scripts/performance_analytics.py
python scripts/recommender.py Moderate
```

## Dashboard

- The dashboard assets live in `reports/`.
- Open the published dashboard if you have a Power BI Service or Tableau Public URL.
- If you publish a dashboard later, add the public link here:
  - Dashboard URL: _add your published link_

## Dataset Descriptions

- `nav_history_cleaned.csv` — daily NAV history by scheme.
- `fund_master_cleaned.csv` — scheme metadata including category and risk grade.
- `scheme_performance_cleaned.csv` — expense ratio and return snapshots.
- `investor_transactions_cleaned.csv` — transaction-level investor activity.
- `portfolio_holdings.csv` — sector weights used for HHI concentration analysis.
- `var_cvar_report.csv` — historical VaR and CVaR summary by fund.
- `rolling_sharpe.csv` — 90-day rolling Sharpe ratio series.
- `investor_cohort_analysis.csv` — cohort-level SIP metrics.
- `sip_continuity_analysis.csv` — average SIP gap and at-risk flags.
- `sector_hhi_concentration.csv` — sector concentration scores.

## Key Deliverables

- `Advanced_Analytics.ipynb`
- `Final_Report.pdf`
- `Bluestock_MF_Presentation.pptx`
- `var_cvar_report.csv`
- `recommender.py`
- `rolling_sharpe_chart.png`

