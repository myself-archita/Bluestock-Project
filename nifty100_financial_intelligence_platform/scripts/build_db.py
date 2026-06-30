from __future__ import annotations

from pathlib import Path
import sqlite3
import sys
import pandas as pd

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from src.config import DB_PATH

PROCESSED = BASE / "data" / "processed"


def main() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript((BASE / "src" / "db" / "schema.sql").read_text(encoding="utf-8"))
        pd.read_csv(PROCESSED / "companies.csv").to_sql("companies", conn, if_exists="replace", index=False)
        pd.read_csv(PROCESSED / "financials.csv").to_sql("financials", conn, if_exists="replace", index=False)
        ratios = pd.read_csv(PROCESSED / "financials.csv")
        ratios["npm"] = ratios["pat"] / ratios["sales"]
        ratios["opm"] = ratios["operating_profit"] / ratios["sales"]
        ratios["roe"] = ratios["pat"] / ratios["equity"]
        ratios["roce"] = ratios["operating_profit"] / (ratios["equity"] + ratios["debt"])
        ratios["debt_equity"] = ratios["debt"] / ratios["equity"]
        ratios["interest_coverage"] = ratios["operating_profit"] / (ratios["debt"] * 0.08 + 1e-9)
        ratios["asset_turnover"] = ratios["sales"] / ratios["assets"]
        ratios["fcf"] = ratios["cfo"] - ratios["capex"]
        ratios["cfo_quality_score"] = ratios["cfo"] / ratios["pat"]
        ratios["capex_intensity"] = ratios["capex"] / ratios["sales"]
        ratios["fcf_conversion"] = ratios["fcf"] / ratios["cfo"]
        ratios["capital_allocation_class"] = "balanced"
        ratios[["ticker","year","npm","opm","roe","roce","debt_equity","interest_coverage","asset_turnover","fcf","cfo_quality_score","capex_intensity","fcf_conversion","capital_allocation_class"]].to_sql("financial_ratios", conn, if_exists="replace", index=False)


if __name__ == "__main__":
    main()
