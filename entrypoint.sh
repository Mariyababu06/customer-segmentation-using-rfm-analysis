#!/bin/bash
set -e

RAW_FILE="data/raw/online_retail_II.xlsx"

echo "=== RFM App Entrypoint ==="

echo "Waiting for database at $DB_HOST..."
until pg_isready -h "$DB_HOST" -U "$DB_USER" > /dev/null 2>&1; do
    echo "  db not ready yet, retrying in 2s..."
    sleep 2
done
echo "Database is up."

# Check the DB itself (not local disk) to decide whether to run the pipeline.
# This works correctly even though Render containers are ephemeral.
ROW_COUNT=$(PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -tAc \
    "SELECT COUNT(*) FROM rfm_table;" 2>/dev/null || echo "0")

if [ "$ROW_COUNT" -gt "0" ] 2>/dev/null; then
    echo "rfm_table already has $ROW_COUNT rows — skipping pipeline, launching dashboard."
else
    echo "rfm_table is empty or missing — running full pipeline..."

    if [ ! -f "$RAW_FILE" ]; then
        echo "ERROR: $RAW_FILE not found in the image."
        echo "Make sure your Dockerfile has: COPY data/raw/ /app/data/raw/"
        echo "And that .dockerignore / .gitignore do not exclude this file."
        exit 1
    fi

    echo "[1/4] Loading raw Excel data into Postgres (retail_transactions)..."
    (cd src && python data_loader.py)

    echo "[2/4] Cleaning data (clean_transactions)..."
    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -f sql/clean_data.sql

    echo "[3/4] Building RFM aggregation (rfm_table)..."
    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -f sql/rfm_analsis.sql

    echo "[4/4] Scoring, clustering, labeling segments..."
    (cd src && python segmentation.py)

    echo "Pipeline complete."
fi

echo "Starting Streamlit dashboard..."
exec streamlit run app/streamlit_app.py --server.port=8501 --server.address=0.0.0.0