# Data Dictionary

This dictionary documents the cleaned data products generated for the capstone.

## Core tables

- `nav_history_cleaned.csv`: AMFI NAV history with forward-filled business dates.
- `investor_transactions_cleaned.csv`: Standardised investor transactions.
- `scheme_performance_cleaned.csv`: Scheme performance and expense ratio metrics.
- `fund_master_cleaned.csv`: Master list of funds and scheme metadata.
- `date_dimension.csv`: Date dimension for the star schema.
- `benchmark_nav_cleaned.csv`: Benchmark series for Nifty 50 and Nifty 100.
- `aum_growth_by_fund_house.csv`: AUM trend by fund house and year.
- `sip_inflows.csv`: Monthly SIP inflows.
- `category_inflows.csv`: Category-level inflow trends.
- `portfolio_holdings.csv`: Sector allocation summary for equity portfolios.

## Deliverable references

- `schema.sql`: SQLite star schema DDL.
- `queries.sql`: Analytical SQL queries.
- `bluestock_mf.db`: SQLite database populated from the cleaned CSVs.
