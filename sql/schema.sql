-- bluestock_mf.db schema
-- star schema design for mutual fund analytics
-- Day 2 | June 2026

-- drop tables if re-running
DROP TABLE IF EXISTS fact_performance;
DROP TABLE IF EXISTS fact_transactions;
DROP TABLE IF EXISTS fact_nav;
DROP TABLE IF EXISTS fact_aum;
DROP TABLE IF EXISTS fact_sip_industry;
DROP TABLE IF EXISTS fact_portfolio;
DROP TABLE IF EXISTS dim_date;
DROP TABLE IF EXISTS dim_fund;


-- dimension: fund master
CREATE TABLE dim_fund (
    amfi_code         TEXT PRIMARY KEY,
    fund_house        TEXT NOT NULL,
    scheme_name       TEXT NOT NULL,
    category          TEXT,
    sub_category      TEXT,
    plan              TEXT,
    launch_date       TEXT,
    benchmark         TEXT,
    expense_ratio_pct REAL,
    exit_load_pct     REAL,
    min_sip_amount    REAL,
    min_lumpsum_amount REAL,
    fund_manager      TEXT,
    risk_category     TEXT,
    sebi_category_code TEXT
);


-- dimension: date
-- pre-populated with all dates in the dataset range
CREATE TABLE dim_date (
    date_id    TEXT PRIMARY KEY,   -- YYYY-MM-DD
    year       INTEGER,
    month      INTEGER,
    quarter    INTEGER,
    month_name TEXT,
    is_weekday INTEGER             -- 1 = weekday, 0 = weekend
);


-- fact: daily nav per scheme
CREATE TABLE fact_nav (
    amfi_code    TEXT NOT NULL,
    nav_date     TEXT NOT NULL,
    nav          REAL NOT NULL,
    PRIMARY KEY (amfi_code, nav_date),
    FOREIGN KEY (amfi_code) REFERENCES dim_fund(amfi_code)
);


-- fact: investor transactions
CREATE TABLE fact_transactions (
    tx_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    investor_id        TEXT,
    transaction_date   TEXT,
    amfi_code          TEXT,
    transaction_type   TEXT,
    amount_inr         REAL,
    state              TEXT,
    city               TEXT,
    city_tier          TEXT,
    age_group          TEXT,
    gender             TEXT,
    annual_income_lakh REAL,
    payment_mode       TEXT,
    kyc_status         TEXT,
    FOREIGN KEY (amfi_code) REFERENCES dim_fund(amfi_code)
);


-- fact: scheme-level performance metrics
CREATE TABLE fact_performance (
    amfi_code         TEXT PRIMARY KEY,
    scheme_name       TEXT,
    fund_house        TEXT,
    category          TEXT,
    plan              TEXT,
    return_1yr_pct    REAL,
    return_3yr_pct    REAL,
    return_5yr_pct    REAL,
    benchmark_3yr_pct REAL,
    alpha             REAL,
    beta              REAL,
    sharpe_ratio      REAL,
    sortino_ratio     REAL,
    std_dev_ann_pct   REAL,
    max_drawdown_pct  REAL,
    aum_crore         REAL,
    expense_ratio_pct REAL,
    morningstar_rating INTEGER,
    risk_grade        TEXT,
    FOREIGN KEY (amfi_code) REFERENCES dim_fund(amfi_code)
);


-- fact: quarterly aum by fund house
CREATE TABLE fact_aum (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    date            TEXT,
    fund_house      TEXT,
    aum_lakh_crore  REAL,
    aum_crore       REAL,
    num_schemes     INTEGER
);


-- fact: industry-level monthly sip data
CREATE TABLE fact_sip_industry (
    month                      TEXT PRIMARY KEY,
    sip_inflow_crore           REAL,
    active_sip_accounts_crore  REAL,
    new_sip_accounts_lakh      REAL,
    sip_aum_lakh_crore         REAL,
    yoy_growth_pct             REAL
);


-- fact: portfolio holdings per fund
CREATE TABLE fact_portfolio (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    amfi_code        TEXT,
    stock_symbol     TEXT,
    stock_name       TEXT,
    sector           TEXT,
    weight_pct       REAL,
    market_value_cr  REAL,
    current_price_inr REAL,
    portfolio_date   TEXT,
    FOREIGN KEY (amfi_code) REFERENCES dim_fund(amfi_code)
);
