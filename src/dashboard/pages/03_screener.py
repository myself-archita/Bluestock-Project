import streamlit as st
from src.dashboard.utils.db import company_frame

st.title("Screener")
df=company_frame()
if df.empty: st.warning("No data available"); st.stop()
presets={"Quality":(15,2,0),"Value":(0,3,0),"Growth":(10,3,0),"Dividend":(0,4,0),"Debt-Free":(0,0,0),"Turnaround":(0,5,0)}
preset=st.sidebar.radio("Preset",["Custom"]+list(presets))
roe_default,de_default,fcf_default=presets.get(preset,(0,10,-1))
roe=st.sidebar.slider("ROE min",0.,100.,float(roe_default)); de=st.sidebar.slider("D/E max",0.,10.,float(de_default)); fcf=st.sidebar.slider("FCF min",-1000.,10000.,float(fcf_default))
for col,value in [("roe",roe),("fcf",fcf)]: df=df[df[col].fillna(-1)>=value]
df=df[df.debt_equity.fillna(999)<=de]
st.write(f"{len(df)} companies match your filters")
visible=[c for c in ["ticker","company_name","sector","composite_score","roe","roce","npm","debt_equity","fcf","revenue_cagr_5yr"] if c in df]
st.download_button("Download CSV",df[visible].to_csv(index=False).encode(),"screener_results.csv","text/csv")
st.dataframe(df[visible],hide_index=True,use_container_width=True)
