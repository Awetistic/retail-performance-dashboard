-- ============================================================
-- business_questions.sql
-- Answers the core business questions against the `transactions`
-- table in data/retail.db.
--
-- Run all of them with:
--   sqlite3 data/retail.db < sql/business_questions.sql
-- Or run one at a time in the sqlite3 shell / any SQLite client.
-- ============================================================

-- 1. INVENTORY: Top 10 sub-categories by revenue
SELECT sub_category, ROUND(SUM(sales), 2) AS total_revenue
FROM transactions
GROUP BY sub_category
ORDER BY total_revenue DESC
LIMIT 10;

-- 2. INVENTORY: Bottom 10 sub-categories by revenue
SELECT sub_category, ROUND(SUM(sales), 2) AS total_revenue
FROM transactions
GROUP BY sub_category
ORDER BY total_revenue ASC
LIMIT 10;

-- 3. INVENTORY: Month-over-month sales trend by category
SELECT category, year, month, ROUND(SUM(sales), 2) AS monthly_sales
FROM transactions
GROUP BY category, year, month
ORDER BY category, year, month;

-- 4. DISCOUNTS: Average discount % vs profit margin by category
-- NOTE: margin is SUM(profit)/SUM(sales), the aggregate ("blended") margin —
-- not AVG(profit_margin), which is skewed by outlier rows where a small sale
-- carries a large dollar loss (e.g. $188 in sales against a $2,150 loss is a
-- -1144% row-level ratio that would dominate a simple average).
SELECT category,
       ROUND(AVG(discount) * 100, 2) AS avg_discount_pct,
       ROUND(SUM(profit) * 100.0 / SUM(sales), 2) AS profit_margin_pct
FROM transactions
GROUP BY category
ORDER BY profit_margin_pct DESC;

-- 5. DISCOUNTS: Profit margin by discount bucket (aggregate margin, see note above)
SELECT discount_bucket,
       ROUND(SUM(profit) * 100.0 / SUM(sales), 2) AS profit_margin_pct,
       COUNT(*) AS num_orders
FROM transactions
GROUP BY discount_bucket
ORDER BY
  CASE discount_bucket
    WHEN '0%' THEN 1
    WHEN '1-10%' THEN 2
    WHEN '10-20%' THEN 3
    WHEN '20%+' THEN 4
  END;

-- 6. REGIONAL: Revenue and profit by region
SELECT region,
       ROUND(SUM(sales), 2) AS total_revenue,
       ROUND(SUM(profit), 2) AS total_profit,
       ROUND(SUM(profit) * 100.0 / SUM(sales), 2) AS profit_margin_pct
FROM transactions
GROUP BY region
ORDER BY total_revenue DESC;

-- 7. REGIONAL: Year-over-year revenue growth by region
WITH yearly AS (
  SELECT region, year, SUM(sales) AS revenue
  FROM transactions
  GROUP BY region, year
)
SELECT region, year, ROUND(revenue, 2) AS revenue,
       ROUND(
         100.0 * (revenue - LAG(revenue) OVER (PARTITION BY region ORDER BY year))
         / LAG(revenue) OVER (PARTITION BY region ORDER BY year), 2
       ) AS yoy_growth_pct
FROM yearly
ORDER BY region, year;
