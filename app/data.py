"""Every database query and file read the app needs, cached so the database is
asked at most once an hour per query. The app only reads; all writing happens in
the GitHub Actions workflow.
"""
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

# The app runs from app/, so add the project folder to the path to import src
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# On Streamlit Cloud the connection string is a secret; locally src.db reads .env
if "DATABASE_URL" not in os.environ and not (ROOT / ".env").exists():
    os.environ["DATABASE_URL"] = st.secrets["DATABASE_URL"]

from src.db import get_connection                       # noqa: E402
from src.evaluate import remove_margin                  # noqa: E402
from src.features import load_features                  # noqa: E402
from src.live_score import live_scores                   # noqa: E402
from src.models import LOGISTIC_FEATURES, make_logistic  # noqa: E402
from src.predict import build_features                  # noqa: E402

HOUR = 3600


def query(sql, params=None):
    """Run a SELECT with optional parameters and return a DataFrame."""
    with get_connection() as conn:
        result = conn.execute(sql, params)
        return pd.DataFrame(result.fetchall(), columns=[c.name for c in result.description])


def to_float(df, columns):
    df[columns] = df[columns].astype(float)
    return df


# The league a team plays in now: the league of its most recent match
LATEST_LEAGUE = """
    LEFT JOIN LATERAL (
        SELECT league FROM matches m
        WHERE m.home_team_id = {team} OR m.away_team_id = {team}
        ORDER BY m.match_date DESC LIMIT 1
    ) lg ON TRUE
"""


# ---------- Freshness ----------

@st.cache_data(ttl=HOUR)
def freshness():
    """When the workflow last ran (every run saves a simulation) and the latest result loaded."""
    latest_result = query("SELECT MAX(match_date) AS d FROM matches").d[0]
    try:
        last_run = query("SELECT MAX(run_at) AS t FROM season_simulations").t[0]
    except Exception:   # the table does not exist before the first simulation
        last_run = None
    return last_run, latest_result


# ---------- Upcoming matches ----------

@st.cache_data(ttl=HOUR)
def upcoming():
    """Predictions for matches from today on, with team names and league."""
    df = query(f"""
        SELECT p.match_date, lg.league, h.name AS home, a.name AS away,
               p.prob_home, p.prob_draw, p.prob_away, p.created_at
        FROM predictions p
        JOIN teams h ON h.team_id = p.home_team_id
        JOIN teams a ON a.team_id = p.away_team_id
        {LATEST_LEAGUE.format(team="p.home_team_id")}
        WHERE p.match_date >= CURRENT_DATE AND p.model = 'average'
        ORDER BY p.match_date, lg.league, h.name
    """)
    return to_float(df, ["prob_home", "prob_draw", "prob_away"])


@st.cache_resource(ttl=6 * HOUR)
def explainer():
    """The logistic half of the live model, trained exactly as predict.py does."""
    train = load_features()
    model = make_logistic()
    model.fit(train[LOGISTIC_FEATURES], train["result"])
    return model


FEATURE_LABELS = {
    "elo_diff": "Rating gap (Elo)",
    "home_sot5": "Home side's shots on target",
    "home_sota5": "Home side's shots on target conceded",
    "away_sot5": "Away side's shots on target",
    "away_sota5": "Away side's shots on target conceded",
}


def explain(home, away):
    """How much each input pushes the prediction towards a home or away win.

    For logistic regression, each input's push on the home-win vs away-win odds is
    its scaled value times the difference between the two classes' coefficients.
    Positive favours the home side.
    """
    model = explainer()
    features = build_features(pd.DataFrame({"HomeTeam": [home], "AwayTeam": [away]}))
    if features.empty:
        return None
    scaled = model[:-1].transform(features[LOGISTIC_FEATURES])[0]   # imputer + scaler
    logistic = model[-1]
    classes = list(logistic.classes_)
    h, a = classes.index("H"), classes.index("A")
    weights = logistic.coef_[h] - logistic.coef_[a]

    rows = [{"input": "Home advantage",
             "push": logistic.intercept_[h] - logistic.intercept_[a], "value": ""}]
    for name, x, w, raw in zip(LOGISTIC_FEATURES, scaled, weights, features[LOGISTIC_FEATURES].iloc[0]):
        value = f"{raw:+.0f} points" if name == "elo_diff" else f"{raw:.1f} per game"
        rows.append({"input": FEATURE_LABELS[name], "push": x * w, "value": value})
    return pd.DataFrame(rows)


# ---------- Live record ----------

def per_match_loss(probs, result):
    """Log loss of each match: minus the log of the probability given to what happened."""
    picked = probs[np.arange(len(result)), result.map({"A": 0, "D": 1, "H": 2}).to_numpy()]
    return -np.log(picked)


