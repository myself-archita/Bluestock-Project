from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml


DEFAULT_PRESETS: dict[str, dict[str, dict[str, float]]] = {
    "Quality Compounder": {
        "roe": {"min": 0.15},
        "debt_equity": {"max": 1.0},
        "fcf": {"min": 0.0},
        "revenue_cagr_5y": {"min": 0.10},
    },
    "Value Pick": {
        "pe": {"max": 20.0},
        "pb": {"max": 3.0},
        "debt_equity": {"max": 2.0},
        "dividend_yield": {"min": 0.01},
    },
    "Growth Accelerator": {
        "pat_cagr_5y": {"min": 0.20},
        "revenue_cagr_5y": {"min": 0.15},
        "debt_equity": {"max": 2.0},
    },
    "Dividend Champion": {
        "dividend_yield": {"min": 0.02},
        "dividend_payout": {"max": 0.80},
        "fcf": {"min": 0.0},
    },
    "Debt-Free Blue Chip": {
        "debt_equity": {"max": 0.0},
        "roe": {"min": 0.12},
        "sales": {"min": 5000.0},
    },
    "Turnaround Watch": {
        "revenue_cagr_3y": {"min": 0.10},
        "fcf": {"min": 0.0},
        "debt_equity_declining": {"min": 1.0},
    },
}


METRIC_ALIASES = {
    "roe": "roe",
    "debt_equity": "debt_equity",
    "debt/equity": "debt_equity",
    "fcf": "fcf",
    "revenue_cagr_5yr": "revenue_cagr_5y",
    "revenue_cagr_5y": "revenue_cagr_5y",
    "pat_cagr_5yr": "pat_cagr_5y",
    "pat_cagr_5y": "pat_cagr_5y",
    "opm": "opm",
    "pe": "pe",
    "p/e": "pe",
    "pb": "pb",
    "p/b": "pb",
    "dividend_yield": "dividend_yield",
    "icr": "interest_coverage",
    "interest_coverage": "interest_coverage",
    "market_cap": "market_cap",
    "net_profit": "net_profit",
    "eps_cagr": "eps_cagr_5y",
    "eps_cagr_5y": "eps_cagr_5y",
    "asset_turnover": "asset_turnover",
    "sales": "sales",
    "revenue": "sales",
}


