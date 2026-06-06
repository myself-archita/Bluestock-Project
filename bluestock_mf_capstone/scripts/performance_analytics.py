from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import linregress


BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parents[1]
DATA_RAW_DIR = REPO_ROOT / "data" / "raw"
DATA_PROCESSED_DIR = REPO_ROOT / "data" / "processed"
OUTPUT_DIR = REPO_ROOT

RF_ANNUAL = 0.065
TRADING_DAYS = 252


def ensure_directories() -> None:
    DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def read_csv_file(csv_path: Path) -> pd.DataFrame:
    for encoding in ("utf-8-sig", "utf-8", "latin1"):
        try:
            return pd.read_csv(csv_path, encoding=encoding)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(csv_path, encoding="cp1252")


def find_latest_csv(patterns: list[str]) -> Path:
    candidates: list[Path] = []
    for pattern in patterns:
        candidates.extend(DATA_PROCESSED_DIR.glob(pattern))
        candidates.extend(DATA_RAW_DIR.glob(pattern))
    candidates = [path for path in candidates if path.is_file()]
    if not candidates:
        raise FileNotFoundError("No suitable CSV found in data/raw or data/processed.")
    return sorted(candidates, key=lambda path: path.stat().st_mtime, reverse=True)[0]


def load_nav_frame() -> pd.DataFrame:
    nav_path = find_latest_csv(["*nav*cleaned.csv", "*nav*snapshot*.csv", "nav_history_cleaned.csv", "live_nav_snapshot.csv"])
    frame = read_csv_file(nav_path).copy()
    frame.columns = [str(column).strip().lower() for column in frame.columns]
    required = {"amfi_code", "date", "nav"}
    if not required.issubset(frame.columns):
        raise ValueError(f"{nav_path.name} must include columns {sorted(required)}")
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["nav"] = pd.to_numeric(frame["nav"], errors="coerce")
    frame = frame.dropna(subset=["amfi_code", "date", "nav"]).sort_values(["amfi_code", "date"])
    return frame


def load_performance_frame() -> pd.DataFrame | None:
    candidates = [
        DATA_PROCESSED_DIR / "scheme_performance_cleaned.csv",
        DATA_PROCESSED_DIR / "performance_metrics.csv",
    ]
    for path in candidates:
        if path.exists():
            frame = read_csv_file(path).copy()
            frame.columns = [str(column).strip().lower() for column in frame.columns]
            return frame
    return None


def load_metadata() -> pd.DataFrame | None:
    candidates = [
        DATA_PROCESSED_DIR / "scheme_master_cleaned.csv",
        DATA_PROCESSED_DIR / "fund_master_cleaned.csv",
    ]
    for path in candidates:
        if path.exists():
            frame = read_csv_file(path).copy()
            frame.columns = [str(column).strip().lower() for column in frame.columns]
            return frame
    return None


def compute_daily_returns(nav: pd.DataFrame) -> pd.DataFrame:
    frame = nav.sort_values(["amfi_code", "date"]).copy()
    frame["daily_return"] = frame.groupby("amfi_code")["nav"].pct_change()
    return frame


def year_window(nav: pd.DataFrame, years: int) -> pd.DataFrame:
    max_date = nav["date"].max()
    min_date = max_date - pd.DateOffset(years=years)
    frame = nav[nav["date"] >= min_date].copy()
    return frame


