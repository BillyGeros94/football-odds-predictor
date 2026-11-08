"""Elo ratings: one strength number per team, updated after every match.

Before a match, the rating gap gives the home team's expected score
(win = 1, draw = 0.5, loss = 0). After it, both ratings move by
K × (actual − expected): surprises move them a lot, expected results a little.

On top of plain Elo, two tuned extras (see src/tune.py):
- margin of victory: bigger wins move ratings more
- pull-back: each summer, ratings move part of the way back to the league average

Run to recalculate every rating and save it to the elo_ratings table:
    python -m src.elo
"""
import pandas as pd

from src.db import get_connection, read_sql

# Tuned on 2019/20–2021/22 with src/tune.py (log loss 1.0348 → 1.0309)
K = 5                  # how fast ratings move
HOME_ADVANTAGE = 60    # rating points added to the home team when working out expectations
NEW_TEAM_RATING = {"E0": 1500, "E1": 1400}   # starting rating, by the league a team first appears in
MARGIN = True          # scale rating changes by goal difference
REGRESS = 0.4          # share of the gap to the league average removed each summer


def expected_home(home_rating, away_rating, home_adv=HOME_ADVANTAGE):
    """The home team's expected score, between 0 and 1. Equal teams give 0.5 before home advantage."""
    return 1 / (1 + 10 ** ((away_rating - (home_rating + home_adv)) / 400))


def margin_multiplier(goal_diff):
    """How much a win's size scales K: 1 goal = 1, 2 goals = 1.5, 3+ goals = (11 + n) / 8."""
    goal_diff = abs(goal_diff)
    if goal_diff <= 1:
        return 1.0
    if goal_diff == 2:
        return 1.5
    return (11 + goal_diff) / 8


def update(home_rating, away_rating, result, k=K, home_adv=HOME_ADVANTAGE,
           goal_diff=0, margin=MARGIN):
    """Return both teams' new ratings after a match. result is "H", "D" or "A"."""
    score = {"H": 1, "D": 0.5, "A": 0}[result]
    expected = expected_home(home_rating, away_rating, home_adv)
    if margin:
        k = k * margin_multiplier(goal_diff)
    change = k * (score - expected)
    # Points are swapped: what the home team gains, the away team loses
    return home_rating + change, away_rating - change


def pull_back(team, ratings, last_league, regress):
    """Move a team's rating part of the way towards the average of the league it last played in."""
    league = last_league[team]
    peers = [ratings[t] for t in ratings if last_league[t] == league]
    average = sum(peers) / len(peers)
    return ratings[team] - regress * (ratings[team] - average)


def run_elo(matches, k=K, home_adv=HOME_ADVANTAGE, margin=MARGIN, regress=REGRESS):
    """Go through the matches in date order and return each team's rating before and after each one.

    `matches` must be sorted by date. The "before" ratings are the ones the
    models may use, since they are known at kick-off.
    """
    ratings = {}       # team_id → current rating
    last_season = {}   # team_id → season of its last match
    last_league = {}   # team_id → league of its last match
    rows = []

    for m in matches.itertuples(index=False):
        # At a team's first match of a new season, pull its rating back towards average
        if regress:
            for team in (m.home_team_id, m.away_team_id):
                if team in ratings and last_season[team] != m.season:
                    ratings[team] = pull_back(team, ratings, last_league, regress)
                    last_season[team] = m.season

        # A team seen for the first time gets its league's starting rating
        home_rating = ratings.get(m.home_team_id, NEW_TEAM_RATING[m.league])
        away_rating = ratings.get(m.away_team_id, NEW_TEAM_RATING[m.league])

        goal_diff = m.home_goals - m.away_goals if margin else 0
        new_home, new_away = update(home_rating, away_rating, m.result, k, home_adv,
                                    goal_diff, margin)
        rows.append((m.match_id, home_rating, away_rating, new_home, new_away))

        # The ratings after this match become the ratings before each team's next one
        for team, rating in ((m.home_team_id, new_home), (m.away_team_id, new_away)):
            ratings[team] = rating
            last_season[team] = m.season
            last_league[team] = m.league

    return pd.DataFrame(rows, columns=["match_id", "home_before", "away_before",
                                       "home_after", "away_after"])


def save_elo(conn, elo):
    """Save the ratings. Existing rows are replaced, so retuning K updates every match."""
    clean = elo.astype(object).where(elo.notna(), None)
    rows = clean.values.tolist()

    # DO UPDATE instead of DO NOTHING: EXCLUDED is the new row that hit the conflict
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
    # Date order is essential: each rating depends on every match before it
    matches = read_sql("""
        SELECT match_id, match_date, league, season, home_team_id, away_team_id,
               home_goals, away_goals, result
        FROM matches
        ORDER BY match_date, match_id
    """)
    elo = run_elo(matches)

    with get_connection() as conn:
        save_elo(conn, elo)
        count = conn.execute("SELECT COUNT(*) FROM elo_ratings").fetchone()[0]

    print(count)
