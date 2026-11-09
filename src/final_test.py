"""The final test: run once, after every choice was made on the tuning seasons.

Seasons 2022/23 to 2026/27 (the matches played so far) were never used for any
decision. Each season is predicted by models trained only on earlier seasons.
Results are saved to results/metrics.json and results/calibration_final.png.

It refuses to run again once results/metrics.json exists: rerunning later would
include more matches and overwrite the official numbers quoted in the README.
To run it again on purpose:
    python -m src.final_test --force
"""
import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd

from src.backtest import FINAL_SEASONS, walk_forward
from src.calibration import calibration_error, reliability_chart
from src.evaluate import market_probs, score
from src.features import load_features

METRICS = Path("results/metrics.json")

if __name__ == "__main__":
    if METRICS.exists() and "--force" not in sys.argv:
        run_date = json.loads(METRICS.read_text()).get("run_date", "earlier")
        print(f"The final test already ran on {run_date}; its results are the official ones.\n"
              "Rerunning would overwrite them. Use --force if you really mean to.")
        raise SystemExit(1)

    preds = walk_forward(load_features(), FINAL_SEASONS)
    market = market_probs()
    preds = pd.concat([preds, market[market["match_id"].isin(preds["match_id"])]],
                      ignore_index=True)

    overall = score(preds)
    overall["calibration_error"] = overall["model"].map(
        lambda name: calibration_error(preds[preds["model"] == name]))
    print(overall.round(4).to_string(index=False))

    by_season = {season: score(group).set_index("model")["log_loss"]
                 for season, group in preds.groupby("season")}
    by_season = pd.DataFrame(by_season).loc[["average", "market", "baseline"]]
    by_season.loc["gap to market"] = by_season.loc["average"] - by_season.loc["market"]
    print("\nLog loss by season:")
    print(by_season.round(4).to_string())

    reliability_chart(preds, "Calibration on the final test, 2022/23–2026/27",
                      "results/calibration_final.png")

    metrics = {
        "run_date": date.today().isoformat(),
        "test_seasons": FINAL_SEASONS,
        "matches": int(preds[preds["model"] == "average"].shape[0]),
        "overall": overall.round(4).to_dict(orient="records"),
        "log_loss_by_season": by_season.round(4).to_dict(),
    }
    METRICS.write_text(json.dumps(metrics, indent=2))
    print("\nSaved results/metrics.json and results/calibration_final.png")
