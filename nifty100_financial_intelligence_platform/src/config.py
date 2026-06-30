from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = Path(os.getenv("RAW_DATA_DIR", BASE_DIR / "data" / "raw"))
PROCESSED_DATA_DIR = Path(os.getenv("PROCESSED_DATA_DIR", BASE_DIR / "data" / "processed"))
DB_PATH = Path(os.getenv("DB_PATH", PROCESSED_DATA_DIR / "nifty100.db"))
REPORTS_DIR = BASE_DIR / "reports"

for path in (RAW_DATA_DIR, PROCESSED_DATA_DIR, REPORTS_DIR):
    path.mkdir(parents=True, exist_ok=True)
