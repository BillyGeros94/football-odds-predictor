"""Tests for src/ingest.py: reloading must update a stored match, so a result the site
corrects later is picked up, and must never create a duplicate.

Needs the database. Every test runs inside a transaction that is rolled back.
"""
import pandas as pd
import pytest

from src.db import get_connection
from src.ingest import load_matches


@pytest.fixture
def conn():
    connection = get_connection()
    yield connection
    connection.rollback()
    connection.close()


def stored_match(conn):
    """One real match, plus the team lookup load_matches needs."""
    row = conn.execute("""
        SELECT m.league, m.season, m.match_date, h.name, a.name, m.home_team_id, m.away_team_id
        FROM matches m
        JOIN teams h ON h.team_id = m.home_team_id
        JOIN teams a ON a.team_id = m.away_team_id
        ORDER BY m.match_id LIMIT 1
    """).fetchone()
    league, season, day, home, away, home_id, away_id = row
    return league, season, day, home, away, {home: home_id, away: away_id}


def as_file_row(league, season, day, home, away, goals):
    """The match as read_season would return it, with the given score."""
    home_goals, away_goals = goals
    result = "H" if home_goals > away_goals else "A" if home_goals < away_goals else "D"
    return pd.DataFrame([{
        "Date": pd.Timestamp(day), "HomeTeam": home, "AwayTeam": away,
        "FTHG": home_goals, "FTAG": away_goals, "FTR": result,
        "HS": 10, "AS": 8, "HST": 4, "AST": 3, "League": league, "Season": season}])


def test_corrected_result_replaces_the_old_one(conn):
    league, season, day, home, away, team_ids = stored_match(conn)
    load_matches(conn, as_file_row(league, season, day, home, away, (7, 0)), team_ids)

    goals = conn.execute("""
        SELECT home_goals, away_goals, result FROM matches
        WHERE match_date = %s AND home_team_id = %s AND away_team_id = %s
    """, (day, team_ids[home], team_ids[away])).fetchall()
    assert goals == [(7, 0, "H")]


def test_reloading_never_duplicates(conn):
    league, season, day, home, away, team_ids = stored_match(conn)
    before = conn.execute("SELECT COUNT(*) FROM matches").fetchone()[0]
    for _ in range(2):
        load_matches(conn, as_file_row(league, season, day, home, away, (1, 1)), team_ids)
    assert conn.execute("SELECT COUNT(*) FROM matches").fetchone()[0] == before
