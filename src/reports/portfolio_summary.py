from __future__ import annotations
from pathlib import Path
import sqlite3
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, PageBreak, Table, TableStyle
from reportlab.lib import colors
from src.config import BASE_DIR, DB_PATH

def generate_portfolio_summary(db_path=DB_PATH, output_path=None):
    output_path=Path(output_path or BASE_DIR/"reports"/"portfolio"/"portfolio_summary.pdf"); output_path.parent.mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(db_path) as c: df=pd.read_sql_query("select c.company_name,c.ticker,c.sector,r.year,r.roe,r.roce,r.npm,r.debt_equity,r.fcf,r.interest_coverage from companies c left join financial_ratios r on c.ticker=r.ticker",c)
    doc=SimpleDocTemplate(str(output_path),pagesize=A4); story=[]
    for ticker,g in df.sort_values("ticker").groupby("ticker"):
        latest=g.sort_values("year").iloc[-1]; previous=g.sort_values("year").iloc[-2] if len(g)>1 else latest
        def arrow(col):
            a,b=previous.get(col),latest.get(col)
            if pd.isna(a) or pd.isna(b) or a==0: return "→"
            return "↑" if b>a*1.02 else "↓" if b<a*.98 else "→"
        story.append(Paragraph(f"<font color='#102A43'><b>{latest.company_name}</b> · {ticker}</font><br/>{latest.sector}",__import__('reportlab.lib.styles',fromlist=['getSampleStyleSheet']).getSampleStyleSheet()["Title"]))
        rows=[["KPI","Value","Trend"],["ROE",latest.get("roe"),arrow("roe")],["ROCE",latest.get("roce"),arrow("roce")],["NPM",latest.get("npm"),arrow("npm")],["D/E",latest.get("debt_equity"),arrow("debt_equity")],["FCF",latest.get("fcf"),arrow("fcf")],["ICR",latest.get("interest_coverage"),arrow("interest_coverage")]]
        story.append(Table(rows,style=TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#102A43")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),.25,colors.lightgrey)]))); story.append(PageBreak())
    doc.build(story); return output_path
