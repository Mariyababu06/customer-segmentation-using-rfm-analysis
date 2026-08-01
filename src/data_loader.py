import pandas as pd
from sqlalchemy import inspect, text
import os
from db_connection import get_engine

engine = get_engine()

def table_already_loaded(engine, table_name='retail_transactions'):
    """Check if the table exists and already has data, to avoid duplicate loads on redeploy."""
    try:
        inspector = inspect(engine)
        if not inspector.has_table(table_name):
            return False
        with engine.connect() as conn:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
        return result > 0
    except Exception as e:
        print(f"Warning: could not check existing table state: {e}")
        return False

def load_data():
    if table_already_loaded(engine):
        print("Table 'retail_transactions' already has data — skipping load.")
        return

    file_path = 'data/raw/online_retail_II.csv'
    if not os.path.exists(file_path):
        raise FileNotFoundError(
            f"Could not find {file_path}. Make sure it's included in the Docker image "
            f"(check .dockerignore excludes data/raw/* but allows this .csv)."
        )

    print("Reading CSV...")
    df = pd.read_csv(file_path, encoding='ISO-8859-1')  # UCI dataset commonly needs this encoding

    df.columns = ['invoice_no', 'stock_code', 'description', 'quantity',
                  'invoice_date', 'unit_price', 'customer_id', 'country']

    df = df.dropna(subset=['customer_id'])

    print(f"Loading {len(df)} rows into retail_transactions...")
    try:
        df.to_sql('retail_transactions', engine, if_exists='append',
                   index=False, chunksize=5000)
        print(f"Successfully loaded {len(df)} rows into retail_transactions")
    except Exception as e:
        print(f"ERROR loading data: {e}")
        raise

if __name__ == "__main__":
    load_data()