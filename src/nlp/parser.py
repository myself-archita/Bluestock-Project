from __future__ import annotations
import re
from pathlib import Path
import pandas as pd
from src.config import BASE_DIR

PATTERN = re.compile(r"(\d+)\s*Years?:?\s*([\d.]+)%", re.I)
TARGETS = {"compounded_sales_growth", "compounded_profit_growth", "stock_price_cagr", "roe"}

def parse_analysis(path=None, output_dir=None):
    path = Path(path or BASE_DIR / "data" / "raw" / "analysis.xlsx")
    output_dir = Path(output_dir or BASE_DIR / "output"); output_dir.mkdir(parents=True, exist_ok=True)
    parsed, failures = [], []
    if path.exists():
        source = pd.read_excel(path)
        id_col = next((c for c in ["company_id", "ticker", "company_code"] if c in source.columns), source.columns[0])
        for _, row in source.iterrows():
            for metric in TARGETS:
                if metric not in source.columns or pd.isna(row.get(metric)): continue
                text = str(row[metric]); match = PATTERN.search(text)
                if match:
                    parsed.append({"company_id": row[id_col], "metric_type": metric, "period_years": int(match.group(1)), "value_pct": float(match.group(2))})
                else: failures.append({"company_id": row[id_col], "metric_type": metric, "raw_text": text})
    parsed_df = pd.DataFrame(parsed, columns=["company_id","metric_type","period_years","value_pct"])
    failed_df = pd.DataFrame(failures, columns=["company_id","metric_type","raw_text"])
    parsed_df.to_csv(output_dir / "analysis_parsed.csv", index=False); failed_df.to_csv(output_dir / "parse_failures.csv", index=False)
    return parsed_df, failed_df

if __name__ == "__main__": parse_analysis()
