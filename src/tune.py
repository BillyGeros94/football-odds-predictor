"""Tune the Elo settings on the tuning seasons (2019/20–2021/22).

For each combination, Elo is recalculated in memory (the database is not
touched), then a walk-forward logistic regression on elo_diff is scored.
The combination with the lowest log loss wins.

Run:
    python -m src.tune
"""
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss

from src.backtest import TUNE_SEASONS
from src.db import read_sql
from src.elo import run_elo
from src.features import load_features


def score_elo(matches, features, k, home_adv, margin=False, regress=0.0):
    """Average walk-forward log loss of a logistic regression on Elo calculated with these settings."""
    elo = run_elo(matches, k=k, home_adv=home_adv, margin=margin, regress=regress)

    # Swap the stored Elo columns for the newly calculated ratings
    df = features.drop(columns=["home_elo", "away_elo", "elo_diff"]).merge(elo, on="match_id")
    df["elo_diff"] = df["home_before"] - df["away_before"]

    losses = []
    for season in TUNE_SEASONS:
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
        SELECT match_id, match_date, league, season, home_team_id, away_team_id,
               home_goals, away_goals, result
        FROM matches ORDER BY match_date, match_id
    """)
    features = load_features()

    # Round 1 (done): K and home advantage. K = 20 was best; home advantage made no real difference.
    # Round 2: margin of victory and pulling ratings back between seasons, with home advantage fixed at 60.
    # Best: margin on, regress 0.4, K about 4–6 (1.0309). Chosen: K = 5, now the defaults in elo.py.
    results = []
    for margin in [False, True]:
        for regress in [0.0, 0.2, 0.3, 0.4, 0.5, 0.6]:
            for k in [5, 7.5, 10, 15, 20]:
                loss = score_elo(matches, features, k, 60, margin, regress)
                results.append((margin, regress, k, loss))

    df_results = pd.DataFrame(results, columns=["margin", "regress", "k", "loss"])
    df_results = df_results.sort_values("loss")
    print(df_results.head(12).to_string(index=False))
    print()
    print("Best per option:")
    print(df_results.groupby(["margin", "regress"])["loss"].min().unstack().round(4))
