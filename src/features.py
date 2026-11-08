"""Load the model inputs from the match_features view (built in sql/features.sql).

Every feature is known before kick-off: the Elo ratings before the match and
each team's averages over its previous 5 matches.

Run to check the features:
    python -m src.features
"""
from src.db import read_sql

# Every candidate model input. models.py picks which ones each model uses.
# gf5/ga5 = goals for/against, sot5/sota5 = shots on target for/against,
# all averaged over the team's previous 5 matches
FEATURES = ["elo_diff",
            "home_gf5", "home_ga5", "home_sot5", "home_sota5",
            "away_gf5", "away_ga5", "away_sot5", "away_sota5"]


def load_features():
    """Return one row per finished match, in date order, with every feature as a float."""
    df = read_sql("SELECT * FROM match_features ORDER BY match_date, match_id")

    # Postgres returns numbers as Decimal; scikit-learn needs floats (None becomes NaN)
    columns = ["home_elo", "away_elo"] + FEATURES[1:]
    df[columns] = df[columns].astype(float)

    df["elo_diff"] = df["home_elo"] - df["away_elo"]
    return df


if __name__ == "__main__":
    df = load_features()
    print(df.shape)
    print(df[FEATURES].isna().sum())   # empty values come from each team's first match
    print(df[FEATURES].describe().round(2))
