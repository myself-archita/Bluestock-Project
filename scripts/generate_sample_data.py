from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent.parent
RAW = BASE / "data" / "raw"
PROCESSED = BASE / "data" / "processed"
RAW.mkdir(parents=True, exist_ok=True)
PROCESSED.mkdir(parents=True, exist_ok=True)

rng = np.random.default_rng(7)
tickers = [f"COMP{i:03d}" for i in range(1, 13)]
years = list(range(2014, 2025))

companies = pd.DataFrame({
    "ticker": tickers,
    "company_name": [f"Company {i}" for i in range(1, 13)],
    "sector": ["IT", "Banking", "FMCG", "Auto"] * 3,
    "industry": ["Software", "Private Bank", "Consumer", "OEM"] * 3,
    "is_bank": [0, 1, 0, 0] * 3,
})
companies.to_csv(PROCESSED / "companies.csv", index=False)

rows = []
for ticker in tickers:
    base = rng.uniform(500, 5000)
    for year in years:
        sales = base * (1 + 0.08 * (year - years[0])) * rng.uniform(0.9, 1.1)
        op = sales * rng.uniform(0.1, 0.25)
        pat = op * rng.uniform(0.6, 0.9)
        equity = rng.uniform(200, 4000)
        debt = rng.uniform(0, 2000)
        assets = equity + debt + rng.uniform(100, 1000)
        cfo = pat * rng.uniform(0.8, 1.4)
        capex = sales * rng.uniform(0.03, 0.15)
        eps = pat / rng.uniform(10, 40)
        rows.append([ticker, year, sales, op, pat, equity, debt, assets, cfo, capex, eps])

financials = pd.DataFrame(rows, columns=["ticker", "year", "sales", "operating_profit", "pat", "equity", "debt", "assets", "cfo", "capex", "eps"])
financials.to_csv(PROCESSED / "financials.csv", index=False)

all_data = companies.merge(financials, on="ticker")
all_data["revenue_cagr_5y"] = all_data["sales"].pct_change().fillna(0)
all_data.to_csv(RAW / "sample_financial_source.csv", index=False)
print("Sample data generated.")
