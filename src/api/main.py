from __future__ import annotations

import sqlite3
from pathlib import Path
from fastapi import FastAPI
from ..config import DB_PATH

app = FastAPI(title="NIFTY 100 Financial Intelligence Platform")


def fetch_rows(query: str, params: tuple = ()) -> list[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(row) for row in conn.execute(query, params).fetchall()]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/companies")
def companies():
    return fetch_rows("SELECT * FROM companies ORDER BY ticker")


@app.get("/ratios/{ticker}")
def ratios(ticker: str):
    return fetch_rows("SELECT * FROM financial_ratios WHERE ticker = ? ORDER BY year", (ticker.upper(),))
