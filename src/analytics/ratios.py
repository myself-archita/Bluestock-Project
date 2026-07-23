from __future__ import annotations

import pandas as pd


def safe_div(numerator, denominator):
    if denominator in (0, None) or pd.isna(denominator):
        return None
    if pd.isna(numerator):
        return None
    return numerator / denominator


def compute_profitability_ratios(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["npm"] = out.apply(lambda r: safe_div(r["pat"], r["sales"]), axis=1)
    out["opm"] = out.apply(lambda r: safe_div(r["operating_profit"], r["sales"]), axis=1)
    out["roe"] = out.apply(lambda r: None if r["equity"] in (0, None) or r["equity"] is None else safe_div(r["pat"], r["equity"]), axis=1)
    out["roce"] = out.apply(lambda r: safe_div(r["operating_profit"], r["equity"] + r["debt"]), axis=1)
    return out


def compute_leverage_ratios(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["debt_equity"] = out.apply(lambda r: None if r.get("is_bank") else safe_div(r["debt"], r["equity"]), axis=1)
    out["interest_coverage"] = out.apply(lambda r: None if r.get("debt") in (0, None) else safe_div(r["operating_profit"], r["debt"] * 0.08), axis=1)
    out["asset_turnover"] = out.apply(lambda r: safe_div(r["sales"], r["assets"]), axis=1)
    return out
