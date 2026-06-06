CREATE TABLE IF NOT EXISTS dim_fund (
    fund_key INTEGER PRIMARY KEY,
    amfi_code TEXT NOT NULL UNIQUE,
    scheme_name TEXT
);

CREATE TABLE IF NOT EXISTS dim_date (
    date_key INTEGER PRIMARY KEY,
    date TEXT NOT NULL UNIQUE,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    day INTEGER NOT NULL,
    quarter INTEGER NOT NULL,
    month_name TEXT NOT NULL,
    day_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_nav (
    nav_fact_key INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_key INTEGER NOT NULL,
    date_key INTEGER NOT NULL,
    amfi_code TEXT NOT NULL,
    date TEXT NOT NULL,
    nav REAL NOT NULL CHECK (nav > 0),
    FOREIGN KEY (fund_key) REFERENCES dim_fund (fund_key),
    FOREIGN KEY (date_key) REFERENCES dim_date (date_key)
);

CREATE TABLE IF NOT EXISTS fact_transactions (
    transaction_fact_key INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_key INTEGER,
    date_key INTEGER,
    amfi_code TEXT,
    date TEXT,
    transaction_type TEXT NOT NULL CHECK (transaction_type IN ('SIP', 'Lumpsum', 'Redemption')),
    amount REAL NOT NULL CHECK (amount > 0),
    kyc_status TEXT,
    state TEXT,
    city TEXT,
    FOREIGN KEY (fund_key) REFERENCES dim_fund (fund_key),
    FOREIGN KEY (date_key) REFERENCES dim_date (date_key)
);

CREATE TABLE IF NOT EXISTS fact_performance (
    performance_fact_key INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_key INTEGER,
    date_key INTEGER,
    amfi_code TEXT,
    date TEXT,
    one_year_return REAL,
    three_year_return REAL,
    five_year_return REAL,
    expense_ratio REAL CHECK (expense_ratio IS NULL OR (expense_ratio >= 0.1 AND expense_ratio <= 2.5)),
    FOREIGN KEY (fund_key) REFERENCES dim_fund (fund_key),
    FOREIGN KEY (date_key) REFERENCES dim_date (date_key)
);

CREATE TABLE IF NOT EXISTS fact_aum (
    aum_fact_key INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_key INTEGER,
    date_key INTEGER,
    amfi_code TEXT,
    date TEXT,
    aum REAL,
    FOREIGN KEY (fund_key) REFERENCES dim_fund (fund_key),
    FOREIGN KEY (date_key) REFERENCES dim_date (date_key)
);