def load_config(path: str | Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _winsorize(series: pd.Series, lower: float = 0.10, upper: float = 0.90) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce")
    if s.dropna().empty:
        return s
    lo = s.quantile(lower)
    hi = s.quantile(upper)
    return s.clip(lower=lo, upper=hi)


def _scale_0_100(series: pd.Series) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce")
    if s.dropna().empty:
        return pd.Series(np.nan, index=series.index)
    lo = s.min()
    hi = s.max()
    if pd.isna(lo) or pd.isna(hi) or hi == lo:
        return pd.Series(50.0, index=series.index)
    return (s - lo) / (hi - lo) * 100.0


def _safe_div(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    denominator = denominator.replace({0: np.nan})
    return numerator / denominator


def enrich_metrics(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if {"pat", "sales"}.issubset(out.columns):
        out["npm"] = _safe_div(out["pat"], out["sales"])
    if {"operating_profit", "sales"}.issubset(out.columns):
        out["opm"] = _safe_div(out["operating_profit"], out["sales"])
    if {"pat", "equity"}.issubset(out.columns):
        out["roe"] = _safe_div(out["pat"], out["equity"])
    if {"operating_profit", "equity", "debt"}.issubset(out.columns):
        out["roce"] = _safe_div(out["operating_profit"], (out["equity"] + out["debt"]).replace({0: np.nan}))
    if {"debt", "equity"}.issubset(out.columns):
        out["debt_equity"] = _safe_div(out["debt"], out["equity"])
    if {"operating_profit", "debt"}.issubset(out.columns):
        out["interest_coverage"] = _safe_div(out["operating_profit"], out["debt"] * 0.08)
    if {"sales", "assets"}.issubset(out.columns):
        out["asset_turnover"] = _safe_div(out["sales"], out["assets"])
    if {"cfo", "capex"}.issubset(out.columns):
        out["fcf"] = out["cfo"] - out["capex"]
    if {"cfo", "pat"}.issubset(out.columns):
        out["cfo_pat_ratio"] = _safe_div(out["cfo"], out["pat"])
    if {"cfo", "fcf"}.issubset(out.columns):
        out["fcf_conversion"] = _safe_div(out["fcf"], out["cfo"])
    if {"sales", "operating_profit"}.issubset(out.columns):
        out["profit_margin"] = _safe_div(out["operating_profit"], out["sales"])
    if "year" in out.columns and {"ticker", "debt_equity"}.issubset(out.columns):
        out["debt_equity_declining"] = out.sort_values(["ticker", "year"]).groupby("ticker")["debt_equity"].diff(-1) * -1
    return out


def build_universe(df: pd.DataFrame) -> pd.DataFrame:
    out = enrich_metrics(df)
    if "ticker" not in out.columns and "company_id" in out.columns:
        out = out.rename(columns={"company_id": "ticker"})
    if "company_name" not in out.columns and "name" in out.columns:
        out = out.rename(columns={"name": "company_name"})
    return out


def _resolve_metric_frame(df: pd.DataFrame, metric: str) -> pd.Series:
    metric = METRIC_ALIASES.get(metric.lower(), metric.lower())
    if metric not in df.columns:
        return pd.Series(np.nan, index=df.index)
    return pd.to_numeric(df[metric], errors="coerce")


def apply_filters(df: pd.DataFrame, config: dict[str, Any] | None = None, *, preset_name: str | None = None) -> pd.DataFrame:
    config = config or {}
    metrics = build_universe(df)
    filters = dict(config.get("filters", {}))
    if preset_name and preset_name in DEFAULT_PRESETS:
        filters = {**DEFAULT_PRESETS[preset_name], **filters}

    mask = pd.Series(True, index=metrics.index)
    for metric_name, rule in filters.items():
        metric = METRIC_ALIASES.get(metric_name.lower(), metric_name.lower())
        if metric == "debt_equity" and "sector" in metrics.columns:
            financials_mask = metrics["sector"].astype(str).str.contains("Financial", case=False, na=False)
            if "max" in rule:
                mask &= financials_mask | (_resolve_metric_frame(metrics, metric) <= rule["max"])
                continue
        series = _resolve_metric_frame(metrics, metric)
        if metric == "interest_coverage":
            debt_free = metrics.get("capital_allocation_class", pd.Series("", index=metrics.index)).astype(str).str.contains("debt free", case=False, na=False)
            series = series.where(~debt_free, np.inf)
        if "min" in rule:
            mask &= series >= rule["min"]
        if "max" in rule:
            mask &= series <= rule["max"]
        if "eq" in rule:
            mask &= series == rule["eq"]

    out = metrics.loc[mask].copy()
    out["composite_quality_score"] = compute_composite_quality_score(out)
    sort_cols = [c for c in ["composite_quality_score", "roe", "roce", "fcf"] if c in out.columns]
    if sort_cols:
        out = out.sort_values(sort_cols, ascending=[False] * len(sort_cols))
    return out.reset_index(drop=True)


def compute_composite_quality_score(df: pd.DataFrame, sector_relative: bool = True) -> pd.Series:
    metrics = df.copy()
    components = {
        "profitability": ["roe", "roce", "npm"],
        "cash_quality": ["fcf", "cfo_pat_ratio", "fcf_conversion"],
        "growth": ["revenue_cagr_5y", "pat_cagr_5y", "eps_cagr_5y"],
        "leverage": ["debt_equity", "interest_coverage"],
    }
    weights = {"profitability": 0.35, "cash_quality": 0.30, "growth": 0.20, "leverage": 0.15}

    score = pd.Series(0.0, index=metrics.index)
    for component, columns in components.items():
        present = [c for c in columns if c in metrics.columns]
        if not present:
            continue
        chunk = pd.DataFrame({c: _scale_0_100(_winsorize(metrics[c])) for c in present})
        if component == "leverage":
            if "debt_equity" in chunk:
                chunk["debt_equity"] = 100 - chunk["debt_equity"]
        component_score = chunk.mean(axis=1, skipna=True)
        score += component_score.fillna(0) * weights[component]

    score = score.clip(0, 100)
    if sector_relative and "sector" in metrics.columns:
        relative = score.copy()
        for sector, idx in metrics.groupby("sector").groups.items():
            sector_score = score.loc[idx]
            scaled = _scale_0_100(_winsorize(sector_score))
            relative.loc[idx] = scaled
        score = relative
    return score.round(2)


def build_preset_screeners(df: pd.DataFrame, config: dict[str, Any] | None = None) -> dict[str, pd.DataFrame]:
    config = config or {}
    screeners = {}
    for name in DEFAULT_PRESETS:
        merged = {"filters": {**DEFAULT_PRESETS[name], **config.get("presets", {}).get(name, {})}}
        screeners[name] = apply_filters(df, merged, preset_name=name)
    return screeners


def normalize_percentile_ranks(df: pd.DataFrame, metric_cols: list[str]) -> pd.DataFrame:
    out = df.copy()
    for col in metric_cols:
        if col not in out.columns:
            continue
        series = pd.to_numeric(out[col], errors="coerce")
        out[f"{col}_percentile"] = series.rank(pct=True, method="average")
    return out
