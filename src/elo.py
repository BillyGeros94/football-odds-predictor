import pandas as pd
from src.db import read_sql

K = 20
HOME_ADVANTAGE = 60
NEW_TEAM_RATING = {"E0": 1500, "E1": 1400}

def expected_home(home_rating, away_rating):
    return 1 / (1 + 10 ** ((away_rating - (home_rating + HOME_ADVANTAGE)) / 400))


def update(home_rating, away_rating, result):
    score = {"H": 1, "D": 0.5, "A": 0}[result]
    expected = expected_home(home_rating, away_rating)
    change = K * (score - expected)
    return home_rating + change, away_rating - change

def run_elo(matches):
    ratings = {}
    rows = []

    for m in matches.itertuples(index=False):
        home_rating = ratings.get(m.home_team_id, NEW_TEAM_RATING[m.league])
        away_rating = ratings.get(m.away_team_id, NEW_TEAM_RATING[m.league])
        new_home, new_away = update(home_rating, away_rating, m.result)
        rows.append((m.match_id, home_rating, away_rating, new_home, new_away))
        ratings[m.home_team_id] = new_home
        ratings[m.away_team_id] = new_away
    return pd.DataFrame(rows, columns=["match_id", "home_before", "away_before",
                                       "home_after", "away_after"])

if __name__ == "__main__":
    matches = read_sql("""
        SELECT match_id, match_date, league, home_team_id, away_team_id, result
        FROM matches
        ORDER BY match_date, match_id
    """)
    elo = run_elo(matches)
    print(len(elo))
    print(elo.tail())
