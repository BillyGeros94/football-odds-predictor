import os
from pathlib import Path
import pandas as pd
import psycopg
from dotenv import load_dotenv

load_dotenv()
url = os.environ["DATABASE_URL"]

def get_connection():
    return psycopg.connect(url)

def create_tables():   
    for name in ["schema.sql", "features.sql", "team_current.sql"]:
        sql_text = Path(f"sql/{name}").read_text()
        with get_connection() as conn:
            conn.execute(sql_text)

def read_sql(query):
    with get_connection() as conn:
        rows = conn.execute(query)
        columns = [c.name for c in rows.description]
        return pd.DataFrame(rows.fetchall(), columns=columns)

if __name__ == "__main__":

    create_tables()

    query = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public';
            """

    with get_connection() as conn:
        rows = conn.execute(query).fetchall()

    for row in rows:
        print(row[0])