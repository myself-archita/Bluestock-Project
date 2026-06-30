from __future__ import annotations

import pandas as pd


def cagr(start, end, periods):
    if start in (0, None) or pd.isna(start) or pd.isna(end) or periods <= 0:
        return None
    return (end / start) ** (1 / periods) - 1


def compute_cagr_table(df: pd.DataFrame, value_col: str, group_col: str = "ticker") -> pd.DataFrame:
    rows = []
    for ticker, group in df.sort_values("year").groupby(group_col):
        values = group.set_index("year")[value_col]
        years = list(values.index)
        if len(years) < 2:
            continue
        start, end = values.iloc[0], values.iloc[-1]
        rows.append({"ticker": ticker, f"{value_col}_cagr": cagr(start, end, len(years) - 1)})
    return pd.DataFrame(rows)
