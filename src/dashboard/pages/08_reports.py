import streamlit as st
from src.dashboard.common import selector
st.title("Annual reports"); selector()
st.info("Report links are shown when the company master includes BSE URLs.")
for year in range(2024,2018,-1): st.markdown(f"**{year}** · Report unavailable")
