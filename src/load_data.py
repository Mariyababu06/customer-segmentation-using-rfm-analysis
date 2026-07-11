import pandas as pd
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")

engine = create_engine(f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:5432/{DB_NAME}')

# UCI Online Retail II has 2 sheets: Year 2009-2010 and Year 2010-2011
df1 = pd.read_excel('data/raw/online_retail_II.xlsx', sheet_name='Year 2009-2010')
df2 = pd.read_excel('data/raw/online_retail_II.xlsx', sheet_name='Year 2010-2011')
df = pd.concat([df1, df2], ignore_index=True)

# Rename columns to match your table schema
df.columns = ['invoice_no', 'stock_code', 'description', 'quantity',
              'invoice_date', 'unit_price', 'customer_id', 'country']

# Drop rows with no customer_id (common in this dataset, needed for RFM)
df = df.dropna(subset=['customer_id'])

df.to_sql('retail_transactions', engine, if_exists='append', index=False, chunksize=5000)

print(f"Loaded {len(df)} rows into retail_transactions")