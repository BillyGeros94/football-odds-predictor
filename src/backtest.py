"""Walk-forward backtest: predict each season using only the seasons before it.

This copies real life. To predict 2020/21, the models train on 2015/16 to
2019/20 only, so they never learn from the future. Every prediction is kept,
so the models and the market can later be scored on exactly the same matches.

Seasons are split in two:
- tuning seasons: used for every choice (settings, features, models)
- final seasons: run once at the end, in src/final_test.py

Run to check the backtest:
    python -m src.backtest
"""
import pandas as pd

from src.features import load_features
from src.models import make_models

TUNE_SEASONS = ["1920", "2021", "2122"]
FINAL_SEASONS = ["2223", "2324", "2425", "2526", "2627"]   # run once, at the end

# predict_proba returns columns in alphabetical class order: A, D, H
PROB_COLS = ["prob_away", "prob_draw", "prob_home"]


def add_average(preds):
    """Add the main model: the average of logistic and boosting for each match.

    Chosen on the tuning seasons, where it beat both (1.0271 against 1.0292).
    """
    pair = preds[preds["model"].isin(["logistic", "boosting"])]
    avg = pair.groupby(["match_id", "season", "result"], as_index=False)[PROB_COLS].mean()
    avg["model"] = "average"
    return pd.concat([preds, avg], ignore_index=True)


def season_split(df, season):
    """Train on every season before `season`, test on `season` only.

    Season codes sort correctly as text: "1920" < "2021".
    """
    return df[df["season"] < season], df[df["season"] == season]


def walk_forward(df, seasons):
    """Return every model's predictions for every match in `seasons`, one row per match per model."""
    all_preds = []

    for season in seasons:
        train, test = season_split(df, season)

        # make_models() inside the loop gives untrained models for every season
        for name, (model, cols) in make_models().items():
            model.fit(train[cols], train["result"])
            probs = model.predict_proba(test[cols])

            preds = test[["match_id", "season", "result"]].copy()
            preds["model"] = name
            preds[PROB_COLS] = probs
            all_preds.append(preds)

    return add_average(pd.concat(all_preds, ignore_index=True))


if __name__ == "__main__":
    df = load_features()
    preds = walk_forward(df, TUNE_SEASONS)
    print(preds.shape)
    print(preds.head())
