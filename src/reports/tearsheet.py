from __future__ import annotations
from pathlib import Path
import sqlite3
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from src.config import BASE_DIR, DB_PATH

NAVY=colors.HexColor("#102A43"); GREEN=colors.HexColor("#1B7F5A"); RED=colors.HexColor("#B42318")
def _wrap(text, style): return Paragraph(str(text), style)

def _data(db_path=DB_PATH):
    with sqlite3.connect(db_path) as c:
        companies=pd.read_sql_query("select * from companies",c); fin=pd.read_sql_query("select * from financials",c); rat=pd.read_sql_query("select * from financial_ratios",c)
    return companies,fin.merge(rat,on=["ticker","year"],how="left",suffixes=("","_r"))

def generate_tearsheet(ticker, output_path, db_path=DB_PATH, pros=None, cons=None):
    companies, data=_data(db_path); company=companies[companies.ticker==ticker].iloc[0]; h=data[data.ticker==ticker].sort_values("year"); latest=h.iloc[-1]; styles=getSampleStyleSheet(); body=ParagraphStyle("body",parent=styles["BodyText"],fontSize=8,leading=10); small=ParagraphStyle("small",parent=body,fontSize=7)
    doc=SimpleDocTemplate(str(output_path),pagesize=A4,rightMargin=14*mm,leftMargin=14*mm,topMargin=12*mm,bottomMargin=12*mm); story=[]
    header=Table([[Paragraph(f"<font color='white'><b>{company.company_name}</b><br/>{ticker} · {company.sector}</font>",styles["Title"])]],colWidths=[182*mm]); header.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),NAVY),("LEFTPADDING",(0,0),(-1,-1),10),("TOPPADDING",(0,0),(-1,-1),10),("BOTTOMPADDING",(0,0),(-1,-1),10)])); story += [header,Spacer(1,8)]
    kpis=[("ROE",latest.get("roe")),("ROCE",latest.get("roce")),("NPM",latest.get("npm")),("D/E",latest.get("debt_equity")),("FCF",latest.get("fcf")),("ICR",latest.get("interest_coverage"))]
    cards=[[Paragraph(f"<b>{k}</b><br/>{'N/A' if pd.isna(v) else f'{v:.2f}'}",body) for k,v in kpis[:3]],[Paragraph(f"<b>{k}</b><br/>{'N/A' if pd.isna(v) else f'{v:.2f}'}",body) for k,v in kpis[3:]]]
    t=Table(cards,colWidths=[60*mm]*3,rowHeights=[18*mm,18*mm]); t.setStyle(TableStyle([("GRID",(0,0),(-1,-1),.5,colors.HexColor("#D9E2EC")),("BACKGROUND",(0,0),(-1,-1),colors.HexColor("#F0F4F8")),("VALIGN",(0,0),(-1,-1),"MIDDLE")])); story += [t,Spacer(1,10),Paragraph("Revenue and net profit trend",styles["Heading2"])]
    chart_data=[["Year","Revenue","Net Profit"]]+[[str(r.year),f"{r.sales:,.0f}",f"{r.pat:,.0f}"] for _,r in h.iterrows()]; ct=Table(chart_data,colWidths=[30*mm,55*mm,55*mm]); ct.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),NAVY),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),.25,colors.lightgrey),("FONTSIZE",(0,0),(-1,-1),7)])); story.append(ct); story += [Spacer(1,8),Paragraph("Return trend",styles["Heading2"])]
    rt=Table([["Year","ROE","ROCE"]]+[[str(r.year),f"{r.roe*100:.1f}%",f"{r.roce*100:.1f}%"] for _,r in h.iterrows()],colWidths=[30*mm,55*mm,55*mm]); rt.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),NAVY),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),.25,colors.lightgrey),("FONTSIZE",(0,0),(-1,-1),7)])); story.append(rt); story.append(PageBreak())
    story += [Paragraph("Balance sheet and cash flow",styles["Heading1"])]
    bs=Table([["Year","Equity","Debt","Assets"]]+[[str(r.year),f"{r.equity:,.0f}",f"{r.debt:,.0f}",f"{r.assets:,.0f}"] for _,r in h.iterrows()],colWidths=[30*mm,45*mm,45*mm,45*mm]); bs.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),NAVY),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),.25,colors.lightgrey),("FONTSIZE",(0,0),(-1,-1),7)])); story += [bs,Spacer(1,10),Paragraph("Latest cash flow",styles["Heading2"]),Table([["CFO","CapEx","CFF","Net cash flow"],[f"{latest.cfo:,.0f}",f"{-latest.capex:,.0f}","N/A",f"{latest.cfo-latest.capex:,.0f}"]],colWidths=[45*mm]*4),Spacer(1,12),Paragraph("Pros",styles["Heading2"])]
    for text in pros or ["Financial history is available for review."]: story.append(_wrap(f"<font color='#1B7F5A'>• {text}</font>",body))
    story.append(Paragraph("Cons",styles["Heading2"]))
    for text in cons or ["Monitor the company as additional enriched metrics become available."]: story.append(_wrap(f"<font color='#B42318'>• {text}</font>",body))
    story.append(Spacer(1,8)); story.append(Paragraph("Capital allocation: Balanced",body)); doc.build(story)

def batch_generate(db_path=DB_PATH, output_dir=None, pros_cons_path=None):
    output_dir=Path(output_dir or BASE_DIR/"reports"/"tearsheets"); output_dir.mkdir(parents=True,exist_ok=True); companies,_=_data(db_path); pc=pd.read_csv(pros_cons_path) if pros_cons_path and Path(pros_cons_path).exists() else pd.DataFrame()
    skipped=[]
    for ticker in companies.ticker:
        if len(_data(db_path)[1].query("ticker == @ticker"))<3: skipped.append({"company_id":ticker,"reason":"fewer than 3 years of data"}); continue
        p=pc[(pc.company_id==ticker)&(pc.type=="pro")].text.tolist() if not pc.empty else []; c=pc[(pc.company_id==ticker)&(pc.type=="con")].text.tolist() if not pc.empty else []
        generate_tearsheet(ticker,output_dir/f"{ticker}_tearsheet.pdf",db_path,p,c)
    pd.DataFrame(skipped).to_csv(BASE_DIR/"output"/"skipped_tearsheets.csv",index=False)
    return output_dir

if __name__ == "__main__": batch_generate(pros_cons_path=BASE_DIR/"output"/"pros_cons_generated.csv")
