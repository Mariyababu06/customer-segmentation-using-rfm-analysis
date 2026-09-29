
-- Q1. Revenue concentration: how much do the top customers contribute?
--     (Customers split into 10 equal groups by spend; decile 1 = top 10%)
WITH ranked AS (
    SELECT customer_id,
           monetary::numeric AS monetary,
           NTILE(10) OVER (ORDER BY monetary DESC) AS decile
    FROM rfm_scored
)
SELECT decile,
       COUNT(*)                                                      AS customers,
       ROUND(SUM(monetary), 0)                                       AS revenue,
       ROUND(100.0 * SUM(monetary) / SUM(SUM(monetary)) OVER (), 1)  AS pct_of_revenue,
       ROUND(100.0 * SUM(SUM(monetary)) OVER (ORDER BY decile)
                   / SUM(SUM(monetary)) OVER (), 1)                  AS cumulative_pct_of_revenue
FROM ranked
GROUP BY decile
ORDER BY decile;
 
 
-- Q2. Segment breakdown: size, revenue share and behaviour of each segment
SELECT segment_label,
       COUNT(*)                                                                   AS customers,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)                         AS pct_of_customers,
       ROUND(SUM(monetary)::numeric, 0)                                           AS total_revenue,
       ROUND(100.0 * SUM(monetary)::numeric
                   / SUM(SUM(monetary)::numeric) OVER (), 1)                      AS pct_of_revenue,
       ROUND(AVG(recency_days)::numeric, 0)                                       AS avg_recency_days,
       ROUND(AVG(frequency)::numeric, 1)                                          AS avg_orders,
       ROUND(AVG(monetary)::numeric, 0)                                           AS avg_spend
FROM rfm_scored
GROUP BY segment_label
ORDER BY total_revenue DESC;
 
 
-- Q3. What is at stake in the "At Risk" segment, and what is a win-back worth?
--     (15% / 20% reactivation rates are planning assumptions, not measured values)
SELECT COUNT(*)                                        AS at_risk_customers,
       ROUND(SUM(monetary)::numeric, 0)                AS historical_revenue,
       ROUND(SUM(monetary)::numeric * 0.15, 0)         AS recovery_at_15pct,
       ROUND(SUM(monetary)::numeric * 0.20, 0)         AS recovery_at_20pct
FROM rfm_scored
WHERE segment_label = 'At Risk';
 
 
-- Q4. When should a customer be flagged as churn-risk?
--     Recency distribution per segment -> pick the trigger from the At Risk range
SELECT segment_label,
       MIN(recency_days)                                                              AS min_days,
       ROUND((PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY recency_days))::numeric, 0) AS p25_days,
       ROUND((PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY recency_days))::numeric, 0) AS median_days,
       ROUND((PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY recency_days))::numeric, 0) AS p75_days,
       MAX(recency_days)                                                              AS max_days
FROM rfm_scored
GROUP BY segment_label
ORDER BY median_days;
 
 
-- Q5. Is the business retail-driven or wholesale-driven?
--     Revenue share by order-frequency bucket
SELECT CASE
           WHEN frequency = 1              THEN '1 order (one-time)'
           WHEN frequency BETWEEN 2 AND 4  THEN '2-4 orders'
           WHEN frequency BETWEEN 5 AND 9  THEN '5-9 orders'
           ELSE '10+ orders (likely wholesale)'
       END                                                                        AS frequency_bucket,
       COUNT(*)                                                                   AS customers,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)                         AS pct_of_customers,
       ROUND(100.0 * SUM(monetary)::numeric
                   / SUM(SUM(monetary)::numeric) OVER (), 1)                      AS pct_of_revenue
FROM rfm_scored
GROUP BY 1
ORDER BY MIN(frequency);
 
 
-- Q6. Geographic concentration: top 10 countries by revenue
SELECT country,
       COUNT(DISTINCT customer_id)                                                AS customers,
       ROUND(SUM(quantity * unit_price)::numeric, 0)                              AS revenue,
       ROUND(100.0 * SUM(quantity * unit_price)::numeric
                   / SUM(SUM(quantity * unit_price)::numeric) OVER (), 1)         AS pct_of_revenue
FROM clean_transactions
GROUP BY country
ORDER BY revenue DESC
LIMIT 10;
 
 
-- Q7. Win-back call list: highest-value customers in the "At Risk" segment
SELECT customer_id,
       recency_days,
       frequency,
       ROUND(monetary::numeric, 0) AS lifetime_spend
FROM rfm_scored
WHERE segment_label = 'At Risk'
ORDER BY monetary DESC
LIMIT 50;