"""Database helpers: connect to PostgreSQL, create the tables and views, read queries.

The connection string comes from the DATABASE_URL environment variable, read
from the .env file locally or from a GitHub secret in the workflow.

Run directly to create everything and list the tables:
    python -m src.db
"""
import os
from pathlib import Path

import pandas as pd
import psycopg
from dotenv import load_dotenv

load_dotenv()   # reads .env if it exists; does nothing in GitHub Actions
url = os.environ["DATABASE_URL"]

# Order matters: the views in features.sql and team_current.sql read the tables in schema.sql
SQL_FILES = ["schema.sql", "features.sql", "team_current.sql"]


def get_connection():
    """Open a new database connection. Use it in a `with` block, which commits at the end."""
    return psycopg.connect(url)


def create_tables():
    """Run every SQL file. Safe to rerun: tables use IF NOT EXISTS, views use OR REPLACE."""
    for name in SQL_FILES:
        sql_text = Path(f"sql/{name}").read_text()
        with get_connection() as conn:
            conn.execute(sql_text)


def read_sql(query):
    """Run a SELECT query and return the result as a pandas DataFrame."""
    with get_connection() as conn:
        rows = conn.execute(query)
        columns = [c.name for c in rows.description]
        return pd.DataFrame(rows.fetchall(), columns=columns)


if __name__ == "__main__":
    create_tables()

    # Views are listed here too, after the tables
    query = """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public';
    """
    with get_connection() as conn:
        rows = conn.execute(query).fetchall()

    for row in rows:
        print(row[0])
