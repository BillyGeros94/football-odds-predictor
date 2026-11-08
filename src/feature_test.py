"""Test whether goals and shots on target add anything on top of Elo.

Each feature set is scored with the same walk-forward logistic regression
on the tuning seasons. Lower log loss is better.
"""
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from src.backtest import TUNE_SEASONS
from src.features import FEATURES, load_features

SETS = {
    "elo":         ["elo_diff"],
    "elo + goals": ["elo_diff", "home_gf5", "home_ga5", "away_gf5", "away_ga5"],
    "elo + sot":   ["elo_diff", "home_sot5", "home_sota5", "away_sot5", "away_sota5"],
    "elo + all":   FEATURES,
}


def make_model():
    return make_pipeline(
        SimpleImputer(strategy="median"),   # fills each team's empty first match
        StandardScaler(),                   # puts all features on the same scale
        LogisticRegression(max_iter=1000),
    )


def walk_forward_loss(df, cols):
    losses = []
    for season in TUNE_SEASONS:
        train = df[df["season"] < season]
        test = df[df["season"] == season]

        model = make_model()
        model.fit(train[cols], train["result"])
        probs = model.predict_proba(test[cols])
        losses.append(log_loss(test["result"], probs, labels=model.classes_))

    return losses


if __name__ == "__main__":
    df = load_features()

    rows = []
    for name, cols in SETS.items():
        losses = walk_forward_loss(df, cols)
        rows.append({"features": name,
                     **{season: loss for season, loss in zip(TUNE_SEASONS, losses)},
                     "average": sum(losses) / len(losses)})

    print(pd.DataFrame(rows).round(4).to_string(index=False))
