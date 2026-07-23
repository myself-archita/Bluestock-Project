from __future__ import annotations

import pandas as pd


def compute_cashflow_kpis(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["fcf"] = out["cfo"] - out["capex"]
    out["cfo_quality_score"] = out.apply(lambda r: None if r["pat"] == 0 else r["cfo"] / r["pat"], axis=1)
    out["capex_intensity"] = out.apply(lambda r: None if r["sales"] == 0 else r["capex"] / r["sales"], axis=1)
    out["fcf_conversion"] = out.apply(lambda r: None if r["cfo"] == 0 else r["fcf"] / r["cfo"], axis=1)
    out["capital_allocation_class"] = pd.cut(
        out["fcf"],
        bins=[float("-inf"), 0, 1, 10, float("inf")],
        labels=["distress", "tight", "balanced", "cash-rich"],
    ).astype(str)
    return out
