from __future__ import annotations
from pathlib import Path
import sqlite3
import numpy as np
import pandas as pd
from src.config import BASE_DIR, DB_PATH

PROS = {
"P1": ("Consistently high return on equity above 20% demonstrates exceptional capital efficiency", lambda h,l: (len(h)>=3 and h.roe.tail(3).min()>0.20, 92)),
"P2": ("Strong free cash flow generation over 5 years signals healthy business fundamentals", lambda h,l: (len(h)>=5 and (h.fcf.tail(5)>0).all(), 90)),
"P3": ("Debt-free balance sheet provides financial flexibility and eliminates interest burden", lambda h,l: (l.debt_equity<=0.001, 88)),
"P4": ("Revenue growing at above 15% CAGR over 5 years reflects strong business momentum", lambda h,l: (getattr(l,"revenue_cagr_5y",0)>0.15, 86)),
"P5": ("Operating profit margin above 25% indicates strong pricing power and cost discipline", lambda h,l: (l.opm>0.25, 84)),
"P6": ("Net profit compounding at above 20% over 5 years creates significant shareholder value", lambda h,l: (getattr(l,"pat_cagr_5y",0)>0.20, 83)),
"P7": ("Very high interest coverage ratio reflects negligible financial stress from debt servicing", lambda h,l: (l.interest_coverage>10 or l.debt_equity<=0.001, 82)),
"P8": ("Consistent dividend yield above 2% backed by positive free cash flow", lambda h,l: (getattr(l,"dividend_yield",0)>0.02 and l.fcf>0, 78)),
"P9": ("Earnings per share growing above 15% CAGR indicates strong earnings quality and compounding", lambda h,l: (getattr(l,"eps_cagr_5y",0)>0.15, 81)),
"P10": ("Return on equity improving for 3 consecutive years shows strengthening business quality", lambda h,l: (len(h)>=3 and h.roe.tail(3).is_monotonic_increasing, 80)),
"P11": ("Revenue growing slower than profits shows improving operating leverage and scale benefits", lambda h,l: (getattr(l,"revenue_cagr_5y",0)<getattr(l,"pat_cagr_5y",0), 76)),
"P12": ("Growing asset base funded by internal accruals reflects self-sustaining growth", lambda h,l: (len(h)>=2 and h.assets.iloc[-1]>h.assets.iloc[0] and h.debt.iloc[-1]<=h.debt.iloc[0], 75)),
}
CONS = {
"C1": ("Debt-to-equity ratio of {x:.1f} is elevated for a non-financial company and warrants monitoring", lambda h,l: (l.debt_equity>2, 92)),
"C2": ("Free cash flow negative for 3 consecutive years raises concern about cash generation quality", lambda h,l: (len(h)>=3 and (h.fcf.tail(3)<0).all(), 90)),
"C3": ("Operating margins declining for 3 consecutive years suggest pricing or cost pressure", lambda h,l: (len(h)>=3 and h.opm.tail(3).is_monotonic_decreasing, 86)),
"C4": ("Company reported a net loss in the most recent financial year", lambda h,l: (l.pat<0, 94)),
"C5": ("Revenue contraction over 2 consecutive years indicates demand weakness or market share loss", lambda h,l: (len(h)>=3 and h.sales.tail(3).is_monotonic_decreasing, 85)),
"C6": ("Interest coverage ratio below 1.5x indicates the company is at risk of not meeting its debt obligations", lambda h,l: (l.interest_coverage<1.5, 91)),
"C7": ("Dividend payout ratio above 100% means the company is paying dividends from reserves, which is unsustainable", lambda h,l: (getattr(l,"dividend_payout",0)>1, 88)),
"C8": ("Rising debt-to-equity ratio over 3 years suggests increasing financial leverage risk", lambda h,l: (len(h)>=3 and h.debt_equity.tail(3).is_monotonic_increasing, 84)),
"C9": ("Earnings per share declining for 3 consecutive years reflects deteriorating profitability", lambda h,l: (len(h)>=3 and h.eps.tail(3).is_monotonic_decreasing, 86)),
"C10": ("Return on capital employed below 10% suggests the business is not generating sufficient returns on invested capital", lambda h,l: (l.roce<0.10, 83)),
"C11": ("Net debt exceeding 3 times EBITDA is a high leverage ratio and limits financial flexibility", lambda h,l: (l.debt>3*l.operating_profit, 89)),
"C12": ("Revenue growing at below 5% over 5 years lags inflation and suggests limited business momentum", lambda h,l: (getattr(l,"revenue_cagr_5y",0)<0.05, 80)),
}

def generate(db_path=DB_PATH, output_dir=None):
    output_dir=Path(output_dir or BASE_DIR/"output"); output_dir.mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(db_path) as c:
        companies=pd.read_sql_query("select * from companies",c); fin=pd.read_sql_query("select * from financials",c); rat=pd.read_sql_query("select * from financial_ratios",c)
    rat=rat.merge(fin[["ticker","year","sales","pat","eps","assets","debt"]],on=["ticker","year"],how="left")
    rows=[]
    for ticker in companies.ticker:
        h=rat[rat.ticker==ticker].sort_values("year"); l=h.iloc[-1] if not h.empty else pd.Series(dtype=float)
        for typ,rules in [("pro",PROS),("con",CONS)]:
            matched=False
            for rule,(template,fn) in rules.items():
                try: ok,score=fn(h,l)
                except Exception: ok,score=False,0
                if ok and score>60: rows.append({"company_id":ticker,"type":typ,"rule_id":rule,"text":template.format(x=float(l.get("debt_equity",0))),"confidence_pct":score}); matched=True; break
            if not matched:
                fallback = "Available financial history supports continued monitoring of operating quality." if typ=="pro" else "Some financial metrics require monitoring as the company history is incomplete."
                rows.append({"company_id":ticker,"type":typ,"rule_id":"FALLBACK","text":fallback,"confidence_pct":61})
    out=pd.DataFrame(rows,columns=["company_id","type","rule_id","text","confidence_pct"]); out.to_csv(output_dir/"pros_cons_generated.csv",index=False); return out

if __name__ == "__main__": generate()
