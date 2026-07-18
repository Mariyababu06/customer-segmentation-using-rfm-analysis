DROP TABLE IF EXISTS clean_transactions;

CREATE TABLE clean_transactions AS
SELECT DISTINCT
    customer_id::numeric::bigint AS customer_id,
    invoice_no                   AS invoice_no,
    stock_code                   AS stock_code,
    quantity::integer            AS quantity,
    invoice_date::timestamp      AS invoice_date,
    unit_price::numeric(10,2)    AS unit_price,
    country                      AS country
FROM raw_transactions
WHERE customer_id IS NOT NULL
  AND stock_code IS NOT NULL
  AND invoice_no IS NOT NULL
  AND quantity > 0
  AND unit_price > 0
  AND invoice_no NOT LIKE 'C%';
  SELECT COUNT(*) FROM clean_transactions