from __future__ import annotations
import sqlite3
import time
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from src.config import DB_PATH, BASE_DIR

START=time.time(); VERSION="1.0.0"
app=FastAPI(title="Nifty 100 Financial Intelligence API",version=VERSION,description="Analytics API for the Nifty 100 dashboard")
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_methods=["*"],allow_headers=["*"])

@app.middleware("http")
async def request_logger(request:Request,call_next):
    started=time.perf_counter(); response=await call_next(request); response.headers["X-Response-Time-ms"]=f"{(time.perf_counter()-started)*1000:.2f}"; return response

def rows(sql,params=()):
    with sqlite3.connect(DB_PATH) as c:
        c.row_factory=sqlite3.Row; return [dict(r) for r in c.execute(sql,params).fetchall()]
def frame(sql,params=()):
    import pandas as pd
    with sqlite3.connect(DB_PATH) as c: return pd.read_sql_query(sql,c,params=params)
def latest_metrics():
    return frame("select r.*,f.sales,f.pat,f.equity,f.debt,f.cfo,f.capex,f.eps,c.company_name,c.sector,c.industry from financial_ratios r join financials f using(ticker,year) join companies c using(ticker) where r.year=(select max(year) from financial_ratios)")

@app.get("/api/v1/health")
def health():
    known=["companies","financials","financial_ratios","peer_percentiles","market_cap","capital_allocation","documents","sectors","valuation","analysis"]
    counts={t:0 for t in known}
    with sqlite3.connect(DB_PATH) as c:
        actual={r[0] for r in c.execute("select name from sqlite_master where type='table'")}
        for t in actual:
            counts[t]=c.execute(f"select count(*) from [{t}]").fetchone()[0]
    return {"status":"ok","db_row_counts":counts,"uptime_seconds":round(time.time()-START,3),"version":VERSION}

@app.get("/api/v1/companies")
def list_companies(sector:str|None=None,market_cap_category:str|None=None,search:str|None=None):
    df=latest_metrics();
    if sector: df=df[df.sector.str.casefold()==sector.casefold()]
    if search: df=df[df.company_name.str.contains(search,case=False,na=False)|df.ticker.str.contains(search,case=False,na=False)]
    cols=["ticker","company_name","sector","industry","roe","roce"]; return df.rename(columns={"ticker":"id","sector":"broad_sector","roe":"roe_pct","roce":"roce_pct"})[["id","company_name","broad_sector","industry","roe_pct","roce_pct"]].fillna("N/A").to_dict("records")

@app.get("/api/v1/companies/{ticker}")
def company(ticker:str):
    t=ticker.upper(); c=rows("select * from companies where ticker=?",(t,));
    if not c: raise HTTPException(404,"Ticker not found")
    latest=rows("select r.*,f.sales,f.pat,f.equity,f.debt,f.cfo,f.capex,f.eps from financial_ratios r join financials f using(ticker,year) where r.ticker=? order by year desc limit 1",(t,)); return {**c[0],"latest_kpis":latest[0] if latest else {}}

def history(ticker,table,from_year,to_year,cols="*"):
    if not rows("select 1 from companies where ticker=?",(ticker,)): raise HTTPException(404,"Ticker not found")
    sql=f"select {cols} from {table} where ticker=?"; params=[ticker]
    if from_year: sql+=" and year>=?"; params.append(int(from_year[:4]))
    if to_year: sql+=" and year<=?"; params.append(int(to_year[:4]))
    return rows(sql+" order by year",tuple(params))
@app.get("/api/v1/companies/{ticker}/pl")
def company_pl(ticker:str,from_year:str|None=None,to_year:str|None=None): return {"ticker":ticker.upper(),"history":history(ticker.upper(),"financials",from_year,to_year,"ticker,year,sales,operating_profit,pat,eps")}
@app.get("/api/v1/companies/{ticker}/bs")
def company_bs(ticker:str,from_year:str|None=None,to_year:str|None=None): return {"ticker":ticker.upper(),"history":history(ticker.upper(),"financials",from_year,to_year,"ticker,year,equity,debt,assets")}
@app.get("/api/v1/companies/{ticker}/cashflow")
def company_cashflow(ticker:str,from_year:str|None=None,to_year:str|None=None): return {"ticker":ticker.upper(),"history":history(ticker.upper(),"financials",from_year,to_year,"ticker,year,cfo,capex")}
@app.get("/api/v1/companies/{ticker}/ratios")
def company_ratios(ticker:str,year:int|None=None):
    if not rows("select 1 from companies where ticker=?",(ticker.upper(),)): raise HTTPException(404,"Ticker not found")
    return {"ticker":ticker.upper(),"ratios":rows("select * from financial_ratios where ticker=?"+ (" and year=?" if year else "")+" order by year",(ticker.upper(),year) if year else (ticker.upper(),))}
