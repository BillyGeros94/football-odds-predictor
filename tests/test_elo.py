import pytest
from src.elo import expected_home, update

def test_expected_home():
    assert expected_home(1700, 1500) == pytest.approx(0.817, abs=0.001)

def test_points_are_swapped():
    home, away = update(1700, 1500, "H")
    assert home + away == pytest.approx(3200)

def test_shock_defeat():
    home, away = update(1700, 1500, "A")
    assert home == pytest.approx(1683.7, abs=0.1)
