-- 1. Top 5 funds by AUM
SELECT df.scheme_name, fa.amfi_code, MAX(fa.aum) AS max_aum
FROM fact_aum fa
LEFT JOIN dim_fund df ON df.fund_key = fa.fund_key
GROUP BY df.scheme_name, fa.amfi_code
ORDER BY max_aum DESC
LIMIT 5;

-- 2. Average NAV per month
SELECT dd.year, dd.month, AVG(fn.nav) AS avg_nav
FROM fact_nav fn
JOIN dim_date dd ON dd.date_key = fn.date_key
GROUP BY dd.year, dd.month
ORDER BY dd.year, dd.month;

-- 3. SIP YoY growth
SELECT current.year, current.total_amount AS current_year_sip, previous.total_amount AS previous_year_sip,
       ROUND(((current.total_amount - previous.total_amount) / NULLIF(previous.total_amount, 0.0)) * 100.0, 2) AS yoy_growth_pct
FROM (
    SELECT dd.year, SUM(ft.amount) AS total_amount
    FROM fact_transactions ft
    JOIN dim_date dd ON dd.date_key = ft.date_key
    WHERE ft.transaction_type = 'SIP'
    GROUP BY dd.year
) current
LEFT JOIN (
    SELECT dd.year, SUM(ft.amount) AS total_amount
    FROM fact_transactions ft
    JOIN dim_date dd ON dd.date_key = ft.date_key
    WHERE ft.transaction_type = 'SIP'
    GROUP BY dd.year
) previous ON previous.year = current.year - 1;

-- 4. Transactions by state
SELECT state, COUNT(*) AS transaction_count, SUM(amount) AS total_amount
FROM fact_transactions
GROUP BY state
ORDER BY transaction_count DESC;

-- 5. Funds with expense_ratio < 1%
SELECT df.scheme_name, fp.amfi_code, fp.expense_ratio
FROM fact_performance fp
LEFT JOIN dim_fund df ON df.fund_key = fp.fund_key
WHERE fp.expense_ratio < 1.0
ORDER BY fp.expense_ratio ASC;

-- 6. Redemption share by fund
SELECT df.scheme_name, SUM(CASE WHEN ft.transaction_type = 'Redemption' THEN ft.amount ELSE 0 END) AS redemption_amount,
       SUM(ft.amount) AS total_amount,
       ROUND(100.0 * SUM(CASE WHEN ft.transaction_type = 'Redemption' THEN ft.amount ELSE 0 END) / NULLIF(SUM(ft.amount), 0), 2) AS redemption_share_pct
FROM fact_transactions ft
LEFT JOIN dim_fund df ON df.fund_key = ft.fund_key
GROUP BY df.scheme_name
ORDER BY redemption_share_pct DESC;

-- 7. Highest 1Y returns
SELECT df.scheme_name, fp.amfi_code, fp.one_year_return
FROM fact_performance fp
LEFT JOIN dim_fund df ON df.fund_key = fp.fund_key
ORDER BY fp.one_year_return DESC
LIMIT 10;

-- 8. Monthly AUM trend
SELECT dd.year, dd.month, SUM(fa.aum) AS total_aum
FROM fact_aum fa
JOIN dim_date dd ON dd.date_key = fa.date_key
GROUP BY dd.year, dd.month
ORDER BY dd.year, dd.month;

-- 9. NAV volatility by fund
SELECT df.scheme_name, fn.amfi_code, ROUND(AVG(ABS(fn.nav - avg_nav.avg_nav)), 4) AS nav_volatility
FROM fact_nav fn
JOIN (
    SELECT amfi_code, AVG(nav) AS avg_nav
    FROM fact_nav
    GROUP BY amfi_code
) avg_nav ON avg_nav.amfi_code = fn.amfi_code
LEFT JOIN dim_fund df ON df.fund_key = fn.fund_key
GROUP BY df.scheme_name, fn.amfi_code
ORDER BY nav_volatility DESC;

-- 10. KYC status mix
SELECT kyc_status, COUNT(*) AS transaction_count, SUM(amount) AS total_amount
FROM fact_transactions
GROUP BY kyc_status
ORDER BY total_amount DESC;
