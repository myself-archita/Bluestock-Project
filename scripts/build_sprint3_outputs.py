from __future__ import annotations

from pathlib import Path
import sqlite3
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from src.config import DB_PATH, REPORTS_DIR
from src.screener.engine import build_preset_screeners, build_universe, compute_composite_quality_score, load_config
from src.analytics.peer import build_peer_percentiles, build_peer_groups, export_peer_comparison, radar_chart_path


def load_data() -> pd.DataFrame:
    with sqlite3.connect(DB_PATH) as conn:
        companies = pd.read_sql_query("SELECT * FROM companies", conn)
        financials = pd.read_sql_query("SELECT * FROM financials", conn)
        ratios = pd.read_sql_query("SELECT * FROM financial_ratios", conn)
    latest = financials.sort_values("year").groupby("ticker", as_index=False).tail(1)
    latest_ratios = ratios.sort_values("year").groupby("ticker", as_index=False).tail(1)
    df = latest.merge(latest_ratios, on=["ticker", "year"], how="left").merge(companies, on="ticker", how="left")
    return build_universe(df)


def write_screener_workbook(df: pd.DataFrame, config: dict) -> None:
    screeners = build_preset_screeners(df, config)
    output = BASE / "output" / "screener_output.xlsx"
    output.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for name, sheet in screeners.items():
            cols = [c for c in sheet.columns if c != "peer_group"]
            sheet[cols].to_excel(writer, sheet_name=name[:31], index=False)


def write_radar_chart(row: pd.Series, peer_df: pd.DataFrame) -> None:
    metrics = ["roe", "roce", "npm", "debt_equity", "fcf", "pat_cagr_5y", "revenue_cagr_5y", "composite_quality_score"]
    available = [m for m in metrics if m in row.index]
    if not available:
        return
    values = [float(row.get(m, 0) or 0) for m in available]
    peer_avgs = [float(peer_df[m].mean()) if m in peer_df.columns else 0 for m in available]
    angles = np.linspace(0, 2 * np.pi, len(available), endpoint=False).tolist()
    values += values[:1]
    peer_avgs += peer_avgs[:1]
    angles += angles[:1]
    fig = plt.figure(figsize=(9, 9))
    ax = plt.subplot(111, polar=True)
    ax.plot(angles, values, linewidth=2, label=row["ticker"])
    ax.fill(angles, values, alpha=0.25)
    ax.plot(angles, peer_avgs, linewidth=2, linestyle="--", label="Peer average")
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(available)
    ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.1))
    fig.tight_layout()
    fig.savefig(radar_chart_path(row["ticker"]), dpi=160)
    plt.close(fig)


def build_reports(df: pd.DataFrame) -> None:
    enriched = df.copy()
    enriched["composite_quality_score"] = compute_composite_quality_score(enriched)
    percentiles = build_peer_percentiles(DB_PATH)
    peer_groups = build_peer_groups(enriched[["ticker", "company_name", "sector", "industry", "composite_quality_score", "roe", "roce", "npm", "debt_equity", "fcf", "pat_cagr_5y", "revenue_cagr_5y", "eps_cagr_5y", "interest_coverage", "asset_turnover"]].copy())
    export_peer_comparison(peer_groups, percentiles, BASE / "output" / "peer_comparison.xlsx")
    for group, group_df in peer_groups.groupby("peer_group"):
        for _, row in group_df.iterrows():
            write_radar_chart(row, group_df)


def main() -> None:
    config = load_config(BASE / "screener_config.yaml")
    df = load_data()
    write_screener_workbook(df, config)
    build_reports(df)


if __name__ == "__main__":
    main()
