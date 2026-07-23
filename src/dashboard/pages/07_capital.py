import streamlit as st
import plotly.express as px
from src.dashboard.common import safe_chart
from src.dashboard.utils.db import company_frame
st.title("Capital allocation map"); df=company_frame()
if not df.empty:
    df["pattern"]=df["capital_allocation_class"].fillna("balanced") if "capital_allocation_class" in df else "balanced"; safe_chart(px.treemap(df,path=["pattern","sector","company_name"],values="composite_score",title="Capital allocation patterns")); pattern=st.selectbox("Inspect pattern",sorted(df.pattern.unique())); st.dataframe(df[df.pattern==pattern][["ticker","company_name","sector"]],hide_index=True,use_container_width=True)
