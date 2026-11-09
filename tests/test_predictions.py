"""Tests for saving predictions in src/predict.py: a saved prediction must never be
overwritten, and nothing may be saved less than 2 hours before kick-off.

The kick-off tests use fixed clock times, so they never depend on when they run.
The saving tests need the database and run inside a transaction that is rolled
back, so nothing is ever kept.
"""
from datetime import date, timedelta

import pandas as pd
import pytest

from src.db import get_connection
from src.predict import can_still_predict, save_predictions


def at(utc):
    return pd.Timestamp(utc, tz="UTC")


def one_match(day, time):
    return pd.DataFrame([{"Date": date.fromisoformat(day), "Time": time}])


# ---- Kick-off rule (no database) ----

def test_winter_same_day_far_enough_ahead():
    # November: UK time = UTC. 15:00 kick-off, run at 10:00 → 5 hours ahead
    assert can_still_predict(one_match("2030-11-16", "15:00"), at("2030-11-16 10:00")).all()


def test_winter_too_close_to_kick_off():
    # 15:00 kick-off, run at 13:30 → only 1.5 hours ahead
    assert not can_still_predict(one_match("2030-11-16", "15:00"), at("2030-11-16 13:30")).any()


def test_summer_time_is_converted():
    # August: UK is UTC+1, so a 15:00 kick-off is 14:00 UTC. At 12:30 UTC that is
    # 1.5 hours away (too close); at 11:30 UTC it is 2.5 hours away (fine)
    match = one_match("2030-08-17", "15:00")
    assert not can_still_predict(match, at("2030-08-17 12:30")).any()
    assert can_still_predict(match, at("2030-08-17 11:30")).all()


def test_past_kick_off_is_never_saved():
    assert not can_still_predict(one_match("2030-11-16", "15:00"), at("2030-11-16 16:00")).any()


def test_missing_time_falls_back_to_later_days_only():
    no_time = pd.DataFrame([{"Date": date(2030, 11, 16)}])
    assert not can_still_predict(no_time, at("2030-11-16 06:00")).any()   # same day: not saved
    assert can_still_predict(no_time, at("2030-11-15 06:00")).all()       # day before: saved


def test_unclear_time_at_clock_change_falls_back():
    # 27 Oct 2030: UK clocks go back, so 01:30 happens twice. Treat it like no time
    match = one_match("2030-10-27", "01:30")
    assert can_still_predict(match, at("2030-10-26 06:00")).all()        # an earlier day: saved
    assert not can_still_predict(match, at("2030-10-27 00:00")).any()     # same day: not saved


# ---- Saving (database, rolled back) ----


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


def test_same_day_match_saved_when_far_enough_ahead(conn):
    home, away = two_teams(conn)
    day = date(2031, 1, 18)   # a fixed future Saturday; winter, so UK time = UTC
    match = fixture(home, away, day, (0.5, 0.3, 0.2)).assign(Time="15:00")

    save_predictions(conn, match, now=at("2031-01-18 14:00"))   # 1 hour before: refused
    assert stored(conn, home, away, day) == []
    save_predictions(conn, match, now=at("2031-01-18 09:00"))   # 6 hours before: saved
    assert len(stored(conn, home, away, day)) == 1


def test_today_and_past_are_not_saved(conn):
    home, away = two_teams(conn)
    for day in (date.today(), date.today() - timedelta(days=3)):
        save_predictions(conn, fixture(home, away, day, (0.5, 0.3, 0.2)))
        assert stored(conn, home, away, day) == []
