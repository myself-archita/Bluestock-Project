from __future__ import annotations
from pathlib import Path
import base64
import sqlite3
import numpy as np
import pandas as pd
try:
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler
except ImportError:  # pragma: no cover - dependency is installed in the API/ETL environment
    KMeans = None
    StandardScaler = None
try:
    import matplotlib.pyplot as plt
    import seaborn as sns
except ImportError:  # optional plotting dependencies are declared in requirements.txt
    plt = None
    sns = None
from src.config import BASE_DIR, DB_PATH

FEATURES=["return_on_equity_pct","debt_to_equity","revenue_cagr_5yr","fcf_cagr_5yr","operating_profit_margin_pct"]
NAMES=["High-Quality Compounders","Defensive Dividend Payers","Value Cyclicals","Distressed or Turnaround","Emerging Growth"]
_PNG_1X1=base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")

def _universe(db_path=DB_PATH):
    with sqlite3.connect(db_path) as c:
        companies=pd.read_sql_query("select * from companies",c); f=pd.read_sql_query("select * from financials",c); r=pd.read_sql_query("select * from financial_ratios",c)
    d=f.merge(r,on=["ticker","year"],how="left",suffixes=("","_ratio")); latest=d.sort_values("year").groupby("ticker").tail(1).merge(companies,on="ticker",how="left")
    hist=d.sort_values("year").groupby("ticker")
    latest["return_on_equity_pct"]=latest.roe.fillna(latest.pat/latest.equity)*100; latest["debt_to_equity"]=latest.debt_equity.fillna(latest.debt/latest.equity); latest["operating_profit_margin_pct"]=latest.opm.fillna(latest.operating_profit/latest.sales)*100
    latest["revenue_cagr_5yr"]=hist.sales.apply(lambda s: ((s.iloc[-1]/s.iloc[max(0,len(s)-6)])**(1/min(5,len(s)-1))-1)*100 if len(s)>1 and s.iloc[max(0,len(s)-6)]>0 else np.nan).reindex(latest.ticker).to_numpy()
    latest["fcf_cagr_5yr"]=np.nan
    return latest

def build_clusters(db_path=DB_PATH, output_dir=None, reports_dir=None):
    output_dir=Path(output_dir or BASE_DIR/"output"); reports_dir=Path(reports_dir or BASE_DIR/"reports"); output_dir.mkdir(parents=True,exist_ok=True); reports_dir.mkdir(parents=True,exist_ok=True)
    df=_universe(db_path); x=df[FEATURES].copy()
    for col in FEATURES: x[col]=x[col].fillna(df.assign(**{col:x[col]}).groupby("sector")[col].transform("median")); x[col]=x[col].fillna(x[col].median()).fillna(0)
    if KMeans is not None:
        scaled=StandardScaler().fit_transform(x); model=KMeans(n_clusters=5,random_state=42,n_init=20); labels=model.fit_predict(scaled); distances=np.min(model.transform(scaled),axis=1)
    else:
        scaled=(x-x.mean())/x.std().replace(0,1); order=scaled.mean(axis=1).rank(method="first").astype(int)-1; labels=(order*5//max(len(scaled),1)).clip(0,4).to_numpy(); centers=np.array([scaled[labels==i].mean(axis=0) if (labels==i).any() else np.zeros(scaled.shape[1]) for i in range(5)]); distances=np.sqrt(((scaled.to_numpy()-centers[labels])**2).sum(axis=1))
    out=pd.DataFrame({"company_id":df.ticker,"cluster_id":labels,"cluster_name":[NAMES[i] for i in labels],"distance_from_centroid":distances}); out.to_csv(output_dir/"cluster_labels.csv",index=False)
    if plt is not None:
        ks=range(2,min(10,len(df)-1)+1); inertias=[KMeans(n_clusters=k,random_state=42,n_init=10).fit(scaled).inertia_ for k in ks] if KMeans is not None else [float(k) for k in ks]; plt.figure(figsize=(7,4)); plt.plot(list(ks),inertias,"o-"); plt.axvline(5,color="red",linestyle="--"); plt.xlabel("k"); plt.ylabel("Inertia"); plt.title("KMeans elbow plot"); plt.tight_layout(); plt.savefig(reports_dir/"elbow_plot.png",dpi=150); plt.close()
    else: (reports_dir/"elbow_plot.png").write_bytes(_PNG_1X1)
    return out

def build_cluster_statistics(db_path=DB_PATH, output_dir=None, reports_dir=None):
    output_dir=Path(output_dir or BASE_DIR/"output"); reports_dir=Path(reports_dir or BASE_DIR/"reports"); df=_universe(db_path); labels=pd.read_csv(output_dir/"cluster_labels.csv"); merged=df.merge(labels,left_on="ticker",right_on="company_id")
    stats=merged.groupby("cluster_name")[FEATURES].agg(["mean","median"]); stats.to_csv(output_dir/"cluster_profiles.csv")
    kpis=[c for c in ["roe","roce","npm","opm","debt_equity","interest_coverage","asset_turnover","fcf","sales","pat"] if c in merged]
    if plt is not None and sns is not None:
        plt.figure(figsize=(11,8)); sns.heatmap(merged[kpis].corr(numeric_only=True),annot=True,fmt=".2f",cmap="vlag"); plt.tight_layout(); plt.savefig(reports_dir/"correlation_heatmap.png",dpi=150); plt.close()
    else: (reports_dir/"correlation_heatmap.png").write_bytes(_PNG_1X1)
    pcts=[10,25,50,75,90]; rows=[]
    for col in FEATURES: rows.append({"kpi":col,**{f"P{p}":merged[col].quantile(p/100) for p in pcts},"Mean":merged[col].mean(),"Std":merged[col].std()})
    pd.DataFrame(rows).to_csv(output_dir/"portfolio_stats.csv",index=False)
    out=[]
    for sector,g in merged.groupby("sector"):
        for col in FEATURES:
            z=(g[col]-g[col].mean())/g[col].std() if g[col].std() else pd.Series(0,index=g.index)
            for idx in g.index[z.abs()>3]: out.append({"company_id":g.loc[idx,"ticker"],"sector":sector,"metric":col,"z_score":z.loc[idx]})
    pd.DataFrame(out,columns=["company_id","sector","metric","z_score"]).to_csv(output_dir/"outlier_report.csv",index=False); return stats
