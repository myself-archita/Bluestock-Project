from __future__ import annotations
import streamlit as st
from .utils.db import get_companies

def sidebar_year():
    return st.sidebar.selectbox("Analysis year", list(range(2024, 2018, -1)))

def selector(label="Company", key="ticker"):
    companies = get_companies()
    if companies.empty: return None
    labels = {r.ticker: f"{r.company_name} ({r.ticker})" for r in companies.itertuples()}
    return st.selectbox(label, companies.ticker.tolist(), format_func=lambda x: labels.get(x, x), key=key)

def metric_row(values):
    for col, (label, value) in zip(st.columns(len(values)), values): col.metric(label, value)

def safe_chart(fig):
    fig.update_layout(height=380, margin=dict(l=10, r=10, t=35, b=10), autosize=True)
    st.plotly_chart(fig, use_container_width=True)
