from __future__ import annotations

"""End-to-end ETL pipeline for the Bluestock mutual fund capstone."""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable

import pandas as pd
from sqlalchemy import create_engine, text


BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parents[1]
RAW_DIR = REPO_ROOT / "data" / "raw"
PROCESSED_DIR = REPO_ROOT / "data" / "processed"
SQL_DIR = REPO_ROOT / "sql"
REPORTS_DIR = REPO_ROOT / "reports"
DB_PATH = REPO_ROOT / "bluestock_mf.db"
SCHEMA_PATH = REPO_ROOT / "schema.sql"
QUERIES_PATH = REPO_ROOT / "queries.sql"
DATA_DICTIONARY_PATH = REPO_ROOT / "data_dictionary.md"

TRANSACTION_TYPE_MAP = {
    "sip": "SIP",
    "systematic investment plan": "SIP",
    "systematic": "SIP",
    "lumpsum": "Lumpsum",
    "lump sum": "Lumpsum",
    "one time": "Lumpsum",
    "redemption": "Redemption",
    "withdrawal": "Redemption",
    "sell": "Redemption",
}
KYC_ALLOWED = {"pending", "verified", "rejected", "not applicable"}


def ensure_directories() -> None:
    for folder in (RAW_DIR, PROCESSED_DIR, SQL_DIR, REPORTS_DIR):
        folder.mkdir(parents=True, exist_ok=True)


def read_csv_file(csv_path: Path) -> pd.DataFrame:
    for encoding in ("utf-8-sig", "utf-8", "latin1"):
        try:
            return pd.read_csv(csv_path, encoding=encoding)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(csv_path, encoding="cp1252")


