from __future__ import annotations

import streamlit as st
import pandas as pd
from src.config import DB_PATH
import sqlite3


st.set_page_config(page_title="NIFTY 100 Financial Intelligence Platform", layout="wide")
st.title("NIFTY 100 Financial Intelligence Platform")
st.caption("Submission-ready prototype for ETL, ratios, screener, peer comparison, and API.")


def load_table(name: str) -> pd.DataFrame:
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(f"SELECT * FROM {name}", conn)


try:
    companies = load_table("companies")
    ratios = load_table("financial_ratios")
    st.metric("Companies", len(companies))
    st.metric("Ratio Rows", len(ratios))
    ticker = st.selectbox("Select ticker", companies["ticker"].tolist())
    st.dataframe(ratios[ratios["ticker"] == ticker].sort_values("year"), use_container_width=True)
except Exception as exc:
    st.info(f"Load the database first. {exc}")
