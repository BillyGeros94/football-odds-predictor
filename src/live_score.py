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


ODDS_COLS = ["avg_away", "avg_draw", "avg_home", "close_away", "close_draw", "close_home"]


def live_scores():
    """Return the live record, or None if no predicted match has been played yet.

    The dict holds the scored matches, the scores of the model and both markets on
    those matches, and how many predictions were not scored or were replaced.
    """
    live = read_sql("SELECT * FROM live_record")
    if live.empty:
        return None

    # Count replaced predictions before keeping only the one that counts per match
    superseded = (live["prediction_rank"] > 1).sum()
    live = live[live["prediction_rank"] == 1].copy()
    live[PROB_COLS + ODDS_COLS] = live[PROB_COLS + ODDS_COLS].astype(float)

    # Score everyone on the same matches: those with both pre-match and closing odds
    with_odds = live.dropna(subset=["avg_home", "close_home"])

    preds = with_odds[["match_id", "model", "result"] + PROB_COLS]
    prematch = market_rows(with_odds, "avg", "market pre-match")
    closing = market_rows(with_odds, "close", "market closing")
    scores = score(pd.concat([preds, prematch, closing])).round(4)

    unscored = read_sql("""
        SELECT COUNT(*) AS n FROM predictions
        WHERE match_date < CURRENT_DATE
          AND prediction_id NOT IN (SELECT prediction_id FROM live_record)
    """).n[0]

    return {"matches": with_odds, "scores": scores,
            "unscored": int(unscored), "superseded": int(superseded)}


if __name__ == "__main__":
    record = live_scores()
    if record is None:
        print("No scored predictions yet")
        raise SystemExit(0)

    print(f"Scored {len(record['matches'])} predictions")
    print(record["scores"].to_string(index=False))
    print(f"Past predictions with no result yet: {record['unscored']}")
    print(f"Earlier predictions replaced by a later one: {record['superseded']}")
