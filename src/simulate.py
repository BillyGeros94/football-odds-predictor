"""Simulate the rest of the season to get each team's chances of every outcome.

In a league where every team plays every other team once at home and once away,
the remaining fixtures are all pairings minus the ones already played, even
without dates. Each remaining match gets probabilities from the same models as
the live predictions; the rest of the season is then played out N_SIMS times and
each team's finishing position counted.

Assumptions, also stated in the app:
- ratings and form stay as they are now for the rest of the season
- ties on points are broken by current goal difference, then at random
- points deductions are not included

Run (saves one row per team to season_simulations; skipped when no new results
have arrived since the last simulation):
    python -m src.simulate
"""
import numpy as np
import pandas as pd

from src.db import get_connection, read_sql
from src.features import load_features
from src.models import make_models
from src.predict import build_features

N_SIMS = 10_000
TEAMS_PER_LEAGUE = {"E0": 20, "E1": 24}


def current_season():
    season = read_sql("SELECT MAX(season) AS s FROM matches").s[0]
    if not str(season).isdigit():   # it goes into SQL below, so make sure it is a season code
        raise ValueError(f"Unexpected season code: {season}")
    return season


def already_simulated(season, matches_played):
    """True if the latest simulation was for this season with exactly these matches played.

    Each run of the workflow (and its backup run) would otherwise add a near-identical
    simulation whenever no new results have arrived, differing only by random noise.
    """
    try:
        last = read_sql("""
            SELECT season, SUM(played) AS team_games FROM season_simulations
            WHERE run_at = (SELECT MAX(run_at) FROM season_simulations)
            GROUP BY season
        """)
    except Exception:   # the table does not exist before the first simulation
        return False
    # Every match counts once for each of its two teams
    return (not last.empty and last.season[0] == season
            and int(last.team_games[0]) == 2 * matches_played)


def league_table(played):
    """Points, goal difference and matches played so far for each team in one league."""
    home = pd.DataFrame({"team_id": played["home_team_id"],
                         "points": played["result"].map({"H": 3, "D": 1, "A": 0}),
                         "gd": played["home_goals"] - played["away_goals"]})
    away = pd.DataFrame({"team_id": played["away_team_id"],
                         "points": played["result"].map({"H": 0, "D": 1, "A": 3}),
                         "gd": played["away_goals"] - played["home_goals"]})
    both = pd.concat([home, away])
    return both.groupby("team_id").agg(played=("points", "size"),
                                       points=("points", "sum"),
                                       gd=("gd", "sum"))


def remaining_fixtures(played, team_ids, names):
    """Every home/away pairing not played yet, with team names for build_features."""
    done = set(zip(played["home_team_id"], played["away_team_id"]))
    rows = [(h, a) for h in team_ids for a in team_ids if h != a and (h, a) not in done]
    fixtures = pd.DataFrame(rows, columns=["home_id", "away_id"])
    fixtures["HomeTeam"] = fixtures["home_id"].map(names)
    fixtures["AwayTeam"] = fixtures["away_id"].map(names)
    return fixtures[["HomeTeam", "AwayTeam"]]


def match_probabilities(fixtures, models):
    """Average of logistic and boosting, exactly as in predict.py. Columns: A, D, H."""
    df = build_features(fixtures.copy())
    probs = sum(model.predict_proba(df[cols]) for model, cols in models) / len(models)
    return df[["home_team_id", "away_team_id"]].to_numpy(), probs


