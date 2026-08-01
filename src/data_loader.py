import pandas as pd
from sqlalchemy import create_engine, inspect, text
import os
from dotenv import load_dotenv

load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")


required_vars = {
    "DB_USER": DB_USER,
    "DB_PASSWORD": DB_PASSWORD,
    "DB_HOST": DB_HOST,
    "DB_NAME": DB_NAME
}
missing = [k for k, v in required_vars.items() if not v]
if missing:
    raise EnvironmentError(f"Missing required environment variables: {missing}")

engine = create_engine(
    f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
)

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

    file_path = 'data/raw/online_retail_II.xlsx'
    if not os.path.exists(file_path):
        raise FileNotFoundError(
            f"Could not find {file_path}. Make sure it's included in the Docker image "
            f"(check .dockerignore and .gitignore aren't excluding it)."
        )

    print("Reading Excel sheets...")
    # UCI Online Retail II has 2 sheets: Year 2009-2010 and Year 2010-2011
    df1 = pd.read_excel(file_path, sheet_name='Year 2009-2010')
    df2 = pd.read_excel(file_path, sheet_name='Year 2010-2011')
    df = pd.concat([df1, df2], ignore_index=True)

    
    df.columns = ['invoice_no', 'stock_code', 'description', 'quantity',
                  'invoice_date', 'unit_price', 'customer_id', 'country']

    #
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