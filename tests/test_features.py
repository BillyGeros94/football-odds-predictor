"""The leakage test: the match_features view (sql/features.sql) must equal an independent
pandas calculation of each team's averages over its PREVIOUS 5 matches, for every match.
If the view ever included a match's own result in its features, this would fail.

Needs the database (DATABASE_URL), which the GitHub Actions workflow provides.
"""
import numpy as np
import pandas as pd
import pytest

from src.db import read_sql
from src.features import load_features

STATS = {"gf5": "goals_for", "ga5": "goals_against", "sot5": "sot_for", "sota5": "sot_against"}


@pytest.fixture(scope="module")
def both():
    """The view's features next to the same features calculated in pandas."""
    matches = read_sql("""
        SELECT match_id, match_date, home_team_id, away_team_id, home_goals, away_goals,
               home_shots_on_target, away_shots_on_target
        FROM matches
    """)

    # One row per team per match, the same idea as the SQL but written independently
    home = pd.DataFrame({
        "match_id": matches["match_id"], "match_date": matches["match_date"],
        "team_id": matches["home_team_id"], "side": "home",
        "goals_for": matches["home_goals"], "goals_against": matches["away_goals"],
        "sot_for": matches["home_shots_on_target"], "sot_against": matches["away_shots_on_target"]})
    away = pd.DataFrame({
        "match_id": matches["match_id"], "match_date": matches["match_date"],
        "team_id": matches["away_team_id"], "side": "away",
        "goals_for": matches["away_goals"], "goals_against": matches["home_goals"],
        "sot_for": matches["away_shots_on_target"], "sot_against": matches["home_shots_on_target"]})
    teams = pd.concat([home, away]).sort_values(["team_id", "match_date", "match_id"])
    teams[list(STATS.values())] = teams[list(STATS.values())].astype(float)

    # shift(1) drops the current match; rolling(5) averages up to 5 earlier ones (NaN skipped)
    for short, column in STATS.items():
        teams[short] = (teams.groupby("team_id")[column]
                        .transform(lambda s: s.shift(1).rolling(5, min_periods=1).mean()))

    wide = teams.pivot(index="match_id", columns="side", values=list(STATS))
    wide.columns = [f"{side}_{short}" for short, side in wide.columns]
    return load_features().set_index("match_id"), wide


def test_every_match_is_covered(both):
    view, pandas = both
    assert set(view.index) == set(pandas.index)


@pytest.mark.parametrize("column", [f"{side}_{short}" for side in ("home", "away") for short in STATS])
def test_view_equals_independent_calculation(both, column):
    view, pandas = both
    expected = pandas.loc[view.index, column].to_numpy(dtype=float)
    actual = view[column].to_numpy(dtype=float)
    assert np.allclose(actual, expected, equal_nan=True)


def test_first_match_of_each_team_has_no_form(both):
    view, _ = both
    # Each team has exactly one match with no earlier data, so one empty value per team
    empty = view["home_gf5"].isna().sum() + view["away_gf5"].isna().sum()
    teams = read_sql("SELECT COUNT(*) AS n FROM teams").n[0]
    assert empty == teams
