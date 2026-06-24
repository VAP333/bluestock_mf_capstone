# Data Dictionary
Bluestock Fintech Capstone | June 2026

All tables in bluestock_mf.db. Source CSVs are in data/raw/, cleaned versions in data/processed/.

---

## dim_fund
Master list of 40 mutual fund schemes.
Source: `01_fund_master.csv` | AMFI India

| Column | Type | Description |
|--------|------|-------------|
| amfi_code | TEXT (PK) | Unique AMFI scheme code e.g. 125497 |
| fund_house | TEXT | AMC name e.g. SBI Mutual Fund |
| scheme_name | TEXT | Full official AMFI scheme name |
| category | TEXT | Equity / Debt / Hybrid |
| sub_category | TEXT | Large Cap / Mid Cap / Small Cap / Liquid etc. |
| plan | TEXT | Regular or Direct |
| launch_date | TEXT | Fund launch date YYYY-MM-DD |
| benchmark | TEXT | Official benchmark index |
| expense_ratio_pct | REAL | Annual expense ratio in % (0.1 - 2.5) |
| exit_load_pct | REAL | Exit load % (0 for Liquid/Index funds) |
| min_sip_amount | REAL | Minimum SIP investment in Rs. |
| min_lumpsum_amount | REAL | Minimum lumpsum investment in Rs. |
| fund_manager | TEXT | Primary fund manager name |
| risk_category | TEXT | SEBI risk label: Low / Moderate / High / Very High |
| sebi_category_code | TEXT | Internal SEBI code e.g. EC01 = Large Cap |

---

## dim_date
Date dimension pre-populated Jan 2022 to Dec 2026.
Source: generated during ETL

| Column | Type | Description |
|--------|------|-------------|
| date_id | TEXT (PK) | Date in YYYY-MM-DD format |
| year | INTEGER | Calendar year |
| month | INTEGER | Month number 1-12 |
| quarter | INTEGER | Quarter number 1-4 |
| month_name | TEXT | Full month name e.g. January |
| is_weekday | INTEGER | 1 if weekday, 0 if weekend |

---

## fact_nav
Daily NAV for all 40 schemes from Jan 2022 to May 2026.
Source: `02_nav_history.csv` | mfapi.in
~46,000 rows (1,150 trading days x 40 schemes)

| Column | Type | Description |
|--------|------|-------------|
| amfi_code | TEXT (FK) | References dim_fund |
| nav_date | TEXT | Business date of NAV in YYYY-MM-DD |
| nav | REAL | Net Asset Value in Rs. e.g. 892.45 |

Notes: NAV is only published on trading days (weekdays excluding NSE holidays).
Missing dates were forward-filled during cleaning. NAV > 0 validated.

---

## fact_transactions
Investor-level SIP, Lumpsum, and Redemption transactions.
Source: `08_investor_transactions.csv` | synthetic, realistic distributions
~32,778 rows covering 5,000 investors across 12 Indian states

| Column | Type | Description |
|--------|------|-------------|
| tx_id | INTEGER (PK) | Auto-incremented transaction ID |
| investor_id | TEXT | Unique investor ID e.g. INV003054 |
| transaction_date | TEXT | Date of transaction YYYY-MM-DD |
| amfi_code | TEXT (FK) | Fund invested in |
| transaction_type | TEXT | SIP / Lumpsum / Redemption |
| amount_inr | REAL | Transaction amount in Indian Rupees |
| state | TEXT | Investor state (12 states covered) |
| city | TEXT | Investor city |
| city_tier | TEXT | T30 (top 30 cities) or B30 (beyond top 30) |
| age_group | TEXT | 18-25 / 26-35 / 36-45 / 46-55 / 56+ |
| gender | TEXT | Male / Female |
| annual_income_lakh | REAL | Annual income in Rs. lakh |
| payment_mode | TEXT | UPI / Net Banking / Mandate / Cheque |
| kyc_status | TEXT | Verified (92%) / Pending (8%) |

