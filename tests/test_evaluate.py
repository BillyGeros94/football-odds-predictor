"""Tests for remove_margin in src/evaluate.py, which turns bookmaker odds into the
market probabilities every model is compared against. No database needed."""
import pandas as pd
import pytest

from src.evaluate import remove_margin

ODDS = pd.DataFrame({"away": [4.0, 1.5], "draw": [3.5, 4.2], "home": [2.0, 6.5]})


def test_probabilities_sum_to_one():
    probs = remove_margin(ODDS)
    assert probs.sum(axis=1).tolist() == pytest.approx([1.0, 1.0])


def test_margin_is_removed():
    # 1/odds adds up to more than 1 before; exactly 1 after
    assert (1 / ODDS).sum(axis=1).gt(1).all()
    assert remove_margin(ODDS).sum(axis=1).tolist() == pytest.approx([1.0, 1.0])


def test_shorter_odds_mean_higher_probability():
    probs = remove_margin(ODDS)
    # Row 1: home 2.0 < draw 3.5 < away 4.0, so home > draw > away
    assert probs.loc[0, "home"] > probs.loc[0, "draw"] > probs.loc[0, "away"]
    # Row 2: away 1.5 is the favourite
    assert probs.loc[1].idxmax() == "away"


def test_fair_odds_are_unchanged():
    # Odds with no margin (1/2 + 1/4 + 1/4 = 1) should give exactly 1 / odds
    fair = pd.DataFrame({"away": [4.0], "draw": [4.0], "home": [2.0]})
    assert remove_margin(fair).iloc[0].tolist() == pytest.approx([0.25, 0.25, 0.5])


def test_columns_and_rows_are_kept():
    probs = remove_margin(ODDS)
    assert list(probs.columns) == list(ODDS.columns) and len(probs) == len(ODDS)