@st.cache_data(ttl=HOUR)
def live():
    """The live record from src/live_score.py, with every source's probabilities side by side.

    Returns None while nothing has been scored.
    """
    record = live_scores()
    if record is None:
        return None

    matches = record["matches"].copy()
    names = dict(query("SELECT team_id, name FROM teams").values.tolist())
    matches["home"] = matches["home_team_id"].map(names)
    matches["away"] = matches["away_team_id"].map(names)

    model = matches[["prob_away", "prob_draw", "prob_home"]].to_numpy(dtype=float)
    pre = remove_margin(matches[["avg_away", "avg_draw", "avg_home"]].astype(float)).to_numpy()
    close = remove_margin(matches[["close_away", "close_draw", "close_home"]].astype(float)).to_numpy()
    for label, probs in [("model", model), ("pre", pre), ("close", close)]:
        matches[[f"{label}_away", f"{label}_draw", f"{label}_home"]] = probs
        matches[f"{label}_loss"] = per_match_loss(probs, matches["result"])

    return {"matches": matches.sort_values("match_date"), "scores": record["scores"],
            "unscored": record["unscored"], "superseded": record["superseded"]}


# ---------- Season predictions ----------

@st.cache_data(ttl=HOUR)
def simulation_latest():
    """Every team's chances from the most recent simulation run."""
    df = query("""
        SELECT s.*, t.name AS team
        FROM season_simulations s JOIN teams t USING (team_id)
        WHERE s.run_at = (SELECT MAX(run_at) FROM season_simulations)
    """)
    probs = ["p_title", "p_top4", "p_promotion", "p_playoffs", "p_relegation"]
    return to_float(df, probs + ["expected_points"])


@st.cache_data(ttl=HOUR)
def simulation_history():
    """Every run's chances for every team, for the trend chart."""
    df = query("""
        SELECT s.run_at, s.league, t.name AS team, s.p_title, s.p_top4,
               s.p_promotion, s.p_playoffs, s.p_relegation
        FROM season_simulations s JOIN teams t USING (team_id)
        WHERE s.season = (SELECT MAX(season) FROM season_simulations)
        ORDER BY s.run_at
    """)
    return to_float(df, ["p_title", "p_top4", "p_promotion", "p_playoffs", "p_relegation"])


# ---------- Teams ----------

@st.cache_data(ttl=HOUR)
def team_ratings():
    """Current Elo and last-5 form for every team playing this season."""
    df = query(f"""
        SELECT t.team_id, t.name AS team, lg.league, tc.elo_after AS elo,
               tc.gf5, tc.ga5, tc.sot5, tc.sota5
        FROM team_current tc
        JOIN teams t USING (team_id)
        {LATEST_LEAGUE.format(team="tc.team_id")}
        WHERE tc.match_date >= (
            SELECT MIN(match_date) FROM matches WHERE season = (SELECT MAX(season) FROM matches))
        ORDER BY tc.elo_after DESC
    """)
    return to_float(df, ["elo", "gf5", "ga5", "sot5", "sota5"])


# One row per team per match, with that team's goals and ratings
TEAM_MATCHES = """
    SELECT m.match_id, m.match_date, m.season, m.league, 'H' AS venue,
           o.name AS opponent, m.home_goals AS scored, m.away_goals AS conceded,
           e.home_before AS elo_before, e.home_after AS elo_after
    FROM matches m JOIN elo_ratings e USING (match_id) JOIN teams o ON o.team_id = m.away_team_id
    WHERE m.home_team_id = %(team)s
    UNION ALL
    SELECT m.match_id, m.match_date, m.season, m.league, 'A',
           o.name, m.away_goals, m.home_goals, e.away_before, e.away_after
    FROM matches m JOIN elo_ratings e USING (match_id) JOIN teams o ON o.team_id = m.home_team_id
    WHERE m.away_team_id = %(team)s
"""


@st.cache_data(ttl=HOUR)
def team_matches(team_id):
    """Every match of one team, oldest first, with its Elo before and after."""
    df = query(f"SELECT * FROM ({TEAM_MATCHES}) x ORDER BY match_date, match_id",
               {"team": int(team_id)})
    df = to_float(df, ["elo_before", "elo_after"])
    df["result"] = np.select([df["scored"] > df["conceded"], df["scored"] < df["conceded"]],
                             ["W", "L"], "D")
    return df


# ---------- Model performance ----------

@st.cache_data
def final_metrics():
    """The one-time final test, saved by src/final_test.py."""
    return json.loads((ROOT / "results" / "metrics.json").read_text())


@st.cache_data(ttl=24 * HOUR)
def home_win_rate():
    """Share of home wins in each season and league."""
    df = query("""
        SELECT season, league, AVG((result = 'H')::int) AS home_win_rate, COUNT(*) AS matches
        FROM matches GROUP BY season, league ORDER BY season
    """)
    return to_float(df, ["home_win_rate"])


CALIBRATION_CHART = ROOT / "results" / "calibration_final.png"
