import streamlit as st
import plotly.express as px
from src.dashboard.common import selector, safe_chart
from src.dashboard.utils.db import get_ratios
st.title("Trend analysis"); ticker=selector(); df=get_ratios(ticker)
if not df.empty:
    metrics=[c for c in ["roe","roce","npm","opm","debt_equity","fcf"] if c in df]; chosen=st.multiselect("Overlay up to 3 metrics",metrics,default=metrics[:2],max_selections=3); safe_chart(px.line(df,x="year",y=chosen,markers=True,title="Year-on-year financial trends"))