@app.get("/api/v1/companies/{ticker}/tearsheet")
def company_tearsheet(ticker:str):
    path=BASE_DIR/"reports"/"tearsheets"/f"{ticker.upper()}_tearsheet.pdf";
    if not path.exists(): raise HTTPException(404,"Tearsheet unavailable")
    return FileResponse(path,media_type="application/pdf",filename=path.name)

@app.get("/api/v1/screener")
def screener(min_roe:float|None=None,max_de:float|None=None,min_fcf:float|None=None,sector:str|None=None,min_rev_cagr_5yr:float|None=None,min_pat_cagr_5yr:float|None=None,max_pe:float|None=None):
    for value in [min_roe,min_fcf,min_rev_cagr_5yr,min_pat_cagr_5yr,max_de,max_pe]:
        if value is not None and not isinstance(value,(int,float)): raise HTTPException(400,"Invalid parameter")
    d=latest_metrics(); d["roe"]=d.roe.fillna(d.pat/d.equity); d["fcf"]=d.cfo-d.capex; d["debt_equity"]=d.debt/d.equity
    if min_roe is not None:d=d[d.roe*100>=min_roe]
    if max_de is not None:d=d[d.debt_equity<=max_de]
    if min_fcf is not None:d=d[d.fcf>=min_fcf]
    if sector:d=d[d.sector.str.casefold()==sector.casefold()]
    return d.sort_values("roe",ascending=False).fillna("N/A").to_dict("records")
@app.get("/api/v1/sectors")
def sectors():
    d=latest_metrics(); return d.groupby("sector").agg(company_count=("ticker","count"),median_roe=("roe","median"),median_de=("debt_equity","median")).reset_index().rename(columns={"sector":"broad_sector"}).fillna("N/A").to_dict("records")
@app.get("/api/v1/sectors/{sector}/companies")
def sector_companies(sector:str):
    d=latest_metrics(); d=d[d.sector.str.casefold()==sector.casefold()]
    if d.empty: raise HTTPException(404,"Unknown sector")
    return d.fillna("N/A").to_dict("records")
@app.get("/api/v1/peers/{group_name}")
def peers(group_name:str):
    d=rows("select * from peer_percentiles where lower(peer_group)=lower(?)",(group_name,))
    if not d:
        d=latest_metrics(); d=d[d.sector.str.casefold()==group_name.casefold()].to_dict("records")
    if not d: raise HTTPException(404,"Unknown peer group")
    return {"peer_group":group_name,"companies":d}
@app.get("/api/v1/companies/{ticker}/peers/compare")
def peer_compare(ticker:str):
    d=latest_metrics(); row=d[d.ticker==ticker.upper()]
    if row.empty: raise HTTPException(404,"Ticker not found")
    metrics=["roe","roce","npm","opm","debt_equity","interest_coverage","asset_turnover","fcf"]; peer=d[d.sector==row.iloc[0].sector]
    return {"ticker":ticker.upper(),"axes":[{"metric":m,"company":row.iloc[0].get(m),"peer_average":peer[m].mean() if m in peer else None} for m in metrics],"benchmark_company":peer.iloc[0].ticker}
@app.get("/api/v1/market-cap/{ticker}")
def market_cap(ticker:str): return {"ticker":ticker.upper(),"history":rows("select year,eps from financials where ticker=? and year between 2019 and 2024 order by year",(ticker.upper(),))}
@app.get("/api/v1/portfolio/stats")
def portfolio_stats():
    d=latest_metrics(); cols=[c for c in ["roe","roce","npm","debt_equity","interest_coverage","asset_turnover","fcf"] if c in d]; return [{"kpi":c,**{f"P{p}":d[c].quantile(p/100) for p in [10,25,50,75,90]}} for c in cols]
@app.get("/api/v1/companies/{ticker}/documents")
def documents(ticker:str):
    if not rows("select 1 from companies where ticker=?",(ticker.upper(),)): raise HTTPException(404,"Ticker not found")
    return {"ticker":ticker.upper(),"documents":[]}
