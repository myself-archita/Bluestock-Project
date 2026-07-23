from __future__ import annotations

import sqlite3
from pathlib import Path
import pandas as pd
import streamlit as st

from src.config import DB_PATH

_ROOT = Path(__file__).resolve().parents[2]

def _read(sql: str, params: tuple = ()) -> pd.DataFrame:
    if not Path(DB_PATH).exists():
        return pd.DataFrame()
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(sql, conn, params=params)

@st.cache_data(ttl=600)
def get_companies() -> pd.DataFrame:
    return _read("SELECT * FROM companies ORDER BY company_name")

@st.cache_data(ttl=600)
def get_ratios(ticker: str | None = None, year: int | None = None) -> pd.DataFrame:
    sql, params = "SELECT * FROM financial_ratios", []
    filters = []
    if ticker: filters.append("ticker = ?"); params.append(ticker)
    if year: filters.append("year = ?"); params.append(year)
    if filters: sql += " WHERE " + " AND ".join(filters)
    return _read(sql + " ORDER BY year", tuple(params))

@st.cache_data(ttl=600)
def get_pl(ticker: str | None = None) -> pd.DataFrame:
    return _read("SELECT * FROM financials WHERE ticker = ? ORDER BY year", (ticker,)) if ticker else _read("SELECT * FROM financials ORDER BY year")

@st.cache_data(ttl=600)
def get_bs(ticker: str | None = None) -> pd.DataFrame:
    cols = "ticker, year, equity, debt, assets"
    return _read(f"SELECT {cols} FROM financials WHERE ticker = ? ORDER BY year", (ticker,)) if ticker else _read(f"SELECT {cols} FROM financials ORDER BY year")

@st.cache_data(ttl=600)
def get_cf(ticker: str | None = None) -> pd.DataFrame:
    cols = "ticker, year, cfo, capex"
    return _read(f"SELECT {cols} FROM financials WHERE ticker = ? ORDER BY year", (ticker,)) if ticker else _read(f"SELECT {cols} FROM financials ORDER BY year")

@st.cache_data(ttl=600)
def get_sectors() -> pd.DataFrame:
    return _read("SELECT sector, COUNT(*) AS company_count FROM companies GROUP BY sector ORDER BY company_count DESC")

@st.cache_data(ttl=600)
def get_peers(group_name: str | None = None) -> pd.DataFrame:
    if group_name:
        return _read("SELECT * FROM peer_percentiles WHERE peer_group = ?", (group_name,))
    return _read("SELECT DISTINCT peer_group FROM peer_percentiles ORDER BY peer_group")

@st.cache_data(ttl=600)
def get_valuation(ticker: str | None = None) -> pd.DataFrame:
    path = _ROOT / "output" / "valuation_summary.xlsx"
    if path.exists():
        frame = pd.read_excel(path)
        return frame[frame.company_id == ticker] if ticker and "company_id" in frame else frame
    return pd.DataFrame()

def company_frame(year: int | None = None) -> pd.DataFrame:
    companies, ratios, financials = get_companies(), get_ratios(year=year), get_pl()
    if companies.empty: return pd.DataFrame()
    latest = ratios.sort_values("year").groupby("ticker").tail(1) if not ratios.empty else pd.DataFrame()
    out = companies.merge(latest, on="ticker", how="left")
    if not financials.empty:
        fin = financials.sort_values("year").groupby("ticker").agg(first_sales=("sales", "first"), last_sales=("sales", "last"), first_year=("year", "first"), last_year=("year", "last")).reset_index()
        fin["revenue_cagr_5yr"] = ((fin.last_sales / fin.first_sales).clip(lower=0) ** (1 / (fin.last_year - fin.first_year).clip(lower=1)) - 1) * 100
        out = out.merge(fin[["ticker", "revenue_cagr_5yr"]], on="ticker", how="left")
    for col in ["roe", "roce", "npm", "debt_equity", "fcf", "revenue_cagr_5yr"]:
        if col not in out: out[col] = pd.NA
    out["composite_score"] = out[["roe", "roce", "npm"]].fillna(0).mean(axis=1) * 100
    return out

def fmt(value, suffix=""):
    return "N/A" if value is None or pd.isna(value) else f"{value:.1f}{suffix}"
