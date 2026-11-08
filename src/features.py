from src.db import read_sql

FEATURES = ["elo_diff",
            "home_gf5", "home_ga5", "home_sot5", "home_sota5",
            "away_gf5", "away_ga5", "away_sot5", "away_sota5"]

def load_features():
    df  = read_sql("SELECT * FROM match_features ORDER BY match_date, match_id")
    columns = ["home_elo", "away_elo"] + FEATURES[1:]
    df[columns] = df[columns].astype(float)
    df["elo_diff"] = df["home_elo"] - df["away_elo"]
    return df

if __name__ == "__main__":
    df = load_features()
    print(df.shape)
    print(df[FEATURES].isna().sum())
    print(df[FEATURES].describe().round(2))
