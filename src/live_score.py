"""Score the live predictions against the actual results and the market.

Only predictions whose match has been played appear in the live_record view.

Run:
    python -m src.live_score
"""
import pandas as pd

from src.db import read_sql
from src.evaluate import market_probs, score

PROB_COLS = ["prob_away", "prob_draw", "prob_home"]

if __name__ == "__main__":
    live = read_sql("SELECT * FROM live_record")

    if live.empty:
        print("No scored predictions yet")
        raise SystemExit(0)

    live[PROB_COLS] = live[PROB_COLS].astype(float)
    with_odds = live.dropna(subset=["close_home"])

    preds = with_odds[["match_id", "model", "result"] + PROB_COLS]

    market = market_probs()
    market = market[market["match_id"].isin(with_odds["match_id"])]
    scores = score(pd.concat([preds, market])).round(4)
    
    print(f"Scored {len(preds)} predictions")
    print(scores.to_string(index=False))
