import pandas as pd
from src.db import get_connection, read_sql

K = 20
HOME_ADVANTAGE = 60
NEW_TEAM_RATING = {"E0": 1500, "E1": 1400}

def expected_home(home_rating, away_rating, home_adv=HOME_ADVANTAGE):
    return 1 / (1 + 10 ** ((away_rating - (home_rating + home_adv)) / 400))


def update(home_rating, away_rating, result, k=K, home_adv=HOME_ADVANTAGE):
    score = {"H": 1, "D": 0.5, "A": 0}[result]
    expected = expected_home(home_rating, away_rating, home_adv)
    change = k * (score - expected)
    return home_rating + change, away_rating - change

def run_elo(matches, k=K, home_adv=HOME_ADVANTAGE):
    ratings = {}
    rows = []

    for m in matches.itertuples(index=False):
        home_rating = ratings.get(m.home_team_id, NEW_TEAM_RATING[m.league])
        away_rating = ratings.get(m.away_team_id, NEW_TEAM_RATING[m.league])
        new_home, new_away = update(home_rating, away_rating, m.result, k, home_adv)
        rows.append((m.match_id, home_rating, away_rating, new_home, new_away))
        ratings[m.home_team_id] = new_home
        ratings[m.away_team_id] = new_away
    return pd.DataFrame(rows, columns=["match_id", "home_before", "away_before",
                                       "home_after", "away_after"])

def save_elo(conn, elo):
    clean = elo.astype(object).where(elo.notna(), None)
    rows = clean.values.tolist()
        
    sql = """
        INSERT INTO elo_ratings(
            match_id, home_before, away_before, home_after, away_after)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (match_id) DO UPDATE SET
        home_before = EXCLUDED.home_before,
        away_before = EXCLUDED.away_before,
        home_after  = EXCLUDED.home_after,
        away_after  = EXCLUDED.away_after
    """
    
    with conn.cursor() as cur:
        cur.executemany(sql, rows)
    

if __name__ == "__main__":
    matches = read_sql("""
        SELECT match_id, match_date, league, home_team_id, away_team_id, result
        FROM matches
        ORDER BY match_date, match_id
    """)
    elo = run_elo(matches)

    with get_connection() as conn:
        save_elo(conn, elo)
        count = conn.execute("SELECT COUNT(*) FROM elo_ratings").fetchone()[0]

    print(count)

