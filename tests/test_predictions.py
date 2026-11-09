"""Tests for saving predictions in src/predict.py: a saved prediction must never be
overwritten, and nothing for a match on or before today may be saved.

Needs the database. Every test runs inside a transaction that is rolled back, so
nothing is ever kept.
"""
from datetime import date, timedelta

import pandas as pd
import pytest

from src.db import get_connection
from src.predict import save_predictions


@pytest.fixture
def conn():
    """A connection whose changes are always thrown away at the end of the test."""
    connection = get_connection()
    yield connection
    connection.rollback()
    connection.close()


def two_teams(conn):
    return [row[0] for row in conn.execute("SELECT team_id FROM teams ORDER BY team_id LIMIT 2")]


def fixture(home, away, day, probs):
    """One upcoming match in the format save_predictions expects."""
    return pd.DataFrame([{"Date": day, "home_team_id": home, "away_team_id": away,
                          "prob_home": probs[0], "prob_draw": probs[1], "prob_away": probs[2]}])


def stored(conn, home, away, day):
    return conn.execute("""
        SELECT prob_home, prob_draw, prob_away FROM predictions
        WHERE home_team_id = %s AND away_team_id = %s AND match_date = %s AND model = 'average'
    """, (home, away, day)).fetchall()


def test_first_prediction_survives(conn):
    home, away = two_teams(conn)
    day = date.today() + timedelta(days=400)   # far ahead, so it never clashes with a real one

    save_predictions(conn, fixture(home, away, day, (0.5, 0.3, 0.2)))
    save_predictions(conn, fixture(home, away, day, (0.1, 0.1, 0.8)))   # a later, different one

    rows = stored(conn, home, away, day)
    assert len(rows) == 1
    assert [float(x) for x in rows[0]] == pytest.approx([0.5, 0.3, 0.2])


def test_today_and_past_are_not_saved(conn):
    home, away = two_teams(conn)
    for day in (date.today(), date.today() - timedelta(days=3)):
        save_predictions(conn, fixture(home, away, day, (0.5, 0.3, 0.2)))
        assert stored(conn, home, away, day) == []
