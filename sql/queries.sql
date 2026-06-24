-- queries.sql
-- 10 analytical queries on bluestock_mf.db
-- Day 2 | June 2026


-- Q1: top 5 fund houses by latest AUM (Dec 2025)
SELECT
    fund_house,
    aum_lakh_crore,
    aum_crore,
    num_schemes
FROM fact_aum
WHERE date = (SELECT MAX(date) FROM fact_aum)
ORDER BY aum_crore DESC
LIMIT 5;


-- Q2: average NAV per month across all schemes (last 12 months)
SELECT
    strftime('%Y-%m', nav_date) AS month,
    ROUND(AVG(nav), 2) AS avg_nav
FROM fact_nav
WHERE nav_date >= date('now', '-12 months')
GROUP BY month
ORDER BY month;


-- Q3: SIP inflow year-on-year growth
SELECT
    strftime('%Y', month) AS year,
    ROUND(SUM(sip_inflow_crore), 0) AS total_sip_inflow_crore,
    ROUND(AVG(yoy_growth_pct), 1) AS avg_yoy_growth_pct
FROM fact_sip_industry
GROUP BY year
ORDER BY year;


-- Q4: transaction count and total amount by state
SELECT
    state,
    COUNT(*) AS num_transactions,
    ROUND(SUM(amount_inr) / 1e6, 2) AS total_amount_millions
FROM fact_transactions
GROUP BY state
ORDER BY total_amount_millions DESC;


-- Q5: funds with expense_ratio below 1%
SELECT
    f.scheme_name,
    f.fund_house,
    f.category,
    f.expense_ratio_pct,
    f.plan
FROM dim_fund f
WHERE f.expense_ratio_pct < 1.0
ORDER BY f.expense_ratio_pct;


-- Q6: top 10 funds by 3-year return
SELECT
    scheme_name,
    fund_house,
    category,
    return_3yr_pct,
    sharpe_ratio,
    alpha
FROM fact_performance
ORDER BY return_3yr_pct DESC
LIMIT 10;


-- Q7: transaction split by type (SIP vs Lumpsum vs Redemption)
SELECT
    transaction_type,
    COUNT(*) AS num_transactions,
    ROUND(SUM(amount_inr) / 1e7, 2) AS total_crore,
    ROUND(AVG(amount_inr), 0) AS avg_amount_inr
FROM fact_transactions
GROUP BY transaction_type
ORDER BY total_crore DESC;


-- Q8: average SIP amount by age group
SELECT
    age_group,
    COUNT(*) AS num_transactions,
    ROUND(AVG(amount_inr), 0) AS avg_sip_amount,
    ROUND(SUM(amount_inr) / 1e7, 2) AS total_crore
FROM fact_transactions
WHERE transaction_type = 'SIP'
GROUP BY age_group
ORDER BY avg_sip_amount DESC;


-- Q9: top 5 equity holdings by total portfolio weight across all funds
SELECT
    stock_name,
    sector,
    COUNT(DISTINCT amfi_code) AS num_funds_holding,
    ROUND(AVG(weight_pct), 2) AS avg_weight_pct,
    ROUND(SUM(market_value_cr), 0) AS total_market_value_cr
FROM fact_portfolio
GROUP BY stock_name, sector
ORDER BY total_market_value_cr DESC
LIMIT 5;


-- Q10: monthly active investors (unique investors transacting each month)
SELECT
    strftime('%Y-%m', transaction_date) AS month,
    COUNT(DISTINCT investor_id) AS active_investors,
    COUNT(*) AS total_transactions,
    ROUND(SUM(amount_inr) / 1e7, 2) AS total_crore
FROM fact_transactions
GROUP BY month
ORDER BY month;
