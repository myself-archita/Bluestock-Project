from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import numpy as np

BASE_DIR = Path(__file__).resolve().parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"
VAR_FILE = BASE_DIR / "var_cvar_report.csv"

RISK_MAP = {
    "low": {"low", "moderately low"},
    "moderate": {"moderate", "moderately high"},
    "high": {"high", "aggressive", "moderately high"},
}


def load_data() -> pd.DataFrame:
    var = pd.read_csv(VAR_FILE)
    funds = pd.read_csv(PROCESSED_DIR / "fund_master_cleaned.csv")
    nav = pd.read_csv(PROCESSED_DIR / "nav_history_cleaned.csv")
    nav["date"] = pd.to_datetime(nav["date"], errors="coerce")
    nav["nav"] = pd.to_numeric(nav["nav"], errors="coerce")
    nav = nav.dropna(subset=["amfi_code", "date", "nav"]).sort_values(["amfi_code", "date"])
    nav["daily_return"] = nav.groupby("amfi_code")["nav"].pct_change()
    sharpe = (
        nav.groupby("amfi_code")["daily_return"]
        .apply(lambda series: (series.mean() / series.std(ddof=1)) * np.sqrt(252) if series.dropna().shape[0] > 1 and series.std(ddof=1) not in (0, None) else np.nan)
        .rename("sharpe_ratio")
        .reset_index()
    )
    merged = funds.merge(var, on="amfi_code", how="inner").merge(sharpe, on="amfi_code", how="left")
    return merged


def recommend(risk_appetite: str, top_n: int = 3) -> pd.DataFrame:
    merged = load_data()
    allowed = RISK_MAP.get(risk_appetite.lower(), RISK_MAP["moderate"])
    mask = merged["risk_grade"].fillna("").str.lower().apply(lambda value: any(option in value for option in allowed))
    candidates = merged[mask].copy()
    if candidates.empty:
        candidates = merged.copy()
    candidates = candidates.sort_values(["sharpe_ratio", "historical_var_95_pct", "cvar_95_pct"], ascending=[False, True, True])
    return candidates[["amfi_code", "scheme_name", "risk_grade", "sharpe_ratio", "historical_var_95_pct", "cvar_95_pct"]].head(top_n)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Simple fund recommender by risk appetite")
    parser.add_argument("risk_appetite", nargs="?", default="Moderate", choices=["Low", "Moderate", "High"], help="Investor risk appetite")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    table = recommend(args.risk_appetite)
    print(f"Top recommendations for {args.risk_appetite} risk appetite:\n")
    print(table.to_string(index=False, justify="left", float_format=lambda value: f"{value:.4f}"))


if __name__ == "__main__":
    main()
