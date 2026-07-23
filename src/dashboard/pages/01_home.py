import streamlit as st
import plotly.express as px
from src.dashboard.common import sidebar_year, metric_row, safe_chart
from src.dashboard.utils.db import company_frame

st.title("Market overview")
year = sidebar_year(); df = company_frame(year)
if df.empty: st.warning("No financial data is available yet."); st.stop()
metric_row([("Average ROE",f"{df.roe.mean()*100:.1f}%"),("Median P/E","N/A"),("Median D/E",f"{df.debt_equity.median():.2f}"),("Total Companies",len(df)),("Median Revenue CAGR 5yr",f"{df.revenue_cagr_5yr.median():.1f}%"),("Debt-Free Companies",int((df.debt_equity.fillna(0)<=0).sum()))])
c1,c2=st.columns([1,1.4])
with c1: safe_chart(px.pie(df,names="sector",hole=.58,title="Companies by sector"))
with c2: st.subheader("Top quality companies"); st.dataframe(df.nlargest(5,"composite_score")[["ticker","company_name","sector","composite_score","roe","roce"]],hide_index=True,use_container_width=True)
