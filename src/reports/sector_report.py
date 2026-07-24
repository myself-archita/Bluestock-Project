from __future__ import annotations
from pathlib import Path
import sqlite3
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle
from reportlab.lib import colors
from src.config import BASE_DIR, DB_PATH

def generate_sector_reports(db_path=DB_PATH, output_dir=None):
    output_dir=Path(output_dir or BASE_DIR/"reports"/"sector"); output_dir.mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(db_path) as c: df=pd.read_sql_query("select c.company_name,c.ticker,c.sector,r.roe,r.roce,r.npm,r.debt_equity,r.fcf from companies c left join financial_ratios r on c.ticker=r.ticker and r.year=(select max(year) from financial_ratios)",c)
    for sector,g in df.groupby("sector"):
        doc=SimpleDocTemplate(str(output_dir/f"{sector}_report.pdf"),pagesize=A4); story=[Paragraph(f"<b>{sector} sector report</b>",__import__('reportlab.lib.styles',fromlist=['getSampleStyleSheet']).getSampleStyleSheet()["Title"])]
        story.append(Table([["Ticker","Company","ROE","ROCE","NPM","D/E","FCF"]]+g.fillna("N/A").astype(str).values.tolist(),repeatRows=1,style=TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#102A43")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),.25,colors.lightgrey),("FONTSIZE",(0,0),(-1,-1),7)]))); doc.build(story)
    return output_dir