def compute_cagr(nav: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for amfi_code, group in nav.groupby("amfi_code", sort=False):
        group = group.sort_values("date")
        for label, years in (("1yr", 1), ("3yr", 3), ("5yr", 5)):
            window = group[group["date"] >= (group["date"].max() - pd.DateOffset(years=years))].copy()
            window = window.dropna(subset=["nav"])
            if window.empty or len(window) < 2:
                cagr = np.nan
            else:
                start_nav = float(window["nav"].iloc[0])
                end_nav = float(window["nav"].iloc[-1])
                periods = max((window["date"].iloc[-1] - window["date"].iloc[0]).days / 365.25, 1 / TRADING_DAYS)
                cagr = (end_nav / start_nav) ** (1 / periods) - 1
            rows.append({"amfi_code": amfi_code, "horizon": label, "cagr_pct": round(cagr * 100, 4) if pd.notna(cagr) else np.nan})
    return pd.DataFrame(rows)


def downside_std(returns: pd.Series) -> float:
    downside = returns[returns < 0]
    if downside.empty:
        return float("nan")
    return float(downside.std(ddof=1))


def max_drawdown_series(nav: pd.Series) -> tuple[float, pd.Timestamp | None, pd.Timestamp | None]:
    running_max = nav.cummax()
    drawdown = nav / running_max - 1
    end_idx = drawdown.idxmin()
    worst_dd = float(drawdown.min())
    if pd.isna(end_idx):
        return float("nan"), None, None
    start_idx = nav.loc[:end_idx].idxmax()
    return worst_dd, start_idx, end_idx


def load_benchmark_series(nav: pd.DataFrame) -> pd.DataFrame:
    bench = nav[nav["amfi_code"].astype(str).str.contains("nifty|benchmark", case=False, na=False)].copy()
    if bench.empty:
        bench = nav[nav["amfi_code"] == nav["amfi_code"].iloc[0]].copy()
    bench["benchmark_return"] = bench["nav"].pct_change()
    return bench[["date", "benchmark_return"]]


def load_benchmark_frame() -> pd.DataFrame:
    candidates = [
        DATA_PROCESSED_DIR / "benchmark_nav_cleaned.csv",
        DATA_RAW_DIR / "benchmark_nav_snapshot.csv",
    ]
    for path in candidates:
        if path.exists():
            frame = read_csv_file(path).copy()
            frame.columns = [str(column).strip().lower() for column in frame.columns]
            required = {"benchmark_code", "date", "nav"}
            if not required.issubset(frame.columns):
                continue
            frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
            frame["nav"] = pd.to_numeric(frame["nav"], errors="coerce")
            return frame.dropna(subset=["benchmark_code", "date", "nav"]).sort_values(["benchmark_code", "date"])
    raise FileNotFoundError("benchmark_nav_cleaned.csv or benchmark_nav_snapshot.csv not found.")


def compute_scorecard(nav: pd.DataFrame, performance: pd.DataFrame | None) -> pd.DataFrame:
    latest = nav.sort_values("date").groupby("amfi_code", as_index=False).tail(1).copy()
    cagr_table = compute_cagr(nav)
    cagr_3yr = cagr_table[cagr_table["horizon"] == "3yr"].rename(columns={"cagr_pct": "cagr_3yr_pct"})
    daily = compute_daily_returns(nav)

    rows = []
    for amfi_code, group in daily.groupby("amfi_code", sort=False):
        returns = group["daily_return"].dropna()
        nav_series = group["nav"]
        if returns.empty:
            continue
        sharpe = ((returns.mean() - RF_ANNUAL / TRADING_DAYS) / returns.std(ddof=1)) * np.sqrt(TRADING_DAYS) if returns.std(ddof=1) else np.nan
        downside = downside_std(returns)
        sortino = ((returns.mean() - RF_ANNUAL / TRADING_DAYS) / downside) * np.sqrt(TRADING_DAYS) if downside and pd.notna(downside) and downside != 0 else np.nan
        if performance is not None:
            perf_rows = performance[performance["amfi_code"].astype(str) == str(amfi_code)]
            expense_ratio = pd.to_numeric(perf_rows.get("expense_ratio"), errors="coerce").dropna().mean() if "expense_ratio" in perf_rows.columns else np.nan
        else:
            expense_ratio = np.nan
        worst_dd, dd_start, dd_end = max_drawdown_series(nav_series.reset_index(drop=True))
        rows.append(
            {
                "amfi_code": amfi_code,
                "sharpe_ratio": sharpe,
                "sortino_ratio": sortino,
                "max_drawdown_pct": worst_dd * 100 if pd.notna(worst_dd) else np.nan,
                "dd_start": dd_start.date().isoformat() if dd_start is not None else None,
                "dd_end": dd_end.date().isoformat() if dd_end is not None else None,
                "expense_ratio": expense_ratio,
            }
        )

    scorecard = pd.DataFrame(rows)
    scorecard = scorecard.merge(cagr_3yr, on="amfi_code", how="left")

    def rank_inverse(series: pd.Series) -> pd.Series:
        return series.rank(ascending=True, method="min")

    scorecard["rank_3yr_return"] = scorecard["cagr_3yr_pct"].rank(ascending=False, method="min")
    scorecard["rank_sharpe"] = scorecard["sharpe_ratio"].rank(ascending=False, method="min")
    scorecard["rank_alpha"] = scorecard.get("alpha_annualised", pd.Series(np.nan, index=scorecard.index)).rank(ascending=False, method="min")
    scorecard["rank_expense"] = rank_inverse(scorecard["expense_ratio"])
    scorecard["rank_drawdown"] = rank_inverse(scorecard["max_drawdown_pct"].abs())

    max_rank = max(scorecard["rank_3yr_return"].max(), 1)
    scorecard["fund_score"] = (
        30 * (1 - (scorecard["rank_3yr_return"] - 1) / max_rank)
        + 25 * (1 - (scorecard["rank_sharpe"] - 1) / max_rank)
        + 20 * (1 - (scorecard["rank_alpha"] - 1) / max_rank)
        + 15 * (1 - (scorecard["rank_expense"] - 1) / max_rank)
        + 10 * (1 - (scorecard["rank_drawdown"] - 1) / max_rank)
    )
    return scorecard.sort_values("fund_score", ascending=False)


def compute_alpha_beta(nav: pd.DataFrame, benchmarks: pd.DataFrame) -> pd.DataFrame:
    rows = []
    bench_returns_map = {}
    for benchmark_code, benchmark_group in benchmarks.groupby("benchmark_code", sort=False):
        benchmark_group = benchmark_group.sort_values("date").copy()
        benchmark_group["benchmark_return"] = benchmark_group["nav"].pct_change()
        bench_returns_map[str(benchmark_code)] = benchmark_group.set_index("date")["benchmark_return"]

    for amfi_code, group in nav.groupby("amfi_code", sort=False):
        series = group.sort_values("date").copy()
        series["fund_return"] = series["nav"].pct_change()
        fund_returns = series.set_index("date")["fund_return"]
        for benchmark_code, bench_returns in bench_returns_map.items():
            aligned = pd.concat([fund_returns, bench_returns], axis=1).dropna()
            if aligned.shape[0] < 2:
                continue
            result = linregress(aligned.iloc[:, 1], aligned.iloc[:, 0])
            rows.append(
                {
                    "amfi_code": amfi_code,
                    "benchmark_code": benchmark_code,
                    "alpha_daily": result.intercept,
                    "alpha_annualised": result.intercept * TRADING_DAYS,
                    "beta": result.slope,
                    "r_value": result.rvalue,
                    "p_value": result.pvalue,
                    "std_err": result.stderr,
                }
            )
    return pd.DataFrame(rows)


def plot_top_funds(nav: pd.DataFrame, scorecard: pd.DataFrame, benchmarks: pd.DataFrame, output_path: Path) -> Path:
    top_funds = scorecard.head(5)["amfi_code"].tolist()
    fig, ax = plt.subplots(figsize=(14, 8))
    for code in top_funds:
        series = nav[nav["amfi_code"] == code].sort_values("date").copy()
        series = series.tail(756).copy()
        if series.empty:
            continue
        normalized = series["nav"] / series["nav"].iloc[0] * 100
        ax.plot(series["date"], normalized, label=f"Fund {code}", linewidth=2)

    for benchmark_code, benchmark_group in benchmarks.groupby("benchmark_code", sort=False):
        bench = benchmark_group.sort_values("date").tail(756).copy()
        if bench.empty:
            continue
        normalized = bench["nav"] / bench["nav"].iloc[0] * 100
        benchmark_name = benchmark_group["benchmark_name"].iloc[0] if "benchmark_name" in benchmark_group.columns else benchmark_code
        ax.plot(bench["date"], normalized, linestyle="--", linewidth=2, label=f"{benchmark_name} ({benchmark_code})")

    ax.set_title("Top 5 Funds vs Benchmarks")
    ax.set_xlabel("Date")
    ax.set_ylabel("Indexed NAV (Start = 100)")
    ax.legend(ncol=2, fontsize=9)
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)
    return output_path


