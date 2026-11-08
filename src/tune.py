from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss
import pandas as pd

from src.db import read_sql
from src.elo import run_elo
from src.features import load_features
from src.backtest import TUNE_SEASONS

def score_elo(matches, features, k, home_adv):
    elo = run_elo(matches, k=k, home_adv=home_adv)

    df = features.drop(columns=["home_elo", "away_elo", "elo_diff"]).merge(elo, on="match_id")
    df["elo_diff"] = df["home_before"] - df["away_before"]

    losses = []
    for  season in TUNE_SEASONS:
        train = df[df["season"] < season]
        test = df[df["season"] == season]
        model = LogisticRegression(max_iter=1000)
        model.fit(train[["elo_diff"]], train["result"])

        pred = model.predict_proba(test[["elo_diff"]])
        loss = log_loss(test["result"], pred, labels=model.classes_)
        losses.append(loss)
    return sum(losses) / len(losses)

if __name__ == "__main__":
    matches = read_sql("""
        SELECT match_id, match_date, league, home_team_id, away_team_id, result
        FROM matches ORDER BY match_date, match_id
    """)
    features = load_features()

    results = []
    for k in [10, 15, 20, 25, 30, 40]:
        for home_adv in [0, 30, 60, 90]:
            loss = score_elo(matches, features, k, home_adv)
            results.append((k, home_adv, loss))

    df_results = pd.DataFrame(results, columns=["k", "home_adv", "loss"])
    df_results = df_results.sort_values("loss")
    print(df_results.head(10))
