from __future__ import annotations

import pandas as pd
import sqlite3
from pathlib import Path
from src.config import BASE_DIR, DB_PATH


def compute_cashflow_kpis(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["fcf"] = out["cfo"] - out["capex"]
    out["cfo_quality_score"] = out.apply(lambda r: None if r["pat"] == 0 else r["cfo"] / r["pat"], axis=1)
    out["capex_intensity"] = out.apply(lambda r: None if r["sales"] == 0 else r["capex"] / r["sales"], axis=1)
    out["fcf_conversion"] = out.apply(lambda r: None if r["cfo"] == 0 else r["fcf"] / r["cfo"], axis=1)
    out["capital_allocation_class"] = pd.cut(
        out["fcf"],
        bins=[float("-inf"), 0, 1, 10, float("inf")],
        labels=["distress", "tight", "balanced", "cash-rich"],
    ).astype(str)
    return out

def build_cashflow_intelligence(db_path=DB_PATH, output_dir=None):
    output_dir=Path(output_dir or BASE_DIR/"output"); output_dir.mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        companies=pd.read_sql_query("select * from companies",conn)
        fin=pd.read_sql_query("select * from financials",conn)
        rat=pd.read_sql_query("select * from financial_ratios",conn)
    df=fin.merge(companies[["ticker","sector","is_bank"]],on="ticker",how="left").merge(rat,on=["ticker","year"],how="left",suffixes=("","_ratio"))
    df["cff"]=df.get("cff",0); df["investing_activity"]=df.get("investing_activity",-df["capex"]); df["fcf"]=df["cfo"]-df["capex"]
    df["cfo_ratio"]=df["cfo"]/df["pat"].replace(0,pd.NA); df["capex_intensity_pct"]=df["investing_activity"].abs()/df["sales"].replace(0,pd.NA)*100
    latest=df.sort_values("year").groupby("ticker").tail(1); avg=df.sort_values("year").groupby("ticker").tail(5).groupby("ticker")["cfo_ratio"].mean()
    rows=[]
    for _,r in latest.iterrows():
        t=r.ticker; score=float(avg.get(t,0) if pd.notna(avg.get(t,0)) else 0); intensity=float(r.capex_intensity_pct if pd.notna(r.capex_intensity_pct) else 0)
        cfo_label="High Quality" if score>1 else "Moderate" if score>=.5 else "Accrual Risk"; capex_label="Asset Light" if intensity<3 else "Moderate" if intensity<=8 else "Capital Intensive"
        history=df[df.ticker==t].sort_values("year"); prev=history.iloc[-2] if len(history)>1 else r
        rows.append({"company_id":t,"sector":r.sector,"cfo_quality_score":score,"cfo_quality_label":cfo_label,"capex_intensity_pct":intensity,"capex_label":capex_label,"fcf_cagr_5yr":None,"fcf_conversion_pct":(r.fcf/r.cfo*100 if r.cfo else None),"distress_flag":bool(r.cfo<0 and r.cff>0),"deleveraging_flag":bool(r.cff<0 and r.debt<prev.debt),"capital_allocation_label":r.get("capital_allocation_class","Balanced")})
    out=pd.DataFrame(rows); out.to_excel(output_dir/"cashflow_intelligence.xlsx",index=False)
    alerts=latest[(latest.cfo<0)&(latest.cff>0)][["ticker","cfo","cff","pat"]].rename(columns={"ticker":"company_id","pat":"latest_net_profit"}); alerts.to_csv(output_dir/"distress_alerts.csv",index=False)
    return out

def build_capital_allocation_reports(db_path=DB_PATH, output_dir=None):
    output_dir=Path(output_dir or BASE_DIR/"output"); output_dir.mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        companies=pd.read_sql_query("select * from companies",conn); ratios=pd.read_sql_query("select * from financial_ratios",conn)
    ratios["capital_allocation_label"]=ratios["capital_allocation_class"].fillna("balanced") if "capital_allocation_class" in ratios else "balanced"
    latest=ratios.sort_values("year").groupby("ticker").tail(1); latest.merge(companies[["ticker","company_name"]],on="ticker",how="left").groupby("capital_allocation_label").size().rename("company_count").reset_index().to_csv(output_dir/"capital_allocation_distribution.csv",index=False)
    ordered=ratios.sort_values(["ticker","year"]); ordered["previous_pattern"]=ordered.groupby("ticker")["capital_allocation_label"].shift(1); changes=ordered[ordered["previous_pattern"].notna() & (ordered.capital_allocation_label!=ordered.previous_pattern)][["ticker","year","previous_pattern","capital_allocation_label"]].rename(columns={"ticker":"company_id","capital_allocation_label":"new_pattern"}); changes.to_csv(output_dir/"pattern_changes.csv",index=False); return changes

if __name__ == "__main__": build_cashflow_intelligence()
