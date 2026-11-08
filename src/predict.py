"""Predict upcoming fixtures, save the predictions and export them for the public record.

Steps:
1. Read data/fixtures/fixtures.csv and keep Premier League and Championship games
2. Look up each team's current form in the team_current view
3. Train logistic and boosting on every finished match and average their probabilities
4. Save predictions for matches after today, stamped with the time (never overwritten)
5. Export this run's new predictions to predictions/, which the workflow commits

Run the day before the matches:
    python -m src.predict
"""
from datetime import date, timezone
from pathlib import Path

import pandas as pd

from src.db import get_connection, read_sql
from src.features import FEATURES, load_features
from src.models import make_models


def load_fixtures(path):
    """Read the fixtures file and keep only E0 and E1 matches."""
    # utf-8-sig removes the invisible BOM character at the start of this file
    df = pd.read_csv(path, encoding="utf-8-sig")
    df = df[df["Div"].isin(["E0", "E1"])].copy()
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, format="mixed").dt.date
    return df[["Div", "Date", "HomeTeam", "AwayTeam"]]


def build_features(fixtures):
    """Attach each team's current Elo and last-5 averages, with the same names the models use."""
    team_ids = dict(read_sql("SELECT name, team_id FROM teams").values.tolist())
    current = read_sql("SELECT * FROM team_current")

    fixtures["home_team_id"] = fixtures["HomeTeam"].map(team_ids)
    fixtures["away_team_id"] = fixtures["AwayTeam"].map(team_ids)

    # A team name the database has never seen (for example a newly promoted club
    # before its first match is loaded) would silently drop the fixture, so say so
    unknown = set(fixtures.loc[fixtures["home_team_id"].isna(), "HomeTeam"]) | \
              set(fixtures.loc[fixtures["away_team_id"].isna(), "AwayTeam"])
    if unknown:
        print("Skipping fixtures with unknown teams:", ", ".join(sorted(unknown)))

    # add_prefix renames team_id → home_team_id and sot5 → home_sot5, so the merge
    # joins on the right column and the columns match the FEATURES names
    df = (fixtures
          .merge(current.add_prefix("home_"), on="home_team_id")
          .merge(current.add_prefix("away_"), on="away_team_id"))

    df["home_elo_after"] = df["home_elo_after"].astype(float)
    df["away_elo_after"] = df["away_elo_after"].astype(float)
    df[FEATURES[1:]] = df[FEATURES[1:]].astype(float)
    df["elo_diff"] = df["home_elo_after"] - df["away_elo_after"]
    return df


def save_predictions(conn, df):
    """Save predictions for matches after today. A prediction already saved is never overwritten."""
    # Strictly after today, so every saved prediction was made before kick-off
    df = df[df["Date"] > date.today()]

    if df.empty:
        print("No upcoming matches to save")
        return

    df = df.copy()
    df["model"] = "average"

    clean = df.astype(object).where(df.notna(), None)
    columns = ["Date", "home_team_id", "away_team_id", "model",
               "prob_home", "prob_draw", "prob_away"]
    rows = clean[columns].values.tolist()

    # created_at is filled in by the database (DEFAULT now())
    sql = """
        INSERT INTO predictions (
            match_date, home_team_id, away_team_id, model, prob_home,
            prob_draw, prob_away)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (match_date, home_team_id, away_team_id, model) DO NOTHING
    """

    with conn.cursor() as cur:
        cur.executemany(sql, rows)


def export_new_predictions(conn, folder="predictions"):
    """Write the predictions saved in this run to a CSV that the workflow commits.

    The public git history then proves when each prediction was made. Inside one
    transaction now() never changes, so created_at = now() picks exactly the rows
    inserted by this run (not ones kept from earlier runs).
    """
    query = """
        SELECT p.match_date, h.name AS home_team, a.name AS away_team, p.model,
               p.prob_home, p.prob_draw, p.prob_away, p.created_at
        FROM predictions p
        JOIN teams h ON h.team_id = p.home_team_id
        JOIN teams a ON a.team_id = p.away_team_id
        WHERE p.created_at = now()
        ORDER BY p.match_date, h.name
    """
    result = conn.execute(query)
    new = pd.DataFrame(result.fetchall(), columns=[c.name for c in result.description])
    if new.empty:
        print("No new predictions to export")
        return

    # Fair odds = 1 / probability (no bookmaker margin)
    for outcome in ["home", "draw", "away"]:
        new[f"prob_{outcome}"] = new[f"prob_{outcome}"].astype(float)
        new[f"odds_{outcome}"] = (1 / new[f"prob_{outcome}"]).round(2)

    made = new["created_at"].iloc[0].astimezone(timezone.utc)
    new["created_at"] = made.strftime("%Y-%m-%d %H:%M:%S UTC")

    Path(folder).mkdir(exist_ok=True)
    path = Path(folder) / f"{made:%Y-%m-%d_%H%M}.csv"
    new.to_csv(path, index=False)
    print(f"Exported {len(new)} predictions to {path}")


if __name__ == "__main__":
    # The main model: average of logistic and boosting, trained on every finished match
    train = load_features()
    fixtures = build_features(load_fixtures("data/fixtures/fixtures.csv"))
    if fixtures.empty:
        print("No Premier League or Championship fixtures in the file")
        raise SystemExit(0)

    all_probs = []
    for name in ["logistic", "boosting"]:
        model, cols = make_models()[name]
        model.fit(train[cols], train["result"])
        all_probs.append(model.predict_proba(fixtures[cols]))
    probs = sum(all_probs) / len(all_probs)

    # Columns come in class order: A, D, H
    fixtures["prob_away"] = probs[:, 0]
    fixtures["prob_draw"] = probs[:, 1]
    fixtures["prob_home"] = probs[:, 2]

    fixtures["odds_home"] = 1 / fixtures["prob_home"]
    fixtures["odds_draw"] = 1 / fixtures["prob_draw"]
    fixtures["odds_away"] = 1 / fixtures["prob_away"]

    print(fixtures[["Date", "HomeTeam", "AwayTeam", "prob_home", "prob_draw", "prob_away",
                    "odds_home", "odds_draw", "odds_away"]].round(2).to_string())

    # Saving and exporting share one transaction, which export_new_predictions relies on
    with get_connection() as conn:
        save_predictions(conn, fixtures)
        export_new_predictions(conn)
        print(conn.execute("SELECT COUNT(*) FROM predictions").fetchone()[0])
