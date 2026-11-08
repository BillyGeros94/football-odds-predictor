import pandas as pd
from src.features import load_features
from src.models import make_models

TUNE_SEASONS = ["1920", "2021", "2122"]

def walk_forward(df, seasons):
    all_preds = []

    for season in seasons:
        train, test =  df[df["season"] < season], df[df["season"] == season]
        for name, (model,cols) in make_models().items():
            model.fit(train[cols], train["result"])
            probs = model.predict_proba(test[cols])
            
            preds = test[["match_id", "season", "result"]].copy()
            preds["model"] = name
            preds[["prob_away", "prob_draw", "prob_home"]] = probs
            all_preds.append(preds)

    return pd.concat(all_preds, ignore_index=True)

if __name__ == "__main__":
    df = load_features()
    preds = walk_forward(df, TUNE_SEASONS)
    print(preds.shape)
    print(preds.head())