from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parents[1]
PROCESSED_DIR = REPO_ROOT / "data" / "processed"
REPORTS_DIR = REPO_ROOT / "reports"


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


def load_metrics(input_dir: Path) -> pd.DataFrame:
    path = input_dir / "performance_metrics.csv"
    if not path.exists():
        raise FileNotFoundError(f"Metrics file not found: {path}")
    frame = read_csv_file(path)
    if "amfi_code" not in frame.columns:
        raise ValueError("performance_metrics.csv must include an amfi_code column")
    return frame


def load_metadata(input_dir: Path) -> pd.DataFrame | None:
    candidates = [input_dir / "scheme_performance_cleaned.csv", input_dir / "nav_history_cleaned.csv"]
    for path in candidates:
        if path.exists():
            frame = read_csv_file(path)
            frame.columns = [str(column).strip().lower() for column in frame.columns]
            return frame
    return None


def score_funds(metrics: pd.DataFrame) -> pd.DataFrame:
    scored = metrics.copy()
    numeric_columns = [
        "cagr_pct",
        "annualised_volatility_pct",
        "sharpe_ratio",
        "beta_vs_benchmark",
        "max_drawdown_pct",
        "historical_var_95_pct",
    ]
    for column in numeric_columns:
        scored[column] = pd.to_numeric(scored[column], errors="coerce")

    scored["return_score"] = scored["cagr_pct"].rank(pct=True, ascending=True)
    scored["risk_score"] = (1 - scored["annualised_volatility_pct"].rank(pct=True, ascending=True)).fillna(0)
    scored["sharpe_score"] = scored["sharpe_ratio"].rank(pct=True, ascending=True)
    scored["beta_score"] = (1 - (scored["beta_vs_benchmark"] - 1).abs().rank(pct=True, ascending=True)).fillna(0)
    scored["drawdown_score"] = (1 - scored["max_drawdown_pct"].abs().rank(pct=True, ascending=True)).fillna(0)
    scored["var_score"] = (1 - scored["historical_var_95_pct"].abs().rank(pct=True, ascending=True)).fillna(0)

    scored["recommendation_score"] = (
        scored["return_score"] * 0.30
        + scored["risk_score"] * 0.20
        + scored["sharpe_score"] * 0.25
        + scored["beta_score"] * 0.10
        + scored["drawdown_score"] * 0.10
        + scored["var_score"] * 0.05
    )
    return scored.sort_values("recommendation_score", ascending=False)


def filter_by_risk_profile(frame: pd.DataFrame, risk_profile: str) -> pd.DataFrame:
    risk_profile = risk_profile.lower()
    if risk_profile == "conservative":
        return frame[frame["annualised_volatility_pct"] <= frame["annualised_volatility_pct"].quantile(0.5)]
    if risk_profile == "balanced":
        return frame[
            (frame["annualised_volatility_pct"] <= frame["annualised_volatility_pct"].quantile(0.75))
            & (frame["beta_vs_benchmark"].between(0.7, 1.3))
        ]
    return frame


def generate_recommendations(metrics: pd.DataFrame, top_n: int, risk_profile: str) -> pd.DataFrame:
    scored = score_funds(metrics)
    filtered = filter_by_risk_profile(scored, risk_profile)
    if filtered.empty:
        filtered = scored
    output = filtered.head(top_n).copy()
    output["recommendation_reason"] = output.apply(
        lambda row: (
            f"Sharpe {row['sharpe_ratio']:.2f}, CAGR {row['cagr_pct']:.2f}%, "
            f"volatility {row['annualised_volatility_pct']:.2f}%"
        ),
        axis=1,
    )
    keep_columns = [
        "amfi_code",
        "recommendation_score",
        "recommendation_reason",
        "cagr_pct",
        "annualised_volatility_pct",
        "sharpe_ratio",
        "beta_vs_benchmark",
        "max_drawdown_pct",
        "historical_var_95_pct",
    ]
    return output[keep_columns]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Rank mutual funds using risk-adjusted performance metrics.")
    parser.add_argument("--input-dir", type=Path, default=PROCESSED_DIR, help="Directory containing performance_metrics.csv.")
    parser.add_argument("--top-n", type=int, default=5, help="Number of funds to recommend.")
    parser.add_argument(
        "--risk-profile",
        choices=["conservative", "balanced", "aggressive"],
        default="balanced",
        help="Preference filter to shape the recommendation list.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    ensure_directories()

    metrics = load_metrics(args.input_dir)
    recommendations = generate_recommendations(metrics, args.top_n, args.risk_profile)
    recommendations_path = args.input_dir / "fund_recommendations.csv"
    recommendations.to_csv(recommendations_path, index=False)

    summary = {
        "input_metrics": str(args.input_dir / "performance_metrics.csv"),
        "recommendations_output": str(recommendations_path),
        "risk_profile": args.risk_profile,
        "top_n": args.top_n,
        "recommended_funds": recommendations["amfi_code"].tolist(),
    }
    (REPORTS_DIR / "fund_recommendations_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
