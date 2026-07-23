import streamlit as st
import plotly.express as px
from src.dashboard.common import safe_chart
from src.dashboard.utils.db import company_frame
st.title("Sector analysis"); df=company_frame(); sector=st.selectbox("Sector",sorted(df.sector.dropna().unique())) if not df.empty else None; view=df[df.sector==sector] if sector else df
if not view.empty: safe_chart(px.scatter(view,x="composite_score",y="roe",size="composite_score",color="industry",hover_name="company_name",title=f"{sector} companies")); st.subheader("Sector median KPIs"); st.bar_chart(view[[c for c in ["roe","roce","npm","opm"] if c in view]].median())