---

## fact_performance
Pre-computed risk and return metrics per scheme as of latest available date.
Source: `07_scheme_performance.csv` | computed from NAV history
40 rows (one per scheme)

| Column | Type | Description |
|--------|------|-------------|
| amfi_code | TEXT (PK, FK) | References dim_fund |
| scheme_name | TEXT | Scheme name |
| fund_house | TEXT | AMC name |
| category | TEXT | Equity / Debt / Hybrid |
| plan | TEXT | Regular / Direct |
| return_1yr_pct | REAL | 1-year absolute return % |
| return_3yr_pct | REAL | 3-year CAGR % |
| return_5yr_pct | REAL | 5-year CAGR % |
| benchmark_3yr_pct | REAL | Benchmark 3yr CAGR for comparison |
| alpha | REAL | Excess return over benchmark (return_3yr - benchmark_3yr) |
| beta | REAL | Sensitivity to market (1.0 = market movement) |
| sharpe_ratio | REAL | Risk-adjusted return. Higher is better, >1 is good |
| sortino_ratio | REAL | Like Sharpe but penalises only downside volatility |
| std_dev_ann_pct | REAL | Annualised std deviation of daily returns |
| max_drawdown_pct | REAL | Worst peak-to-trough decline (negative value) |
| aum_crore | REAL | Assets under management in Rs. crore |
| expense_ratio_pct | REAL | Annual expense ratio in % |
| morningstar_rating | INTEGER | 1-5 star rating based on Sharpe |
| risk_grade | TEXT | Low / Moderate / High / Very High |

---

## fact_aum
Quarterly AUM per fund house from 2022 to 2025.
Source: `03_aum_by_fund_house.csv` | AMFI quarterly reports
90 rows (10 fund houses x ~9 quarters)

| Column | Type | Description |
|--------|------|-------------|
| date | TEXT | Quarter end date YYYY-MM-DD |
| fund_house | TEXT | AMC name |
| aum_lakh_crore | REAL | AUM in Rs. lakh crore (e.g. 12.5 = Rs.12.5 lakh crore) |
| aum_crore | REAL | AUM in Rs. crore (e.g. 1250000) |
| num_schemes | INTEGER | Number of schemes managed by this AMC |

Note: aum_lakh_crore and aum_crore represent the same value in different units.
Always check the column name before calculations.

---

## fact_sip_industry
Monthly industry-level SIP data from AMFI Monthly Notes.
Source: `04_monthly_sip_inflows.csv` | AMFI Monthly Notes
48 rows (Jan 2022 to Dec 2025)

| Column | Type | Description |
|--------|------|-------------|
| month | TEXT (PK) | Month in YYYY-MM-DD format (first of each month) |
| sip_inflow_crore | REAL | Total SIP inflows for the month in Rs. crore |
| active_sip_accounts_crore | REAL | Number of active SIP accounts in crore |
| new_sip_accounts_lakh | REAL | New SIP registrations that month in lakh |
| sip_aum_lakh_crore | REAL | Total SIP AUM in Rs. lakh crore |
| yoy_growth_pct | REAL | YoY growth in SIP inflows (null for first 12 months) |

---

## fact_portfolio
Top equity holdings per fund as of Dec 2025.
Source: `09_portfolio_holdings.csv` | fund house disclosures
322 rows (~8 holdings per equity fund)

| Column | Type | Description |
|--------|------|-------------|
| amfi_code | TEXT (FK) | References dim_fund |
| stock_symbol | TEXT | NSE ticker symbol |
| stock_name | TEXT | Company name |
| sector | TEXT | Sector classification e.g. Banking, IT |
| weight_pct | REAL | Portfolio weight as % |
| market_value_cr | REAL | Market value of holding in Rs. crore |
| current_price_inr | REAL | Stock price as of portfolio_date |
| portfolio_date | TEXT | Date of portfolio disclosure YYYY-MM-DD |
