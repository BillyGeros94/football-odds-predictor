"""Tests for the walk-forward split in src/backtest.py: a model must never train on the
season it is tested on, or on anything after it. No database needed."""
import pandas as pd

from src.backtest import season_split

# Three seasons, three matches each, with match IDs 1 to 9
DF = pd.DataFrame({
    "match_id": range(1, 10),
    "season": ["1516"] * 3 + ["1617"] * 3 + ["1718"] * 3,
})


def test_train_is_only_earlier_seasons():
    train, _ = season_split(DF, "1718")
    assert set(train["season"]) == {"1516", "1617"}


def test_test_is_only_that_season():
    _, test = season_split(DF, "1718")
    assert (test["season"] == "1718").all() and len(test) == 3


def test_no_match_in_both():
    train, test = season_split(DF, "1617")
    assert not set(train["match_id"]) & set(test["match_id"])


def test_later_seasons_are_never_used():
    train, test = season_split(DF, "1617")
    assert "1718" not in set(train["season"]) | set(test["season"])


def test_first_season_has_no_training_data():
    train, _ = season_split(DF, "1516")
    assert train.empty


def test_season_codes_sort_in_time_order():
    # The split compares codes as text, which only works if text order is time order
    seasons = ["1516", "1617", "1718", "1819", "1920", "2021", "2122", "2223", "2324",
               "2425", "2526", "2627"]
    assert sorted(seasons) == seasons
