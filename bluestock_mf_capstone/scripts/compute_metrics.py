from __future__ import annotations

"""Compute core mutual fund performance metrics from cleaned NAV data."""

import argparse
import json
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parents[1]
PROCESSED_DIR = REPO_ROOT / "data" / "processed"
REPORTS_DIR = REPO_ROOT / "reports"
OUTPUT_DIR = REPO_ROOT / "data" / "processed"


def ensure_directories() -> None:
    for folder in (PROCESSED_DIR, REPORTS_DIR):
        folder.mkdir(parents=True, exist_ok=True)


def read_csv_file(csv_path: Path) -> pd.DataFrame:
    for encoding in ("utf-8-sig", "utf-8", "latin1"):
        try:
            return pd.read_csv(csv_path, encoding=encoding)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(csv_path, encoding="cp1252")


def load_nav_data(input_dir: Path) -> pd.DataFrame:
    candidates = sorted(input_dir.glob("*nav*cleaned.csv"))
    if not candidates:
        candidates = sorted(input_dir.glob("nav_history_cleaned.csv"))
    if not candidates:
        raise FileNotFoundError(f"No cleaned NAV CSV found in {input_dir}")

    frame = read_csv_file(candidates[0]).copy()
    frame.columns = [str(column).strip().lower() for column in frame.columns]
    required = {"amfi_code", "date", "nav"}
    if not required.issubset(frame.columns):
        raise ValueError(f"NAV file must contain columns: {sorted(required)}")
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["nav"] = pd.to_numeric(frame["nav"], errors="coerce")
    frame = frame.dropna(subset=["amfi_code", "date", "nav"])
    frame = frame.sort_values(["amfi_code", "date"])
    return frame


def load_aum_data(input_dir: Path) -> pd.DataFrame | None:
    candidates = sorted(input_dir.glob("*aum*cleaned.csv"))
    if not candidates:
        return None
    frame = read_csv_file(candidates[0]).copy()
    frame.columns = [str(column).strip().lower() for column in frame.columns]
    if {"amfi_code", "date", "aum"}.issubset(frame.columns):
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
        frame["aum"] = pd.to_numeric(frame["aum"], errors="coerce")
        return frame.dropna(subset=["amfi_code", "date", "aum"])
    return None


def annualised_return(series: pd.Series) -> float:
    start = series.iloc[0]
    end = series.iloc[-1]
    periods = max(len(series) - 1, 1)
    return float((end / start) ** (252 / periods) - 1)


def annualised_volatility(returns: pd.Series) -> float:
    return float(returns.std(ddof=1) * (252 ** 0.5))


def max_drawdown(nav: pd.Series) -> float:
    running_peak = nav.cummax()
    drawdown = nav / running_peak - 1
    return float(drawdown.min())


def calc_beta(asset_returns: pd.Series, benchmark_returns: pd.Series) -> float:
    aligned = pd.concat([asset_returns, benchmark_returns], axis=1).dropna()
    if aligned.shape[0] < 2:
        return float("nan")
    asset = aligned.iloc[:, 0]
    benchmark = aligned.iloc[:, 1]
    variance = benchmark.var(ddof=1)
    if variance == 0 or pd.isna(variance):
        return float("nan")
    covariance = asset.cov(benchmark)
    return float(covariance / variance)


def calc_var(returns: pd.Series, confidence: float = 0.95) -> tuple[float, float]:
    if returns.empty:
        return float("nan"), float("nan")
    percentile = 1 - confidence
    historical = float(-returns.quantile(percentile))
    mean = returns.mean()
    std = returns.std(ddof=1)
    if pd.isna(std) or std == 0:
        parametric = float("nan")
    else:
        z_score = 1.6448536269514722 if confidence == 0.95 else 2.3263478740408408
        parametric = float(-(mean - z_score * std))
    return historical, parametric


