from pathlib import Path
import pandas as pd
from src.db import get_connection

COLUMNS = ["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR",
           "HS", "AS", "HST", "AST",
           "AvgH", "AvgD", "AvgA", "AvgCH", "AvgCD", "AvgCA"]

def read_season(path):
    """
    Reads a season CSV file and returns a DataFrame with the relevant columns.

    """
    # Read the file. latin-1 avoids errors from odd characters
    df = pd.read_csv(path, encoding="latin-1")

    # Keep columns. Any that are missing become empty instead of crashing
    df = df.reindex(columns=COLUMNS)

    # Remove blank rows
    df = df.dropna(subset=["HomeTeam"])

    # Convert dates, which come in more than one format
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, format="mixed")

    # Get league and season from the file name
    league, season = path.stem.split("_")

    # Add league and season columns
    df["League"] = league
    df["Season"] = season

    return df

def load_teams(conn, df):
    # Unique names from both columns
    names = set(df["HomeTeam"]) | set(df["AwayTeam"])

    # Insert many rows in one go. Each row must be a tuple, so one value needs a comma: (name,)
    sql = "INSERT INTO teams (name) VALUES (%s) ON CONFLICT (name) DO NOTHING"
    rows = [(name,) for name in names]

    with conn.cursor() as cur:
        cur.executemany(sql, rows)

    # Read the IDs back. Each row is (name, team_id), so dict() can use them directly
    result = conn.execute("SELECT name, team_id FROM teams").fetchall()
    team_ids = dict(result)
    
    return team_ids

if __name__ == "__main__":
    with get_connection() as conn:
        for path in sorted(Path("data/raw").glob("*.csv")):
            df = read_season(path)
            team_ids = load_teams(conn, df)

    print(len(team_ids))