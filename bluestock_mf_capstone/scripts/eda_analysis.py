from __future__ import annotations

"""Prepare EDA summaries and chart-ready outputs for the capstone."""

import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parents[1]
DATA_RAW_DIR = REPO_ROOT / "data" / "raw"
DATA_PROCESSED_DIR = REPO_ROOT / "data" / "processed"
REPORTS_DIR = REPO_ROOT / "reports"


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    summary = {
        "status": "template",
        "message": (
            "EDA notebook scaffold created for NAV trends, AUM growth, SIP inflow, "
            "investor demographics, geography, folio growth, correlation, and sector allocation."
        ),
        "expected_inputs": [
            "nav_history_cleaned.csv",
            "benchmark_nav_cleaned.csv",
            "scheme_performance_cleaned.csv",
            "portfolio_holdings.csv",
            "investor_demographics.csv",
            "sip_inflows.csv",
            "aum_by_fund_house.csv",
        ],
    }
    (REPORTS_DIR / "eda_analysis_template.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
