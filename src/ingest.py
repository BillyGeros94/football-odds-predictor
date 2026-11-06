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

def load_matches(conn, df, team_ids):
    df = df.copy()
    df["Date"] = df["Date"].dt.date
    df["home_id"] = df["HomeTeam"].map(team_ids)
    df["away_id"] = df["AwayTeam"].map(team_ids)

    clean = df.astype(object).where(df.notna(), None)

    columns = ["League", "Season", "Date", "home_id", "away_id",
           "FTHG", "FTAG", "HS", "AS", "HST", "AST", "FTR"]
    rows = clean[columns].values.tolist()

    sql = """
        INSERT INTO matches (
            league, season, match_date, home_team_id, away_team_id,
            home_goals, away_goals, home_shots, away_shots,
            home_shots_on_target, away_shots_on_target, result
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (match_date, home_team_id, away_team_id) DO NOTHING
    """

    with conn.cursor() as cur:
        cur.executemany(sql, rows)

def load_odds(conn, df, team_ids):
    # Keep only matches with closing odds
    df = df.dropna(subset=["AvgCH"]).copy()
    if df.empty:
        return

    df["Date"] = df["Date"].dt.date
    df["home_id"] = df["HomeTeam"].map(team_ids)
    df["away_id"] = df["AwayTeam"].map(team_ids)

    # Get this file's match IDs from the database
    league = df["League"].iloc[0]
    season = df["Season"].iloc[0]
    query = """
        SELECT match_id, match_date, home_team_id, away_team_id
        FROM matches
        WHERE league = %s AND season = %s
    """
    result = conn.execute(query, (league, season)).fetchall()

    # Build a lookup: (date, home ID, away ID) → match_id
    match_ids = {(date, home, away): match_id
                 for match_id, date, home, away in result}

    # Find the match_id for each row
    keys = zip(df["Date"], df["home_id"], df["away_id"])
    df["match_id"] = [match_ids[key] for key in keys]

    clean = df.astype(object).where(df.notna(), None)
    
    columns = ["match_id", "AvgH", "AvgD", "AvgA", "AvgCH", "AvgCD", "AvgCA"]
    rows = clean[columns].values.tolist()
    
    sql = """
        INSERT INTO odds (
            match_id, avg_home, avg_draw, avg_away, close_home,
            close_draw, close_away)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (match_id) DO NOTHING
    """
    
    with conn.cursor() as cur:
        cur.executemany(sql, rows)

if __name__ == "__main__":
    with get_connection() as conn:
        for path in sorted(Path("data/raw").glob("*.csv")):
            df = read_season(path)
            team_ids = load_teams(conn, df)
            load_matches(conn, df, team_ids)
            load_odds(conn, df, team_ids)

        count = conn.execute("SELECT COUNT(*) FROM odds").fetchone()[0]


    print(count)