def simulate_league(table, pairs, probs, rng):
    """Play the remaining matches N_SIMS times and return each team's finishing positions."""
    team_ids = table.index.to_numpy()
    index = {team: i for i, team in enumerate(team_ids)}
    n_teams = len(team_ids)

    # One draw per simulation per match: home win, draw or away win
    draw = rng.random((N_SIMS, len(pairs)))
    home_win = draw < probs[:, 2]
    is_draw = (draw >= probs[:, 2]) & (draw < probs[:, 2] + probs[:, 1])
    away_win = ~home_win & ~is_draw
    home_points = 3 * home_win + is_draw
    away_points = 3 * away_win + is_draw

    # Matrices that send each match's points to the right team: (simulations × matches) @ (matches × teams)
    home_onehot = np.zeros((len(pairs), n_teams))
    away_onehot = np.zeros((len(pairs), n_teams))
    for j, (home, away) in enumerate(pairs):
        home_onehot[j, index[home]] = 1
        away_onehot[j, index[away]] = 1
    final_points = table["points"].to_numpy() + home_points @ home_onehot + away_points @ away_onehot

    # Rank by points, then current goal difference, then at random
    gd = table["gd"].to_numpy()
    sort_key = final_points + gd / 1_000 + rng.random((N_SIMS, n_teams)) / 1_000_000
    order = np.argsort(-sort_key, axis=1)
    position = np.empty_like(order)
    position[np.arange(N_SIMS)[:, None], order] = np.arange(1, n_teams + 1)
    return final_points, position


def simulate():
    """Return one row per team in the current season with its chances of each outcome."""
    season = current_season()
    played_all = read_sql(f"""
        SELECT league, home_team_id, away_team_id, home_goals, away_goals, result
        FROM matches WHERE season = '{season}'
    """)
    if already_simulated(season, len(played_all)):
        print("No new results since the last simulation, skipping")
        return pd.DataFrame()
    names = dict(read_sql("SELECT team_id, name FROM teams").values.tolist())

    # Train once, as predict.py does: on every finished match
    train = load_features()
    models = []
    for name in ["logistic", "boosting"]:
        model, cols = make_models()[name]
        model.fit(train[cols], train["result"])
        models.append((model, cols))

    rng = np.random.default_rng()
    results = []
    for league, expected_teams in TEAMS_PER_LEAGUE.items():
        played = played_all[played_all["league"] == league]
        table = league_table(played)

        # Early in a season some teams have not played yet, so the team list is incomplete
        if len(table) != expected_teams:
            print(f"{league}: {len(table)} of {expected_teams} teams have played, skipping")
            continue

        fixtures = remaining_fixtures(played, table.index.tolist(), names)
        if fixtures.empty:
            print(f"{league}: season finished, nothing to simulate")
            continue

        pairs, probs = match_probabilities(fixtures, models)
        final_points, position = simulate_league(table, pairs, probs, rng)

        out = table.reset_index()[["team_id", "played", "points"]]
        out["season"], out["league"] = season, league
        out["expected_points"] = final_points.mean(axis=0).round(1)
        out["p_title"] = (position == 1).mean(axis=0)
        out["p_top4"] = (position <= 4).mean(axis=0) if league == "E0" else None
        out["p_promotion"] = (position <= 2).mean(axis=0) if league == "E1" else None
        out["p_playoffs"] = ((position >= 3) & (position <= 6)).mean(axis=0) if league == "E1" else None
        out["p_relegation"] = (position > expected_teams - 3).mean(axis=0)
        results.append(out)
        print(f"{league}: simulated {len(fixtures)} remaining matches {N_SIMS:,} times")

    return pd.concat(results, ignore_index=True) if results else pd.DataFrame()


def save_simulation(conn, sims):
    """Append this run to season_simulations. run_at is filled in by the database."""
    columns = ["season", "league", "team_id", "played", "points", "expected_points",
               "p_title", "p_top4", "p_promotion", "p_playoffs", "p_relegation"]
    clean = sims[columns].astype(object).where(sims[columns].notna(), None)
    sql = f"""
        INSERT INTO season_simulations ({", ".join(columns)})
        VALUES ({", ".join(["%s"] * len(columns))})
    """
    with conn.cursor() as cur:
        cur.executemany(sql, clean.values.tolist())


if __name__ == "__main__":
    sims = simulate()
    if sims.empty:
        print("Nothing to simulate")
        raise SystemExit(0)

    with get_connection() as conn:
        save_simulation(conn, sims)
    print(f"Saved {len(sims)} teams")
