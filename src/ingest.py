from pathlib import Path
import pandas as pd

COLUMNS = ["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR",
           "HS", "AS", "HST", "AST",
           "AvgH", "AvgD", "AvgA", "AvgCH", "AvgCD", "AvgCA"]

def read_season(path):
    """
    Reads a season CSV file and returns a DataFrame with the relevant columns.

    """
    # Read the file. latin-1 avoids errors from odd characters
    df = pd.read_csv(path, encoding="latin-1")

    # Keep columns. Any that are missing become empty instead of crashing
    df = df.reindex(columns=COLUMNS)

    # Remove blank rows
    df = df.dropna(subset=["HomeTeam"])

    # Convert dates, which come in more than one format
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, format="mixed")

    # Get league and season from the file name
    league, season = path.stem.split("_")

    # Add league and season columns
    df["League"] = league
    df["Season"] = season

    return df

if __name__ == "__main__":
    total = 0

    for path in Path("data/raw").glob("*.csv"):
        df = read_season(path)
        total += len(df)     

    print(total)