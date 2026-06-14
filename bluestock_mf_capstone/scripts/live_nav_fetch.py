from __future__ import annotations

"""Fetch live NAV snapshots for a small reference basket of schemes."""

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests


BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)


SCHEMES = {
    "HDFC Top 100 Direct": "125497",
    "SBI Bluechip": "119551",
    "ICICI Bluechip": "120503",
    "Nippon Large Cap": "118632",
    "Axis Bluechip": "119092",
    "Kotak Bluechip": "120841",
}


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def fetch_scheme_nav(scheme_name: str, scheme_code: str) -> pd.DataFrame:
    response = requests.get(f"https://api.mfapi.in/mf/{scheme_code}", timeout=30)
    response.raise_for_status()
    payload = response.json()

    meta = payload.get("meta", {})
    data = payload.get("data", [])
    frame = pd.DataFrame(data)
    if not frame.empty:
        frame.insert(0, "scheme_name", scheme_name)
        frame.insert(1, "scheme_code", scheme_code)
        if "nav" in frame.columns:
            frame["nav"] = pd.to_numeric(frame["nav"], errors="coerce")
        if "date" in frame.columns:
            frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
        frame["fetched_at_utc"] = datetime.now(timezone.utc).isoformat()
        frame["fund_house"] = meta.get("fund_house")
        frame["scheme_type"] = meta.get("scheme_type")
        frame["scheme_category"] = meta.get("scheme_category")
    return frame


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fetch live NAV histories from mfapi.in for the requested schemes."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=RAW_DIR,
        help="Directory where the raw CSV files should be written.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    all_frames = []
    fetch_log = []
    for scheme_name, scheme_code in SCHEMES.items():
        frame = fetch_scheme_nav(scheme_name, scheme_code)
        output_path = output_dir / f"{scheme_code}_{slugify(scheme_name)}.csv"
        frame.to_csv(output_path, index=False)
        print(f"Saved {scheme_name} to {output_path} ({frame.shape[0]} rows)")
        all_frames.append(frame)
        fetch_log.append(
            {
                "scheme_name": scheme_name,
                "scheme_code": scheme_code,
                "rows": int(frame.shape[0]),
                "output_path": str(output_path),
            }
        )

    combined = pd.concat(all_frames, ignore_index=True) if all_frames else pd.DataFrame()
    combined_path = output_dir / "live_nav_snapshot.csv"
    combined.to_csv(combined_path, index=False)
    print(f"Saved combined snapshot to {combined_path}")

    metadata_path = output_dir / "live_nav_fetch_metadata.json"
    metadata_path.write_text(
        json.dumps(
            {
                "schemes": SCHEMES,
                "row_count": int(len(combined)),
                "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
                "outputs": fetch_log,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
