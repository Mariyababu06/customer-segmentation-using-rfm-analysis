DROP TABLE IF EXISTS rfm_table;

WITH customer_orders AS (
    SELECT
        customer_id,
        MAX(invoice_date)          AS last_purchase_date,
        COUNT(DISTINCT invoice_no) AS frequency,
        SUM(quantity * unit_price) AS monetary
    FROM clean_transactions
    GROUP BY customer_id
),
reference_date AS (
    SELECT MAX(invoice_date) AS max_date FROM clean_transactions
)
SELECT
    co.customer_id,
    EXTRACT(DAY FROM (rd.max_date - co.last_purchase_date))::int AS recency_days,
    co.frequency,
    co.monetary
INTO rfm_table
FROM customer_orders co, reference_date rd;
SELECT COUNT(*) FROM rfm_table;