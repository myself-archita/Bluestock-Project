from pathlib import Path
import streamlit as st

st.set_page_config(page_title="Nifty 100 Analytics", page_icon="📈", layout="wide", initial_sidebar_state="expanded")
st.sidebar.title("Nifty 100 Analytics")
pages = Path(__file__).parent / "pages"
items = [st.Page(str(pages / f"{i:02d}_{name}.py"), title=title) for i, name, title in [(1,"home","Home"),(2,"profile","Company Profile"),(3,"screener","Screener"),(4,"peers","Peer Comparison"),(5,"trends","Trend Analysis"),(6,"sectors","Sector Analysis"),(7,"capital","Capital Allocation"),(8,"reports","Annual Reports")]]
st.navigation(items).run()