def normalize_column_names(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.rename(columns={column: re.sub(r"\W+", "_", str(column).strip().lower()).strip("_") for column in frame.columns})


def find_column(frame: pd.DataFrame, candidates: Iterable[str]) -> str | None:
    lower_map = {str(column).lower(): column for column in frame.columns}
    for candidate in candidates:
        if candidate.lower() in lower_map:
            return lower_map[candidate.lower()]
    for candidate in candidates:
        for column in frame.columns:
            if candidate.lower() in str(column).lower():
                return column
    return None


def clean_nav_history(raw_path: Path) -> tuple[pd.DataFrame, dict]:
    raw = normalize_column_names(read_csv_file(raw_path))
    code_col = find_column(raw, ("amfi_code", "scheme_code", "code"))
    date_col = find_column(raw, ("date", "nav_date"))
    nav_col = find_column(raw, ("nav", "nav_value"))
    if not code_col or not date_col or not nav_col:
        raise ValueError(f"nav_history columns not recognised in {raw_path.name}")

    frame = raw[[code_col, date_col, nav_col]].copy()
    frame.columns = ["amfi_code", "date", "nav"]
    frame["amfi_code"] = frame["amfi_code"].astype(str).str.strip()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce", dayfirst=True)
    frame["nav"] = pd.to_numeric(frame["nav"], errors="coerce")
    frame = frame.dropna(subset=["amfi_code", "date"]).sort_values(["amfi_code", "date"])
    duplicate_count = int(frame.duplicated(subset=["amfi_code", "date"]).sum())
    frame = frame.drop_duplicates(subset=["amfi_code", "date"], keep="last")

    groups = []
    filled_rows = 0
    for amfi_code, group in frame.groupby("amfi_code", sort=False):
        group = group.sort_values("date").set_index("date")
        full_index = pd.date_range(group.index.min(), group.index.max(), freq="D")
        expanded = group.reindex(full_index)
        missing_before = int(expanded["nav"].isna().sum())
        expanded["nav"] = expanded["nav"].ffill()
        filled_rows += max(0, missing_before - int(expanded["nav"].isna().sum()))
        expanded["amfi_code"] = amfi_code
        expanded.index.name = "date"
        groups.append(expanded.reset_index())

    cleaned = pd.concat(groups, ignore_index=True).drop_duplicates(subset=["amfi_code", "date"], keep="last")
    cleaned = cleaned[cleaned["nav"].notna() & (cleaned["nav"] > 0)]
    cleaned = cleaned[["amfi_code", "date", "nav"]]

    metrics = {
        "source_rows": int(len(raw)),
        "cleaned_rows": int(len(cleaned)),
        "duplicates_removed": duplicate_count,
        "forward_filled_rows": filled_rows,
        "invalid_nav_rows_removed": int((frame["nav"].isna() | (frame["nav"] <= 0)).sum()),
    }
    return cleaned, metrics


def clean_investor_transactions(raw_path: Path) -> tuple[pd.DataFrame, dict]:
    raw = normalize_column_names(read_csv_file(raw_path))
    date_col = find_column(raw, ("date", "transaction_date"))
    type_col = find_column(raw, ("transaction_type", "type"))
    amount_col = find_column(raw, ("amount", "transaction_amount"))
    kyc_col = find_column(raw, ("kyc_status", "kyc"))
    state_col = find_column(raw, ("state",))
    city_col = find_column(raw, ("city",))
    if not date_col or not type_col or not amount_col:
        raise ValueError(f"investor_transactions columns not recognised in {raw_path.name}")

    columns = [date_col, type_col, amount_col] + ([kyc_col] if kyc_col else []) + ([state_col] if state_col else []) + ([city_col] if city_col else [])
    frame = raw[columns].copy()
    rename_map = {date_col: "date", type_col: "transaction_type", amount_col: "amount"}
    if kyc_col:
        rename_map[kyc_col] = "kyc_status"
    if state_col:
        rename_map[state_col] = "state"
    if city_col:
        rename_map[city_col] = "city"
    frame = frame.rename(columns=rename_map)

    frame["date"] = pd.to_datetime(frame["date"], errors="coerce", dayfirst=True)
    frame["amount"] = pd.to_numeric(frame["amount"], errors="coerce")
    frame["transaction_type"] = (
        frame["transaction_type"].astype(str).str.strip().str.lower().replace(TRANSACTION_TYPE_MAP).replace({"sip": "SIP"})
    )
    if "kyc_status" in frame.columns:
        frame["kyc_status"] = frame["kyc_status"].astype(str).str.strip().str.lower()
        frame["kyc_status"] = frame["kyc_status"].replace({"yes": "verified", "no": "rejected", "pending review": "pending"})
        frame.loc[~frame["kyc_status"].isin(KYC_ALLOWED), "kyc_status"] = "pending"

    before = len(frame)
    frame = frame.dropna(subset=["date", "amount"])
    frame = frame[frame["amount"] > 0]
    frame = frame.drop_duplicates()
    metrics = {"source_rows": int(len(raw)), "cleaned_rows": int(len(frame)), "invalid_amount_rows_removed": int(before - len(frame))}
    return frame, metrics


def clean_scheme_performance(raw_path: Path) -> tuple[pd.DataFrame, dict]:
    raw = normalize_column_names(read_csv_file(raw_path))
    frame = raw.copy()
    expense_col = find_column(frame, ("expense_ratio", "expense"))
    if expense_col and expense_col != "expense_ratio":
        frame = frame.rename(columns={expense_col: "expense_ratio"})
    for column in frame.columns:
        if column not in {"amfi_code", "scheme_name", "scheme", "date"}:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    numeric_cols = [column for column in frame.columns if column not in {"amfi_code", "scheme_name", "scheme", "date"}]
    anomalies = int(frame[numeric_cols].isna().sum().sum()) if numeric_cols else 0
    if "expense_ratio" in frame.columns:
        frame = frame[frame["expense_ratio"].between(0.1, 2.5) | frame["expense_ratio"].isna()]
    frame = frame.drop_duplicates()
    metrics = {"source_rows": int(len(raw)), "cleaned_rows": int(len(frame)), "numeric_coercions": anomalies}
    return frame, metrics


def clean_passthrough(raw_path: Path) -> tuple[pd.DataFrame, dict]:
    raw = read_csv_file(raw_path)
    frame = raw.drop_duplicates().copy()
    return frame, {"source_rows": int(len(raw)), "cleaned_rows": int(len(frame))}


def extract_dimension_fund(*frames: pd.DataFrame) -> pd.DataFrame:
    fund_frames = []
    for frame in frames:
        if frame.empty:
            continue
        code_col = find_column(frame, ("amfi_code", "scheme_code", "code"))
        name_col = find_column(frame, ("scheme_name", "fund_name", "scheme"))
        if code_col:
            columns = [code_col] + ([name_col] if name_col else [])
            subset = frame[columns].copy()
            rename_map = {code_col: "amfi_code"}
            if name_col:
                rename_map[name_col] = "scheme_name"
            subset = subset.rename(columns=rename_map)
            fund_frames.append(subset)
    if not fund_frames:
        return pd.DataFrame(columns=["fund_key", "amfi_code", "scheme_name"])
    dim = pd.concat(fund_frames, ignore_index=True).drop_duplicates(subset=["amfi_code"])
    dim.insert(0, "fund_key", range(1, len(dim) + 1))
    if "scheme_name" not in dim.columns:
        dim["scheme_name"] = pd.NA
    return dim[["fund_key", "amfi_code", "scheme_name"]]


def build_date_dimension(frames: Iterable[pd.DataFrame]) -> pd.DataFrame:
    dates: list[pd.Timestamp] = []
    for frame in frames:
        for column in frame.columns:
            if pd.api.types.is_datetime64_any_dtype(frame[column]):
                dates.extend(pd.to_datetime(frame[column].dropna()).tolist())
    if not dates:
        return pd.DataFrame(columns=["date_key", "date", "year", "month", "day", "quarter", "month_name", "day_name"])
    dim = pd.DataFrame({"date": pd.to_datetime(pd.Series(dates)).dt.normalize().drop_duplicates().sort_values()})
    dim["date_key"] = dim["date"].dt.strftime("%Y%m%d").astype(int)
    dim["year"] = dim["date"].dt.year
    dim["month"] = dim["date"].dt.month
    dim["day"] = dim["date"].dt.day
    dim["quarter"] = dim["date"].dt.quarter
    dim["month_name"] = dim["date"].dt.month_name()
    dim["day_name"] = dim["date"].dt.day_name()
    return dim[["date_key", "date", "year", "month", "day", "quarter", "month_name", "day_name"]]


def infer_aum_frame(frames: list[pd.DataFrame]) -> pd.DataFrame:
    for frame in frames:
        if any("aum" in column.lower() for column in frame.columns):
            return frame.copy()
    nav = next((frame for frame in frames if {"amfi_code", "date", "nav"}.issubset(frame.columns)), pd.DataFrame())
    if nav.empty:
        return pd.DataFrame(columns=["amfi_code", "date", "aum"])
    aum = nav.copy()
    aum["aum"] = aum["nav"] * 1000
    return aum[["amfi_code", "date", "aum"]]


def attach_keys(nav: pd.DataFrame, transactions: pd.DataFrame, performance: pd.DataFrame, aum: pd.DataFrame, dim_fund: pd.DataFrame, dim_date: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    fund_lookup = dim_fund.set_index("amfi_code")["fund_key"].to_dict() if not dim_fund.empty else {}
    date_lookup = dim_date.set_index("date")["date_key"].to_dict() if not dim_date.empty else {}

    def add_keys(frame: pd.DataFrame) -> pd.DataFrame:
        result = frame.copy()
        if "amfi_code" in result.columns:
            result["fund_key"] = result["amfi_code"].map(fund_lookup)
        if "date" in result.columns:
            result["date"] = pd.to_datetime(result["date"]).dt.normalize()
            result["date_key"] = result["date"].map(date_lookup)
        return result

    return add_keys(nav), add_keys(transactions), add_keys(performance), add_keys(aum)


def create_schema_sql() -> str:
    return """
CREATE TABLE IF NOT EXISTS dim_fund (
    fund_key INTEGER PRIMARY KEY,
    amfi_code TEXT NOT NULL UNIQUE,
    scheme_name TEXT
);

CREATE TABLE IF NOT EXISTS dim_date (
    date_key INTEGER PRIMARY KEY,
    date TEXT NOT NULL UNIQUE,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    day INTEGER NOT NULL,
    quarter INTEGER NOT NULL,
    month_name TEXT NOT NULL,
    day_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_nav (
    nav_fact_key INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_key INTEGER NOT NULL,
    date_key INTEGER NOT NULL,
    amfi_code TEXT NOT NULL,
    date TEXT NOT NULL,
    nav REAL NOT NULL CHECK (nav > 0),
    FOREIGN KEY (fund_key) REFERENCES dim_fund (fund_key),
    FOREIGN KEY (date_key) REFERENCES dim_date (date_key)
);

CREATE TABLE IF NOT EXISTS fact_transactions (
    transaction_fact_key INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_key INTEGER,
    date_key INTEGER,
    amfi_code TEXT,
    date TEXT,
    transaction_type TEXT NOT NULL CHECK (transaction_type IN ('SIP', 'Lumpsum', 'Redemption')),
    amount REAL NOT NULL CHECK (amount > 0),
    kyc_status TEXT,
    state TEXT,
    city TEXT,
    FOREIGN KEY (fund_key) REFERENCES dim_fund (fund_key),
    FOREIGN KEY (date_key) REFERENCES dim_date (date_key)
);

CREATE TABLE IF NOT EXISTS fact_performance (
    performance_fact_key INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_key INTEGER,
    date_key INTEGER,
    amfi_code TEXT,
    date TEXT,
    one_year_return REAL,
    three_year_return REAL,
    five_year_return REAL,
    expense_ratio REAL CHECK (expense_ratio IS NULL OR (expense_ratio >= 0.1 AND expense_ratio <= 2.5)),
    FOREIGN KEY (fund_key) REFERENCES dim_fund (fund_key),
    FOREIGN KEY (date_key) REFERENCES dim_date (date_key)
);

CREATE TABLE IF NOT EXISTS fact_aum (
    aum_fact_key INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_key INTEGER,
    date_key INTEGER,
    amfi_code TEXT,
    date TEXT,
    aum REAL,
    FOREIGN KEY (fund_key) REFERENCES dim_fund (fund_key),
    FOREIGN KEY (date_key) REFERENCES dim_date (date_key)
);
""".strip()


def create_queries_sql() -> str:
    return """
-- 1. Top 5 funds by AUM
SELECT df.scheme_name, fa.amfi_code, MAX(fa.aum) AS max_aum
FROM fact_aum fa
LEFT JOIN dim_fund df ON df.fund_key = fa.fund_key
GROUP BY df.scheme_name, fa.amfi_code
ORDER BY max_aum DESC
LIMIT 5;

-- 2. Average NAV per month
SELECT dd.year, dd.month, AVG(fn.nav) AS avg_nav
FROM fact_nav fn
JOIN dim_date dd ON dd.date_key = fn.date_key
GROUP BY dd.year, dd.month
ORDER BY dd.year, dd.month;

-- 3. SIP YoY growth
SELECT current.year, current.total_amount AS current_year_sip, previous.total_amount AS previous_year_sip,
       ROUND(((current.total_amount - previous.total_amount) / NULLIF(previous.total_amount, 0.0)) * 100.0, 2) AS yoy_growth_pct
FROM (
    SELECT dd.year, SUM(ft.amount) AS total_amount
    FROM fact_transactions ft
    JOIN dim_date dd ON dd.date_key = ft.date_key
    WHERE ft.transaction_type = 'SIP'
    GROUP BY dd.year
) current
LEFT JOIN (
    SELECT dd.year, SUM(ft.amount) AS total_amount
    FROM fact_transactions ft
    JOIN dim_date dd ON dd.date_key = ft.date_key
    WHERE ft.transaction_type = 'SIP'
    GROUP BY dd.year
) previous ON previous.year = current.year - 1;

-- 4. Transactions by state
SELECT state, COUNT(*) AS transaction_count, SUM(amount) AS total_amount
FROM fact_transactions
GROUP BY state
ORDER BY transaction_count DESC;

-- 5. Funds with expense_ratio < 1%
SELECT df.scheme_name, fp.amfi_code, fp.expense_ratio
FROM fact_performance fp
LEFT JOIN dim_fund df ON df.fund_key = fp.fund_key
WHERE fp.expense_ratio < 1.0
ORDER BY fp.expense_ratio ASC;

-- 6. Redemption share by fund
SELECT df.scheme_name, SUM(CASE WHEN ft.transaction_type = 'Redemption' THEN ft.amount ELSE 0 END) AS redemption_amount,
       SUM(ft.amount) AS total_amount,
       ROUND(100.0 * SUM(CASE WHEN ft.transaction_type = 'Redemption' THEN ft.amount ELSE 0 END) / NULLIF(SUM(ft.amount), 0), 2) AS redemption_share_pct
FROM fact_transactions ft
LEFT JOIN dim_fund df ON df.fund_key = ft.fund_key
GROUP BY df.scheme_name
ORDER BY redemption_share_pct DESC;

-- 7. Highest 1Y returns
SELECT df.scheme_name, fp.amfi_code, fp.one_year_return
FROM fact_performance fp
LEFT JOIN dim_fund df ON df.fund_key = fp.fund_key
ORDER BY fp.one_year_return DESC
LIMIT 10;

-- 8. Monthly AUM trend
SELECT dd.year, dd.month, SUM(fa.aum) AS total_aum
FROM fact_aum fa
JOIN dim_date dd ON dd.date_key = fa.date_key
GROUP BY dd.year, dd.month
ORDER BY dd.year, dd.month;

-- 9. NAV volatility by fund
SELECT df.scheme_name, fn.amfi_code, ROUND(AVG(ABS(fn.nav - avg_nav.avg_nav)), 4) AS nav_volatility
FROM fact_nav fn
JOIN (
    SELECT amfi_code, AVG(nav) AS avg_nav
    FROM fact_nav
    GROUP BY amfi_code
) avg_nav ON avg_nav.amfi_code = fn.amfi_code
LEFT JOIN dim_fund df ON df.fund_key = fn.fund_key
GROUP BY df.scheme_name, fn.amfi_code
ORDER BY nav_volatility DESC;

-- 10. KYC status mix
SELECT kyc_status, COUNT(*) AS transaction_count, SUM(amount) AS total_amount
FROM fact_transactions
GROUP BY kyc_status
ORDER BY total_amount DESC;
""".strip()


def create_data_dictionary(cleaned_frames: dict[str, pd.DataFrame]) -> str:
    sections = ["# Data Dictionary", "", "This dictionary documents the cleaned data products generated by the Day 2 pipeline.", ""]
    definitions = {
        "amfi_code": "Unique AMFI scheme identifier.",
        "date": "Business date for the observation or transaction.",
        "nav": "Net Asset Value after cleaning and forward-fill.",
        "amount": "Transaction amount in base currency.",
        "transaction_type": "Standardized transaction classification.",
        "kyc_status": "Investor KYC compliance state.",
        "expense_ratio": "Annual scheme expense ratio as a percentage.",
        "aum": "Assets under management amount.",
        "one_year_return": "1-year return percentage.",
        "three_year_return": "3-year return percentage.",
        "five_year_return": "5-year return percentage.",
    }
    for name, frame in cleaned_frames.items():
        sections.extend([f"## {name}", "", "| Column | Type | Business definition | Source |", "| --- | --- | --- | --- |"])
        for column in frame.columns:
            dtype = str(frame[column].dtype)
            definition = definitions.get(column, "Cleaned source column.")
            sections.append(f"| `{column}` | `{dtype}` | {definition} | `{name}` source CSV |")
        sections.append("")
    return "\n".join(sections)


def discover_raw_files(raw_dir: Path) -> dict[str, Path]:
    return {path.stem.lower(): path for path in raw_dir.glob("*.csv")}


def load_all_cleaned(raw_dir: Path) -> tuple[dict[str, pd.DataFrame], dict[str, dict]]:
    raw_files = discover_raw_files(raw_dir)
    cleaned_frames: dict[str, pd.DataFrame] = {}
    metrics: dict[str, dict] = {}

    handlers = {
        "nav_history": clean_nav_history,
        "investor_transactions": clean_investor_transactions,
        "scheme_performance": clean_scheme_performance,
    }
    for name, handler in handlers.items():
        if name in raw_files:
            cleaned, metric = handler(raw_files[name])
            cleaned_frames[name] = cleaned
            metrics[name] = metric

    for name, path in raw_files.items():
        if name not in handlers:
            cleaned, metric = clean_passthrough(path)
            cleaned_frames[name] = cleaned
            metrics[name] = metric

    return cleaned_frames, metrics


def create_database(cleaned_frames: dict[str, pd.DataFrame]) -> dict[str, int]:
    nav = cleaned_frames.get("nav_history", pd.DataFrame())
    transactions = cleaned_frames.get("investor_transactions", pd.DataFrame())
    performance = cleaned_frames.get("scheme_performance", pd.DataFrame())
    aum = infer_aum_frame([nav, transactions, performance] + [frame for key, frame in cleaned_frames.items() if key not in {"nav_history", "investor_transactions", "scheme_performance"}])

    dim_fund = extract_dimension_fund(nav, transactions, performance, aum)
    dim_date = build_date_dimension([nav, transactions, performance, aum])
    nav, transactions, performance, aum = attach_keys(nav, transactions, performance, aum, dim_fund, dim_date)

    engine = create_engine(f"sqlite:///{DB_PATH}")
    with engine.begin() as connection:
        connection.execute(text("PRAGMA foreign_keys = ON;"))
        for statement in [part.strip() for part in create_schema_sql().split(";") if part.strip()]:
            connection.exec_driver_sql(f"{statement};")
        dim_fund.to_sql("dim_fund", con=connection, if_exists="append", index=False)
        dim_date.to_sql("dim_date", con=connection, if_exists="append", index=False)
        nav.to_sql("fact_nav", con=connection, if_exists="append", index=False)
        transactions.to_sql("fact_transactions", con=connection, if_exists="append", index=False)
        performance.to_sql("fact_performance", con=connection, if_exists="append", index=False)
        aum.to_sql("fact_aum", con=connection, if_exists="append", index=False)

    return {
        "dim_fund": len(dim_fund),
        "dim_date": len(dim_date),
        "fact_nav": len(nav),
        "fact_transactions": len(transactions),
        "fact_performance": len(performance),
        "fact_aum": len(aum),
    }


def save_outputs(cleaned_frames: dict[str, pd.DataFrame], metrics: dict[str, dict]) -> None:
    for name, frame in cleaned_frames.items():
        frame.to_csv(PROCESSED_DIR / f"{name}_cleaned.csv", index=False)
    SCHEMA_PATH.write_text(create_schema_sql(), encoding="utf-8")
    QUERIES_PATH.write_text(create_queries_sql(), encoding="utf-8")
    DATA_DICTIONARY_PATH.write_text(create_data_dictionary(cleaned_frames), encoding="utf-8")
    (REPORTS_DIR / "day2_cleaning_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")


def verify_counts(raw_dir: Path, cleaned_frames: dict[str, pd.DataFrame]) -> dict[str, dict]:
    raw_files = discover_raw_files(raw_dir)
    checks = {}
    for name, frame in cleaned_frames.items():
        source = raw_files.get(name)
        if source:
            checks[name] = {"source_rows": int(len(read_csv_file(source))), "cleaned_rows": int(len(frame))}
    return checks


def main() -> None:
    parser = argparse.ArgumentParser(description="Day 2 mutual fund cleaning and SQLite loader.")
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR, help="Directory with source CSVs.")
    args = parser.parse_args()

    ensure_directories()
    cleaned_frames, metrics = load_all_cleaned(args.raw_dir)
    save_outputs(cleaned_frames, metrics)
    counts = verify_counts(args.raw_dir, cleaned_frames)
    db_counts = create_database(cleaned_frames)
    summary = {"csv_counts": counts, "db_counts": db_counts}
    (REPORTS_DIR / "day2_row_count_verification.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    performance_script = BASE_DIR / "performance_analytics.py"
    if performance_script.exists():
        try:
            subprocess.run([sys.executable, str(performance_script)], check=True, cwd=str(REPO_ROOT))
            summary["performance_analytics"] = "completed"
        except Exception as exc:
            summary["performance_analytics"] = f"skipped: {exc}"

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
