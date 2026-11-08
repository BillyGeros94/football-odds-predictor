import pandas as pd
from src.features import load_features
from src.models import make_models

TUNE_SEASONS = ["1920", "2021", "2122"]
FINAL_SEASONS = ["2223", "2324", "2425", "2526", "2627"]   # run once, at the end

PROB_COLS = ["prob_away", "prob_draw", "prob_home"]


def add_average(preds):
    # The main model: average of logistic and boosting for each match.
    # Chosen on the tuning seasons, where it beat both (1.0271 vs 1.0292)
    pair = preds[preds["model"].isin(["logistic", "boosting"])]
    avg = pair.groupby(["match_id", "season", "result"], as_index=False)[PROB_COLS].mean()
    avg["model"] = "average"
    return pd.concat([preds, avg], ignore_index=True)


def walk_forward(df, seasons):
    all_preds = []

    for season in seasons:
        train, test = df[df["season"] < season], df[df["season"] == season]
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
