from __future__ import annotations

from pathlib import Path
import yaml
import pandas as pd


def load_config(path: str | Path) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def apply_filters(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    query_parts = []
    for column, rule in config.get("filters", {}).items():
        if "min" in rule:
            query_parts.append(f"`{column}` >= {rule['min']}")
        if "max" in rule:
            query_parts.append(f"`{column}` <= {rule['max']}")
    if query_parts:
        df = df.query(" and ".join(query_parts))
    return df


def score_companies(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    out = df.copy()
    weights = config.get("weights", {"valuation": 0.5, "quality": 0.3, "momentum": 0.2})
    out["score"] = 0.0
    for metric, weight in weights.items():
        if metric in out.columns:
            col = out[metric].rank(pct=True)
            out["score"] += col * weight
    return out.sort_values("score", ascending=False)
