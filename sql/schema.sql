CREATE TABLE retail_transactions (
    invoice_no VARCHAR(20),
    stock_code VARCHAR(20),
    description TEXT,
    quantity INTEGER,
    invoice_date TIMESTAMP,
    unit_price NUMERIC(10,2),
    customer_id VARCHAR(20),
    country VARCHAR(50)
);
SELECT * FROM retail_transactions LIMIT 10;
SELECT COUNT(*) FROM retail_transactions;