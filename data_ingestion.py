from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
REPORTS_DIR = BASE_DIR / "reports"


def ensure_directories() -> None:
    for folder in (RAW_DIR, PROCESSED_DIR, REPORTS_DIR):
        folder.mkdir(parents=True, exist_ok=True)


def read_csv_file(csv_path: Path) -> pd.DataFrame:
    for encoding in ("utf-8-sig", "utf-8", "latin1"):
        try:
            return pd.read_csv(csv_path, encoding=encoding)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(csv_path, encoding="cp1252")


def detect_column(frame: pd.DataFrame, keywords: Iterable[str]) -> str | None:
    keyword_list = [keyword.lower() for keyword in keywords]
    for column in frame.columns:
        lower = str(column).lower()
        if all(keyword in lower for keyword in keyword_list):
            return column
    return None


def print_dataset_overview(name: str, frame: pd.DataFrame) -> dict:
    print(f"\n=== {name} ===")
    print(f"Shape: {frame.shape}")
    print("Dtypes:")
    print(frame.dtypes)
    print("Head:")
    print(frame.head())

    anomalies = []
    unnamed_columns = [column for column in frame.columns if str(column).startswith("Unnamed")]
    if unnamed_columns:
        anomalies.append(f"Unnamed columns present: {unnamed_columns}")

    missing_by_column = frame.isna().sum()
    missing_total = int(missing_by_column.sum())
    if missing_total:
        top_missing = missing_by_column[missing_by_column > 0].sort_values(ascending=False).head(5)
        anomalies.append(
            "Missing values detected in top columns: "
            + ", ".join(f"{column}={int(count)}" for column, count in top_missing.items())
        )

    duplicate_rows = int(frame.duplicated().sum())
    if duplicate_rows:
        anomalies.append(f"Duplicate rows detected: {duplicate_rows}")

    if not anomalies:
        anomalies.append("No obvious structural anomalies detected.")

    print("Anomalies:")
    for anomaly in anomalies:
        print(f"- {anomaly}")

    return {
        "dataset": name,
        "shape": f"{frame.shape[0]}x{frame.shape[1]}",
        "columns": len(frame.columns),
        "missing_values": missing_total,
        "duplicate_rows": duplicate_rows,
        "anomalies": "; ".join(anomalies),
    }


def load_all_raw_datasets() -> list[dict]:
    csv_files = sorted(RAW_DIR.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(
            f"No CSV files found in {RAW_DIR}. Place the 10 provided datasets there first."
        )

    summaries = []
    for csv_file in csv_files:
        frame = read_csv_file(csv_file)
        summaries.append(print_dataset_overview(csv_file.name, frame))
    return summaries


def infer_fund_master_and_nav_history() -> tuple[Path | None, Path | None]:
    candidates = list(RAW_DIR.glob("*.csv"))
    fund_master = next((path for path in candidates if "fund_master" in path.stem.lower()), None)
    nav_history = next((path for path in candidates if "nav_history" in path.stem.lower()), None)
    return fund_master, nav_history


def quality_check_amfi_codes(fund_master_path: Path, nav_history_path: Path) -> dict:
    fund_master = read_csv_file(fund_master_path)
    nav_history = read_csv_file(nav_history_path)

    fund_code_column = detect_column(fund_master, ("scheme", "code")) or detect_column(
        fund_master, ("amfi", "code")
    )
    nav_code_column = detect_column(nav_history, ("scheme", "code")) or detect_column(
        nav_history, ("amfi", "code")
    )

    if fund_code_column is None or nav_code_column is None:
        raise ValueError("Could not identify scheme code columns in fund_master/nav_history.")

    fund_codes = set(fund_master[fund_code_column].dropna().astype(str).str.strip())
    nav_codes = set(nav_history[nav_code_column].dropna().astype(str).str.strip())
    missing_codes = sorted(fund_codes - nav_codes)
    shared_codes = sorted(fund_codes & nav_codes)

    summary = {
        "fund_master_rows": int(len(fund_master)),
        "nav_history_rows": int(len(nav_history)),
        "fund_master_unique_codes": int(len(fund_codes)),
        "nav_history_unique_codes": int(len(nav_codes)),
        "shared_unique_codes": int(len(shared_codes)),
        "missing_in_nav_history": missing_codes,
        "all_codes_present": len(missing_codes) == 0,
        "coverage_pct": round((len(shared_codes) / len(fund_codes) * 100), 2) if fund_codes else 0.0,
    }

    print("\n=== AMFI Code Validation ===")
    print(json.dumps(summary, indent=2))

    validation_df = pd.DataFrame(
        {
            "fund_master_code": sorted(fund_codes),
            "present_in_nav_history": [code in nav_codes for code in sorted(fund_codes)],
        }
    )
    validation_df.to_csv(REPORTS_DIR / "amfi_code_validation.csv", index=False)

    return summary


def explore_fund_master(fund_master_path: Path) -> dict:
    fund_master = read_csv_file(fund_master_path)

    column_map = {
        "fund_houses": detect_column(fund_master, ("fund", "house")),
        "categories": detect_column(fund_master, ("category",)),
        "sub_categories": detect_column(fund_master, ("sub", "category")),
        "risk_grades": detect_column(fund_master, ("risk",)),
        "scheme_codes": detect_column(fund_master, ("scheme", "code")),
    }

    summary = {}
    for label, column in column_map.items():
        if column:
            values = (
                fund_master[column]
                .dropna()
                .astype(str)
                .str.strip()
                .replace("", pd.NA)
                .dropna()
                .sort_values()
                .unique()
                .tolist()
            )
            summary[label] = values
            print(f"\nUnique {label.replace('_', ' ')}:")
            for value in values[:50]:
                print(f"- {value}")
            if len(values) > 50:
                print(f"- ... and {len(values) - 50} more")
        else:
            summary[label] = []
            print(f"\nUnique {label.replace('_', ' ')}: column not found")

    return summary


def save_report(report_payload: dict) -> Path:
    report_path = REPORTS_DIR / "day1_ingestion_summary.json"
    report_path.write_text(json.dumps(report_payload, indent=2), encoding="utf-8")
    return report_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Day 1 mutual fund ETL: inspect raw CSVs and validate AMFI scheme codes."
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=RAW_DIR,
        help="Directory containing the 10 raw CSV datasets.",
    )
    parser.add_argument(
        "--skip-quality-check",
        action="store_true",
        help="Skip fund_master versus nav_history code validation.",
    )
    return parser


def main() -> None:
    global RAW_DIR
    args = build_parser().parse_args()

    ensure_directories()
    RAW_DIR = args.raw_dir

    dataset_summaries = load_all_raw_datasets()

    fund_master_summary = {}
    quality_summary = {}
    if not args.skip_quality_check:
        fund_master_path, nav_history_path = infer_fund_master_and_nav_history()
        if fund_master_path and nav_history_path:
            fund_master_summary = explore_fund_master(fund_master_path)
            quality_summary = quality_check_amfi_codes(fund_master_path, nav_history_path)
        else:
            print("\nSkipping fund_master/nav_history checks because matching files were not found.")

    report_payload = {
        "datasets": dataset_summaries,
        "fund_master_exploration": fund_master_summary,
        "quality_summary": quality_summary,
    }
    report_path = save_report(report_payload)
    print(f"\nSaved summary report to {report_path}")


if __name__ == "__main__":
    main()
