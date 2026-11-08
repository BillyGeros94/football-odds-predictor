"""Load the football-data CSV files from data/raw/ into the database.

Each file is one league and season, named like E0_2526.csv (E0 = Premier
League, E1 = Championship). Teams, matches and odds are inserted with
ON CONFLICT DO NOTHING, so rerunning only adds rows that are new.

Run after downloading new files:
    python -m src.ingest
"""
from pathlib import Path

import pandas as pd

from src.db import get_connection

# Columns kept from each CSV:
# FTHG/FTAG = full-time goals, FTR = result (H/D/A), HS/AS = shots,
# HST/AST = shots on target, Avg* = average pre-match odds, AvgC* = closing odds
COLUMNS = ["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR",
           "HS", "AS", "HST", "AST",
           "AvgH", "AvgD", "AvgA", "AvgCH", "AvgCD", "AvgCA"]


def read_season(path):
    """Read one season file and return a clean DataFrame with league and season added."""
    # latin-1 avoids errors from odd characters in older files
    df = pd.read_csv(path, encoding="latin-1")

    # Keep our columns. Any that a file lacks (older seasons have no Avg odds) become empty
    df = df.reindex(columns=COLUMNS)

    # Some files end with blank rows
    df = df.dropna(subset=["HomeTeam"])

    # Older files use 2-digit years (07/08/15), newer ones 4-digit (07/08/2015)
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, format="mixed")

    # The file name holds the league and season: E0_2526 → "E0", "2526"
    league, season = path.stem.split("_")
    df["League"] = league
    df["Season"] = season

    return df


def load_teams(conn, df):
    """Insert any new team names and return a {name: team_id} lookup."""
    names = set(df["HomeTeam"]) | set(df["AwayTeam"])

    # executemany needs one tuple per row, so a single value needs a comma: (name,)
    sql = "INSERT INTO teams (name) VALUES (%s) ON CONFLICT (name) DO NOTHING"
    rows = [(name,) for name in names]

    with conn.cursor() as cur:
        cur.executemany(sql, rows)

    # Each row is (name, team_id), so dict() turns them straight into a lookup
    result = conn.execute("SELECT name, team_id FROM teams").fetchall()
    return dict(result)


def load_matches(conn, df, team_ids):
    """Insert the season's matches. Matches already in the database are skipped."""
    df = df.copy()
    df["Date"] = df["Date"].dt.date
    df["home_id"] = df["HomeTeam"].map(team_ids)
    df["away_id"] = df["AwayTeam"].map(team_ids)

    # pandas marks blanks as NaN, but the database needs None (stored as NULL)
    clean = df.astype(object).where(df.notna(), None)

    # Same order as the INSERT columns below
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
    """Insert the season's odds. Only seasons from 2019/20 have closing odds."""
    df = df.dropna(subset=["AvgCH"]).copy()
    if df.empty:
        return

    df["Date"] = df["Date"].dt.date
    df["home_id"] = df["HomeTeam"].map(team_ids)
    df["away_id"] = df["AwayTeam"].map(team_ids)

    # The odds table needs match_id, which only exists in the database, so read this file's IDs back
    league = df["League"].iloc[0]
    season = df["Season"].iloc[0]
    query = """
        SELECT match_id, match_date, home_team_id, away_team_id
        FROM matches
        WHERE league = %s AND season = %s
    """
    result = conn.execute(query, (league, season)).fetchall()

    # Lookup: (date, home ID, away ID) → match_id
    match_ids = {(date, home, away): match_id
                 for match_id, date, home, away in result}

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
    # One connection for all files: if anything fails, nothing is half-loaded
    with get_connection() as conn:
        for path in sorted(Path("data/raw").glob("*.csv")):
            df = read_season(path)
            team_ids = load_teams(conn, df)
            load_matches(conn, df, team_ids)   # matches first: odds need their IDs
            load_odds(conn, df, team_ids)

        count = conn.execute("SELECT COUNT(*) FROM odds").fetchone()[0]

    print(count)
