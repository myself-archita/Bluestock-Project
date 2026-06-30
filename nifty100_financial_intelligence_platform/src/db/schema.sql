CREATE TABLE IF NOT EXISTS companies (
    ticker TEXT PRIMARY KEY,
    company_name TEXT NOT NULL,
    sector TEXT NOT NULL,
    industry TEXT,
    is_bank INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS financials (
    ticker TEXT NOT NULL,
    year INTEGER NOT NULL,
    sales REAL,
    operating_profit REAL,
    pat REAL,
    equity REAL,
    debt REAL,
    assets REAL,
    cfo REAL,
    capex REAL,
    eps REAL,
    revenue_cagr_5y REAL,
    pat_cagr_5y REAL,
    eps_cagr_5y REAL,
    PRIMARY KEY (ticker, year),
    FOREIGN KEY (ticker) REFERENCES companies(ticker)
);

CREATE TABLE IF NOT EXISTS financial_ratios (
    ticker TEXT NOT NULL,
    year INTEGER NOT NULL,
    npm REAL,
    opm REAL,
    roe REAL,
    roce REAL,
    debt_equity REAL,
    interest_coverage REAL,
    asset_turnover REAL,
    fcf REAL,
    cfo_quality_score REAL,
    capex_intensity REAL,
    fcf_conversion REAL,
    capital_allocation_class TEXT,
    PRIMARY KEY (ticker, year),
    FOREIGN KEY (ticker) REFERENCES companies(ticker)
);

CREATE TABLE IF NOT EXISTS peer_percentiles (
    ticker TEXT NOT NULL,
    peer_group TEXT NOT NULL,
    metric TEXT NOT NULL,
    percentile REAL NOT NULL,
    PRIMARY KEY (ticker, peer_group, metric)
);