def build_notebook_summary(nav: pd.DataFrame, scorecard: pd.DataFrame, alpha_beta: pd.DataFrame) -> dict:
    return {
        "funds": int(nav["amfi_code"].nunique()),
        "rows": int(len(nav)),
        "scorecard_rows": int(len(scorecard)),
        "alpha_beta_rows": int(len(alpha_beta)),
        "date_range": [nav["date"].min().date().isoformat(), nav["date"].max().date().isoformat()],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compute mutual fund performance analytics.")
    parser.add_argument("--benchmark-code", type=str, default=None, help="AMFI code used as benchmark.")
    return parser


def main() -> None:
    ensure_directories()
    nav = load_nav_frame()
    performance = load_performance_frame()
    benchmarks = load_benchmark_frame()
    nav = compute_daily_returns(nav)
    cagr_table = compute_cagr(nav)
    alpha_beta = compute_alpha_beta(nav, benchmarks)
    scorecard = compute_scorecard(nav, performance)

    chart_path = OUTPUT_DIR / "benchmark_comparison.png"
    plot_top_funds(nav, scorecard, benchmarks, chart_path)

    scorecard_path = OUTPUT_DIR / "fund_scorecard.csv"
    alpha_beta_path = OUTPUT_DIR / "alpha_beta.csv"
    cagr_path = OUTPUT_DIR / "cagr_comparison.csv"
    scorecard.to_csv(scorecard_path, index=False)
    alpha_beta.to_csv(alpha_beta_path, index=False)
    cagr_table.to_csv(cagr_path, index=False)

    summary = build_notebook_summary(nav, scorecard, alpha_beta)
    (OUTPUT_DIR / "performance_analytics_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
