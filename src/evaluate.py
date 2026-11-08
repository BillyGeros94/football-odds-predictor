import pandas as pd
from sklearn.metrics import log_loss
from src.backtest import walk_forward, TUNE_SEASONS
from src.features import load_features
from src.db import read_sql

def market_probs():
    query = """
    SELECT m.match_id, m.season, m.result,
           o.close_away, o.close_draw, o.close_home
    FROM matches m
    JOIN odds o ON o.match_id = m.match_id
"""
    odds = read_sql(query)
    cols = ["close_away", "close_draw", "close_home"]
    odds[cols] = odds[cols].astype(float)

    implied = 1/odds[cols]
    probs = implied.div(implied.sum(axis=1), axis=0)
    
    return pd.DataFrame(
        {   "model": "market",
            "match_id": odds["match_id"],
            "season": odds["season"],
            "result": odds["result"],
            "prob_away": probs["close_away"],
            "prob_draw": probs["close_draw"],
            "prob_home": probs["close_home"]
        })

def brier(group):
    probs = group[["prob_away", "prob_draw", "prob_home"]].values
    actual = pd.get_dummies(group["result"]).reindex(columns=["A", "D", "H"], fill_value=0).values
    return ((probs - actual) ** 2).sum(axis=1).mean()

def score(preds):
    rows = []
    for name, group in preds.groupby("model"):
        probs = group[["prob_away", "prob_draw", "prob_home"]].values
        rows.append({"model": name,
                "log_loss": log_loss(group["result"], probs, labels=["A", "D", "H"]),
                "brier": brier(group)})
    return pd.DataFrame(rows).sort_values("log_loss")

if __name__ == "__main__":
    preds = walk_forward(load_features(), TUNE_SEASONS)
    market = market_probs()
    market = market[market["match_id"].isin(preds["match_id"])]   # same matches only
    print(score(pd.concat([preds, market])).round(4))
