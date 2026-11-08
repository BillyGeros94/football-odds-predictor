import pytest
from src.elo import expected_home, update, margin_multiplier

def test_expected_home():
    assert expected_home(1700, 1500) == pytest.approx(0.817, abs=0.001)

def test_points_are_swapped():
    home, away = update(1700, 1500, "H")
    assert home + away == pytest.approx(3200)

def test_shock_defeat():
    # The worked example uses K = 20 without margin of victory
    home, away = update(1700, 1500, "A", k=20, margin=False)
    assert home == pytest.approx(1683.7, abs=0.1)

def test_margin_multiplier():
    assert margin_multiplier(0) == 1.0
    assert margin_multiplier(1) == 1.0
    assert margin_multiplier(-2) == 1.5
    assert margin_multiplier(4) == pytest.approx(15 / 8)

def test_bigger_win_moves_more():
    small, _ = update(1500, 1500, "H", k=20, goal_diff=1, margin=True)
    big, _ = update(1500, 1500, "H", k=20, goal_diff=4, margin=True)
    assert big > small
