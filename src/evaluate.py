"""Score the models against the bookmakers' closing odds on the tuning seasons.

The market is treated as a fourth model: its closing odds are turned into
probabilities, then everyone is scored on the same matches with
- log loss: punishes confident wrong predictions hardest (lower is better)
- Brier score: squared distance from what happened (lower is better)

Run:
    python -m src.evaluate
"""
import pandas as pd
from sklearn.metrics import log_loss

from src.backtest import TUNE_SEASONS, walk_forward
from src.db import read_sql
from src.features import load_features


def remove_margin(odds):
    """Turn decimal odds (one column per outcome) into probabilities that sum to 1.

    1 / odds adds up to more than 1 because of the bookmaker's margin;
    dividing each row by its total removes it.
    """
    implied = 1 / odds
    probs = implied.div(implied.sum(axis=1), axis=0)

    return probs


def market_probs():
    """Turn closing odds into probabilities, in the same format as the model predictions."""
    query = """
        SELECT m.match_id, m.season, m.result,
               o.close_away, o.close_draw, o.close_home
        FROM matches m
        JOIN odds o ON o.match_id = m.match_id
    """
    odds = read_sql(query)
    cols = ["close_away", "close_draw", "close_home"]
    odds[cols] = odds[cols].astype(float)

    # Remove the bookmaker's margin
    probs = remove_margin(odds[cols])

    return pd.DataFrame({
        "model": "market",
        "match_id": odds["match_id"],
        "season": odds["season"],
        "result": odds["result"],
        "prob_away": probs["close_away"],
        "prob_draw": probs["close_draw"],
        "prob_home": probs["close_home"],
    })


def brier(group):
    """Brier score: the squared gap between the probabilities and what happened, averaged."""
    probs = group[["prob_away", "prob_draw", "prob_home"]].values
    # What happened as 0s and 1s, e.g. a home win is [0, 0, 1]
    actual = pd.get_dummies(group["result"]).reindex(columns=["A", "D", "H"], fill_value=0).values
    return ((probs - actual) ** 2).sum(axis=1).mean()


def score(preds):
    """Return log loss and Brier score for each model, best first."""
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
