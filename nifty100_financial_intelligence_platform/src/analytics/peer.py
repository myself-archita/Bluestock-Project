from __future__ import annotations

import pandas as pd


def compute_peer_percentiles(df: pd.DataFrame, group_col: str = "peer_group", metric_cols: list[str] | None = None) -> pd.DataFrame:
    metric_cols = metric_cols or [c for c in df.columns if c not in {group_col, "ticker"}]
    rows = []
    for group, gdf in df.groupby(group_col):
        for metric in metric_cols:
            ordered = gdf[["ticker", metric]].dropna().sort_values(metric)
            if ordered.empty:
                continue
            ordered["percentile"] = ordered[metric].rank(pct=True)
            rows.extend(
                {"ticker": row.ticker, "peer_group": group, "metric": metric, "percentile": row.percentile}
                for row in ordered.itertuples()
            )
    return pd.DataFrame(rows)
