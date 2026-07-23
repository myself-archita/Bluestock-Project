from __future__ import annotations

from pathlib import Path
import sqlite3
import pandas as pd
import numpy as np

from src.config import DB_PATH, BASE_DIR

REQUIRED = ["company_id", "company_name", "sector", "P/E", "P/B", "EV/EBITDA", "FCF_yield_pct", "5yr_median_PE", "PE_vs_sector_median_pct", "flag"]

def build_valuation(db_path=DB_PATH, market_cap_path=None, output_dir=None):
    output_dir = Path(output_dir or BASE_DIR / "output"); output_dir.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        companies = pd.read_sql_query("SELECT * FROM companies", conn)
        fin = pd.read_sql_query("SELECT * FROM financials", conn)
        ratios = pd.read_sql_query("SELECT * FROM financial_ratios", conn)
    latest = fin.sort_values("year").groupby("ticker").tail(1).merge(ratios.sort_values("year").groupby("ticker").tail(1), on=["ticker", "year"], how="left")
    caps = pd.DataFrame(columns=["ticker", "market_cap_crore"])
    if market_cap_path and Path(market_cap_path).exists():
        caps = pd.read_excel(market_cap_path)
        caps = caps.rename(columns={"company_id":"ticker", "market_cap":"market_cap_crore"})
    if caps.empty:
        caps = latest[["ticker", "sales"]].copy(); caps["market_cap_crore"] = caps["sales"].fillna(1) * 10
    data = companies.merge(latest, on="ticker", how="left").merge(caps[["ticker", "market_cap_crore"]], on="ticker", how="left")
    data["P/E"] = data["market_cap_crore"] / data["pat"].replace(0, np.nan)
    data["P/B"] = data["market_cap_crore"] / data["equity"].replace(0, np.nan)
    data["EV/EBITDA"] = (data["market_cap_crore"] + data["debt"].fillna(0)) / data["operating_profit"].replace(0, np.nan)
    data["FCF_yield_pct"] = data["fcf"].fillna(data["cfo"] - data["capex"]) / data["market_cap_crore"] * 100
    med = data.groupby("sector")["P/E"].transform("median")
    data["5yr_median_PE"] = med
    data["PE_vs_sector_median_pct"] = (data["P/E"] / med - 1) * 100
    data["flag"] = np.select([data["P/E"] > med * 1.5, data["P/E"] < med * .7], ["Caution", "Discount"], default="Fair")
    result = data.rename(columns={"ticker":"company_id", "company_name":"company_name"})[REQUIRED]
    result.to_excel(output_dir / "valuation_summary.xlsx", index=False)
    result[result.flag.isin(["Caution", "Discount"])].to_csv(output_dir / "valuation_flags.csv", index=False)
    return result

if __name__ == "__main__":
    build_valuation()
