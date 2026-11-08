"""Check calibration: when a model says 60%, does it happen about 60% of the time?

Uses the walk-forward predictions on the tuning seasons, plus the market and a
simple average of logistic and boosting. Saves a reliability chart to results/.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")   # save charts to files without opening a window
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.backtest import TUNE_SEASONS, walk_forward
from src.evaluate import market_probs, score
from src.features import load_features

OUTCOMES = {"home": "H", "draw": "D", "away": "A"}
BINS = np.arange(0, 1.05, 0.1)


def reliability(preds, outcome):
    # Group predictions into 10% bins, then compare predicted and actual rates
    col, letter = f"prob_{outcome}", OUTCOMES[outcome]
    df = preds[[col]].copy()
    df["happened"] = (preds["result"] == letter).astype(float)
    df["bin"] = pd.cut(df[col], BINS, include_lowest=True)
    table = df.groupby("bin", observed=True).agg(
        predicted=(col, "mean"), actual=("happened", "mean"), matches=(col, "size"))
    return table[table["matches"] >= 20]   # ignore bins too small to judge


def reliability_chart(preds, title, path):
    # One panel per outcome: predicted probability against how often it happened
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.2), sharey=True)
    for ax, outcome in zip(axes, OUTCOMES):
        ax.plot([0, 1], [0, 1], color="grey", linestyle="--", linewidth=1, label="perfect")
        for name in ["average", "market"]:
            t = reliability(preds[preds["model"] == name], outcome)
            ax.plot(t["predicted"], t["actual"], marker="o", label=name)
        ax.set_title("Draw" if outcome == "draw" else f"{outcome.capitalize()} win")
        ax.set_xlabel("Predicted probability")
        ax.set_xlim(0, 0.9)
        ax.set_ylim(0, 0.9)
    axes[0].set_ylabel("Actual rate")
    axes[0].legend()
    fig.suptitle(title)
    fig.tight_layout()
    Path(path).parent.mkdir(exist_ok=True)
    fig.savefig(path, dpi=120)
    plt.close(fig)


def calibration_error(preds):
    # Average gap between predicted and actual rates, weighted by matches
    gaps = []
    for outcome in OUTCOMES:
        t = reliability(preds, outcome)
        gaps.append(((t["predicted"] - t["actual"]).abs() * t["matches"]).sum() / t["matches"].sum())
    return sum(gaps) / len(gaps)


if __name__ == "__main__":
    preds = walk_forward(load_features(), TUNE_SEASONS)
    market = market_probs()
    preds = pd.concat([preds, market[market["match_id"].isin(preds["match_id"])]],
                      ignore_index=True)

    table = score(preds)
    table["calibration_error"] = table["model"].map(
        lambda name: calibration_error(preds[preds["model"] == name]))
    print(table.round(4).to_string(index=False))

    print("\nLogistic, home win:")
    print(reliability(preds[preds["model"] == "logistic"], "home").round(3).to_string())

    reliability_chart(preds, "Calibration on 2019/20–2021/22 (walk-forward)",
                      "results/calibration_tuning.png")
    print("\nSaved results/calibration_tuning.png")

# Result: all models are within about 2 percentage points of the actual rates,
# close to the market (0.018). A separate calibration step is not needed.
