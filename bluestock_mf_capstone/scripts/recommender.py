from __future__ import annotations

import argparse
import csv
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parents[1]
PROCESSED_DIR = REPO_ROOT / "data" / "processed"


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as file_handle:
        return list(csv.DictReader(file_handle))


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file_handle:
        writer = csv.DictWriter(file_handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def load_risk_table() -> list[dict]:
    performance = read_csv(PROCESSED_DIR / "var_cvar_report.csv")
    funds = read_csv(PROCESSED_DIR / "fund_master_cleaned.csv")
    rows = []
    for fund in funds:
        match = next((item for item in performance if item["amfi_code"] == fund["amfi_code"]), None)
        if match:
            rows.append({
                "amfi_code": fund["amfi_code"],
                "scheme_name": fund.get("scheme_name", ""),
                "risk_grade": fund.get("risk_grade", "Moderately High"),
                "historical_var_95_pct": float(match["historical_var_95_pct"]),
                "cvar_95_pct": float(match["cvar_95_pct"]),
            })
    return rows


def recommend(risk_appetite: str, top_n: int = 3) -> list[dict]:
    risk_map = {
        "low": {"low", "moderately low"},
        "moderate": {"moderate", "moderately high"},
        "high": {"high", "aggressive", "moderately high"},
    }
    allowed = risk_map.get(risk_appetite.lower(), risk_map["moderate"])
    rows = [row for row in load_risk_table() if any(level in row["risk_grade"].lower() for level in allowed)]
    rows.sort(key=lambda row: (row["historical_var_95_pct"], row["cvar_95_pct"]))
    return rows[:top_n]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Simple fund recommender by risk appetite.")
    parser.add_argument("--risk-appetite", choices=["Low", "Moderate", "High"], default="Moderate")
    parser.add_argument("--top-n", type=int, default=3)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    recommendations = recommend(args.risk_appetite, args.top_n)
    output_path = PROCESSED_DIR / f"recommendations_{args.risk_appetite.lower()}.csv"
    write_csv(output_path, ["amfi_code", "scheme_name", "risk_grade", "historical_var_95_pct", "cvar_95_pct"], recommendations)
    print(f"Recommendation table written to {output_path}")
    for row in recommendations:
        print(f"{row['amfi_code']} | {row['scheme_name']} | {row['risk_grade']} | VaR {row['historical_var_95_pct']} | CVaR {row['cvar_95_pct']}")


if __name__ == "__main__":
    main()
