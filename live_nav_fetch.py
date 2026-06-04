from __future__ import annotations

import json
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
        frame["nav"] = pd.to_numeric(frame.get("nav"), errors="coerce")
        frame["date"] = pd.to_datetime(frame.get("date"), errors="coerce")
        frame["fetched_at_utc"] = datetime.now(timezone.utc).isoformat()
        frame["fund_house"] = meta.get("fund_house")
        frame["scheme_type"] = meta.get("scheme_type")
        frame["scheme_category"] = meta.get("scheme_category")
    return frame


def main() -> None:
    all_frames = []
    for scheme_name, scheme_code in SCHEMES.items():
        frame = fetch_scheme_nav(scheme_name, scheme_code)
        output_path = RAW_DIR / f"{scheme_code}_{scheme_name.lower().replace(' ', '_')}.csv"
        frame.to_csv(output_path, index=False)
        print(f"Saved {scheme_name} to {output_path} ({frame.shape[0]} rows)")
        all_frames.append(frame)

    combined = pd.concat(all_frames, ignore_index=True) if all_frames else pd.DataFrame()
    combined_path = RAW_DIR / "live_nav_snapshot.csv"
    combined.to_csv(combined_path, index=False)
    print(f"Saved combined snapshot to {combined_path}")

    metadata_path = RAW_DIR / "live_nav_fetch_metadata.json"
    metadata_path.write_text(
        json.dumps({"schemes": SCHEMES, "row_count": int(len(combined))}, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
