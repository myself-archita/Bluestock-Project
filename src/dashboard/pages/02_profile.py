import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from src.dashboard.common import selector, metric_row, safe_chart
from src.dashboard.utils.db import get_companies, get_pl, get_ratios, fmt

st.title("Company profile")
ticker = selector("Search company or ticker")
if not ticker: st.info("Ticker not found — please try another"); st.stop()
company=get_companies().query("ticker == @ticker").iloc[0]; fin=get_pl(ticker); rat=get_ratios(ticker)
st.subheader(company.company_name); st.caption(f"{company.sector} · {company.industry or 'Industry not available'} · NSE: {ticker}")
if rat.empty: st.info("Ticker not found — please try another"); st.stop()
latest=rat.sort_values("year").iloc[-1]
metric_row([("ROE",fmt(latest.get("roe"),"%")),("ROCE",fmt(latest.get("roce"),"%")),("Net Profit Margin",fmt(latest.get("npm"),"%")),("D/E",fmt(latest.get("debt_equity"))),("Revenue CAGR 5yr","N/A"),("FCF",fmt(latest.get("fcf")))])
if not fin.empty:
    safe_chart(px.bar(fin,x="year",y=["sales","pat"],barmode="group",title="Revenue and net profit"))
    fig=go.Figure(); fig.add_trace(go.Scatter(x=rat.year,y=rat.roe,name="ROE")); fig.add_trace(go.Scatter(x=rat.year,y=rat.roce,name="ROCE",yaxis="y2")); fig.update_layout(title="ROE and ROCE",yaxis2=dict(overlaying="y",side="right")); safe_chart(fig)
st.subheader("Investment view"); st.success("✓ Profitability data is available for this company."); st.info("✕ Narrative pros/cons require enriched company master data.")