def compute_metrics(nav: pd.DataFrame, benchmark_code: str | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    benchmark_code = benchmark_code or nav["amfi_code"].iloc[0]
    benchmark = nav[nav["amfi_code"] == benchmark_code].copy()
    benchmark = benchmark.sort_values("date")
    benchmark["daily_return"] = benchmark.groupby("amfi_code")["nav"].pct_change()
    benchmark_returns = benchmark.set_index("date")["daily_return"]

    rows = []
    for amfi_code, group in nav.groupby("amfi_code", sort=False):
        ordered = group.sort_values("date").copy()
        ordered["daily_return"] = ordered["nav"].pct_change()
        returns = ordered["daily_return"].dropna()
        if ordered.empty or ordered["nav"].dropna().empty:
            continue

        cagr = annualised_return(ordered["nav"]) if len(ordered) > 1 else float("nan")
        volatility = annualised_volatility(returns) if not returns.empty else float("nan")
        sharpe = float((returns.mean() / returns.std(ddof=1)) * (252 ** 0.5)) if len(returns) > 1 and returns.std(ddof=1) not in (0, None) else float("nan")
        beta = calc_beta(returns, benchmark_returns) if amfi_code != benchmark_code else 1.0
        hist_var_95, param_var_95 = calc_var(returns, 0.95)
        hist_var_99, param_var_99 = calc_var(returns, 0.99)
        drawdown = max_drawdown(ordered["nav"])

        rows.append(
            {
                "amfi_code": amfi_code,
                "observations": int(len(ordered)),
                "start_date": ordered["date"].min().date().isoformat(),
                "end_date": ordered["date"].max().date().isoformat(),
                "cagr_pct": round(cagr * 100, 4) if pd.notna(cagr) else pd.NA,
                "annualised_volatility_pct": round(volatility * 100, 4) if pd.notna(volatility) else pd.NA,
                "sharpe_ratio": round(sharpe, 4) if pd.notna(sharpe) else pd.NA,
                "beta_vs_benchmark": round(beta, 4) if pd.notna(beta) else pd.NA,
                "max_drawdown_pct": round(drawdown * 100, 4) if pd.notna(drawdown) else pd.NA,
                "historical_var_95_pct": round(hist_var_95 * 100, 4) if pd.notna(hist_var_95) else pd.NA,
                "parametric_var_95_pct": round(param_var_95 * 100, 4) if pd.notna(param_var_95) else pd.NA,
                "historical_var_99_pct": round(hist_var_99 * 100, 4) if pd.notna(hist_var_99) else pd.NA,
                "parametric_var_99_pct": round(param_var_99 * 100, 4) if pd.notna(param_var_99) else pd.NA,
            }
        )

    metrics = pd.DataFrame(rows).sort_values(["sharpe_ratio", "cagr_pct"], ascending=[False, False])
    if not metrics.empty:
        metrics["sharpe_rank"] = range(1, len(metrics) + 1)
    return metrics, benchmark[["date", "amfi_code", "daily_return"]]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compute mutual fund performance metrics from cleaned NAV data.")
    parser.add_argument("--input-dir", type=Path, default=PROCESSED_DIR, help="Directory with cleaned CSV outputs.")
    parser.add_argument("--benchmark-code", type=str, default=None, help="AMFI code to use as beta benchmark.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    ensure_directories()

    nav = load_nav_data(args.input_dir)
    aum = load_aum_data(args.input_dir)
    metrics, benchmark_returns = compute_metrics(nav, args.benchmark_code)

    metrics_path = OUTPUT_DIR / "performance_metrics.csv"
    metrics.to_csv(metrics_path, index=False)

    benchmark_returns_path = OUTPUT_DIR / "benchmark_returns.csv"
    benchmark_returns.to_csv(benchmark_returns_path, index=False)

    summary = {
        "benchmark_code": args.benchmark_code or nav["amfi_code"].iloc[0],
        "funds_processed": int(metrics.shape[0]),
        "metrics_output": str(metrics_path),
        "benchmark_returns_output": str(benchmark_returns_path),
    }

    if aum is not None and not aum.empty:
        aum_summary = (
            aum.groupby("amfi_code", as_index=False)["aum"]
            .max()
            .rename(columns={"aum": "max_aum"})
            .sort_values("max_aum", ascending=False)
        )
        aum_summary.to_csv(OUTPUT_DIR / "aum_summary.csv", index=False)
        summary["aum_output"] = str(OUTPUT_DIR / "aum_summary.csv")

    (REPORTS_DIR / "performance_metrics_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
