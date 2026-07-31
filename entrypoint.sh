#!/bin/bash
set -e

CSV_PATH="data/processed/rfm_scored.csv"
RAW_CSV="data/raw/online_retail_II.csv"

echo "=== RFM App Entrypoint ==="

echo "Waiting for database at $DB_HOST..."
until pg_isready -h "$DB_HOST" -U "$DB_USER" > /dev/null 2>&1; do
    echo "  db not ready yet, retrying in 2s..."
    sleep 2
done
echo "Database is up."

if [ -f "$CSV_PATH" ]; then
    echo "$CSV_PATH already exists — skipping pipeline, launching dashboard."
else
    echo "$CSV_PATH not found — running full pipeline..."

    if [ ! -f "$RAW_CSV" ]; then
        echo "ERROR: $RAW_CSV not found."
        echo "Mount the raw dataset into the container, e.g.:"
        echo "  docker run -v \$(pwd)/data/raw:/app/data/raw ..."
        exit 1
    fi

    echo "[1/4] Loading raw CSV into Postgres (raw_transactions)..."
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