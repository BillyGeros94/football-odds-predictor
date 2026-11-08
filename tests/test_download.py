"""Tests for src/download.py. They never contact the website."""
from datetime import date

from src.download import looks_like_csv, season_code


def test_season_code_autumn():
    assert season_code(date(2026, 11, 8)) == "2627"


def test_season_code_spring():
    assert season_code(date(2027, 3, 1)) == "2627"


def test_season_code_new_season_in_july():
    assert season_code(date(2027, 7, 1)) == "2728"


def test_season_code_century():
    assert season_code(date(2099, 9, 1)) == "9900"


def test_accepts_csv_with_and_without_bom():
    assert looks_like_csv(b"Div,Date,Time,HomeTeam\nE0,...")
    assert looks_like_csv(b"\xef\xbb\xbfDiv,Date,Time,HomeTeam\nE0,...")


def test_rejects_html_error_page():
    assert not looks_like_csv(b"<!DOCTYPE html><html>Not found</html>")
