"""Score the live predictions against the actual results and the market.

Only predictions whose match has been played appear in the live_record view.

Run:
    python -m src.live_score
"""
import pandas as pd

from src.db import read_sql
from src.evaluate import remove_margin, score


PROB_COLS = ["prob_away", "prob_draw", "prob_home"]


def market_rows(live, prefix, name):
    """Turn one set of odds in live_record (prefix "avg" or "close") into rows that score() understands."""
    odds = live[[f"{prefix}_away", f"{prefix}_draw", f"{prefix}_home"]].astype(float)
    rows = live[["match_id", "result"]].copy()
    rows["model"] = name
    rows[PROB_COLS] = remove_margin(odds).values
    return rows


if __name__ == "__main__":
    live = read_sql("SELECT * FROM live_record")

    if live.empty:
        print("No scored predictions yet")
        raise SystemExit(0)

    # Count replaced predictions before keeping only the one that counts per match
    superseded = (live["prediction_rank"] > 1).sum()
    live = live[live["prediction_rank"] == 1].copy()
    live[PROB_COLS] = live[PROB_COLS].astype(float)

    # Score everyone on the same matches: those with both pre-match and closing odds
    with_odds = live.dropna(subset=["avg_home", "close_home"])

    preds = with_odds[["match_id", "model", "result"] + PROB_COLS]
    prematch = market_rows(with_odds, "avg", "market pre-match")
    closing = market_rows(with_odds, "close", "market closing")
    scores = score(pd.concat([preds, prematch, closing])).round(4)

    print(f"Scored {len(preds)} predictions")
    print(scores.to_string(index=False))

    unscored = read_sql("""
        SELECT COUNT(*) AS n FROM predictions
        WHERE match_date < CURRENT_DATE
          AND prediction_id NOT IN (SELECT prediction_id FROM live_record)
    """).n[0]
    print(f"Past predictions with no result yet: {unscored}")
    print(f"Earlier predictions replaced by a later one: {superseded}")