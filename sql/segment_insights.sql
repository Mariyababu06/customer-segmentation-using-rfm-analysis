SELECT
    segment_label,
    COUNT(*)                                        AS customer_count,
    ROUND(AVG(recency_days)::numeric, 1)            AS avg_recency_days,
    ROUND(AVG(frequency)::numeric, 1)               AS avg_frequency,
    ROUND(AVG(monetary)::numeric, 2)                AS avg_monetary,
    ROUND(SUM(monetary)::numeric, 2)                AS total_revenue
FROM rfm_scored
GROUP BY segment_label
ORDER BY total_revenue DESC;


-- 2. REVENUE CONTRIBUTION % BY SEGMENT
WITH totals AS (
    SELECT SUM(monetary) AS grand_total FROM rfm_scored
)
SELECT
    r.segment_label,
    COUNT(*)                                                            AS customer_count,
    ROUND(SUM(r.monetary)::numeric, 2)                                  AS segment_revenue,
    ROUND((100.0 * SUM(r.monetary) / t.grand_total)::numeric, 2)        AS pct_of_total_revenue,
    ROUND((100.0 * COUNT(*) / (SELECT COUNT(*) FROM rfm_scored))::numeric, 2) AS pct_of_customers
FROM rfm_scored r, totals t
GROUP BY r.segment_label, t.grand_total
ORDER BY segment_revenue DESC;


-- 3. TOP 10 CUSTOMERS WITHIN EACH SEGMENT
SELECT *
FROM (
    SELECT
        customer_id,
        segment_label,
        monetary,
        frequency,
        recency_days,
        RANK() OVER (PARTITION BY segment_label ORDER BY monetary DESC) AS rank_in_segment
    FROM rfm_scored
) ranked
WHERE rank_in_segment <= 10
ORDER BY segment_label, rank_in_segment;


-- 4. RFM SCORE MATRIX
SELECT
    "R_score",
    "F_score",
    COUNT(*)                        AS customer_count,
    ROUND(AVG(monetary)::numeric, 2) AS avg_monetary
FROM rfm_scored
GROUP BY "R_score", "F_score"
ORDER BY "R_score" DESC, "F_score" DESC;


-- 5. COUNTRY-WISE SEGMENT BREAKDOWN
SELECT
    ct.country,
    rs.segment_label,
    COUNT(DISTINCT rs.customer_id)      AS customer_count,
    ROUND(SUM(rs.monetary)::numeric, 2) AS segment_revenue
FROM rfm_scored rs
JOIN (
    SELECT DISTINCT ON (customer_id) customer_id, country
    FROM clean_transactions
    ORDER BY customer_id, invoice_date DESC
) ct ON ct.customer_id = rs.customer_id
GROUP BY ct.country, rs.segment_label
ORDER BY ct.country, segment_revenue DESC;


-- 6. AT-RISK HIGH-VALUE CUSTOMERS
SELECT
    customer_id,
    recency_days,
    frequency,
    monetary,
    segment_label
FROM rfm_scored
WHERE segment_label = 'At Risk'
  AND monetary > (SELECT AVG(monetary) FROM rfm_scored)
ORDER BY monetary DESC
LIMIT 50;


-- 7. CHAMPIONS VS LOST/CHURNED COMPARISON
SELECT
    segment_label,
    COUNT(*)                              AS customers,
    ROUND(AVG(recency_days)::numeric, 1)  AS avg_recency,
    ROUND(AVG(frequency)::numeric, 1)     AS avg_frequency,
    ROUND(AVG(monetary)::numeric, 2)      AS avg_monetary
FROM rfm_scored
WHERE segment_label IN ('Champions', 'Lost / Churned')
GROUP BY segment_label;


-- 8. MONTHLY REVENUE TREND
SELECT
    DATE_TRUNC('month', invoice_date)::date       AS month,
    COUNT(DISTINCT customer_id)                   AS active_customers,
    COUNT(DISTINCT invoice_no)                    AS orders,
    ROUND(SUM(quantity * unit_price)::numeric, 2) AS revenue
FROM clean_transactions
GROUP BY 1
ORDER BY 1;



WITH scored AS (
    SELECT
        customer_id,
        recency_days,
        frequency,
        monetary,
        NTILE(5) OVER (ORDER BY recency_days DESC) AS r_score,
        NTILE(5) OVER (ORDER BY frequency ASC)     AS f_score,
        NTILE(5) OVER (ORDER BY monetary ASC)      AS m_score
    FROM rfm_table
)
SELECT
    *,
    (r_score + f_score + m_score) AS rfm_total,
    CASE
        WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'Champions'
        WHEN r_score >= 3 AND f_score >= 3                  THEN 'Loyal Customers'
        WHEN r_score <= 2 AND f_score >= 3                  THEN 'At Risk'
        ELSE 'Lost / Churned'
    END AS sql_segment_label
FROM scored
ORDER BY rfm_total DESC;