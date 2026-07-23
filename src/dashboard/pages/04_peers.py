import streamlit as st
import plotly.graph_objects as go
from src.dashboard.common import selector, safe_chart
from src.dashboard.utils.db import get_companies, get_ratios
st.title("Peer comparison")
ticker=selector(); companies=get_companies(); groups=sorted(companies.sector.dropna().unique()) if not companies.empty else []
group=st.selectbox("Peer group",groups) if groups else None; peers=companies[companies.sector==group] if group else companies
metrics=["roe","roce","npm","opm","debt_equity","interest_coverage","asset_turnover","fcf"]; rows=[]
for t in peers.ticker:
    r=get_ratios(t).sort_values("year"); rows.append(r.iloc[-1][metrics].astype(float).tolist() if not r.empty else [0]*len(metrics))
if rows:
    avg=[sum(x)/len(x) for x in zip(*rows)]; selected=rows[list(peers.ticker).index(ticker)] if ticker in peers.ticker.tolist() else avg
    fig=go.Figure(); fig.add_trace(go.Scatterpolar(r=selected,theta=metrics,fill="toself",name=ticker)); fig.add_trace(go.Scatterpolar(r=avg,theta=metrics,fill="toself",name="Peer average")); safe_chart(fig)
st.dataframe(peers[["ticker","company_name","sector"]],hide_index=True,use_container_width=True)
