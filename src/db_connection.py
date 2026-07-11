"""
Central place for creating the SQLAlchemy engine.
Every other script imports get_engine() from here instead of
building its own connection string.
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

load_dotenv()


def get_engine() -> Engine:
    """Build and return a SQLAlchemy engine from .env credentials."""
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    host = os.getenv("DB_HOST")
    db = os.getenv("DB_NAME")

    missing = [name for name, val in
               [("DB_USER", user), ("DB_PASSWORD", password),
                ("DB_HOST", host), ("DB_NAME", db)] if not val]
    if missing:
        raise EnvironmentError(
            f"Missing required .env values: {', '.join(missing)}. "
            "Copy .env.example to .env and fill it in."
        )

    return create_engine(f"postgresql://{user}:{password}@{host}:5432/{db}")


if __name__ == "__main__":
    # Quick sanity check: python db_connection.py
    engine = get_engine()
    with engine.connect() as conn:
        print("Connected successfully to:", engine.url.database)
