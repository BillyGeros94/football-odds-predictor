import pandas as pd
from src.db import read_sql
from src.features import FEATURES, load_features
from src.models import make_models
from src.db import get_connection
from datetime import date


def load_fixtures(path):
    df = pd.read_csv(path, encoding="utf-8-sig")
    df = df[df["Div"].isin(["E0", "E1"])].copy()
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, format="mixed").dt.date
    return df[["Div", "Date", "HomeTeam", "AwayTeam"]]

def build_features(fixtures):
    team_ids = dict(read_sql("SELECT name, team_id FROM teams").values.tolist())
    current = read_sql("SELECT * FROM team_current")

    fixtures["home_team_id"] = fixtures["HomeTeam"].map(team_ids)
    fixtures["away_team_id"] = fixtures["AwayTeam"].map(team_ids)

    df = (fixtures
          .merge(current.add_prefix("home_"), on="home_team_id")
          .merge(current.add_prefix("away_"), on="away_team_id"))

    df["home_elo_after"] = df["home_elo_after"].astype(float)
    df["away_elo_after"] = df["away_elo_after"].astype(float)
    df[FEATURES[1:]] = df[FEATURES[1:]].astype(float)
    df["elo_diff"] = df["home_elo_after"] - df["away_elo_after"]
    return df

def save_predictions(conn, df):
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
        
    sql = """
        INSERT INTO predictions (
            match_date, home_team_id, away_team_id, model, prob_home,
            prob_draw , prob_away)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (match_date, home_team_id, away_team_id, model) DO NOTHING
    """
    
    with conn.cursor() as cur:
        cur.executemany(sql, rows)


if __name__ == "__main__":
    # The main model: average of logistic and boosting, trained on every finished match
    train = load_features()
    fixtures = build_features(load_fixtures("data/fixtures/fixtures.csv"))

    all_probs = []
    for name in ["logistic", "boosting"]:
        model, cols = make_models()[name]
        model.fit(train[cols], train["result"])
        all_probs.append(model.predict_proba(fixtures[cols]))
    probs = sum(all_probs) / len(all_probs)

    fixtures["prob_away"] = probs[:, 0]
    fixtures["prob_draw"] = probs[:, 1]
    fixtures["prob_home"] = probs[:, 2]

    fixtures["odds_home"] = 1 / fixtures["prob_home"]
    fixtures["odds_draw"] = 1 / fixtures["prob_draw"]
    fixtures["odds_away"] = 1 / fixtures["prob_away"]

    print(fixtures[["Date", "HomeTeam", "AwayTeam", "prob_home", "prob_draw", "prob_away", "odds_home", "odds_draw", "odds_away"]].round(2))
    with get_connection() as conn:
        save_predictions(conn, fixtures)
        print(conn.execute("SELECT COUNT(*) FROM predictions").fetchone()[0])