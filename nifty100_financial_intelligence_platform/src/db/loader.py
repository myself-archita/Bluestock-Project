from __future__ import annotations

import sqlite3
from pathlib import Path
import pandas as pd


def create_database(db_path: str | Path, schema_path: str | Path) -> None:
    with sqlite3.connect(db_path) as conn, open(schema_path, "r", encoding="utf-8") as handle:
        conn.executescript(handle.read())


def insert_dataframe(db_path: str | Path, table: str, df: pd.DataFrame) -> None:
    with sqlite3.connect(db_path) as conn:
        df.to_sql(table, conn, if_exists="append", index=False)
