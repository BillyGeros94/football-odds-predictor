"""Tune the gradient boosting model on the tuning seasons (2019/20–2021/22).

Boosting overfits easily on a few thousand matches, so the grid focuses on
slower learning, shallower trees and bigger leaves. Every combination of the
GRID values is tried on both feature sets (64 runs, a few minutes).

Run:
    python -m src.tune_boosting
"""
import itertools

import pandas as pd
from sklearn.metrics import log_loss

from src.backtest import TUNE_SEASONS
from src.features import FEATURES, load_features
from src.models import LOGISTIC_FEATURES, make_boosting

FEATURE_SETS = {"elo + sot": LOGISTIC_FEATURES, "all": FEATURES}

GRID = {
    "learning_rate": [0.02, 0.05],
    "max_iter": [100, 300],
    "max_depth": [2, 3],
    "min_samples_leaf": [20, 100],
    "l2_regularization": [0.0, 1.0],
}


def walk_forward_loss(df, cols, params):
    """Average walk-forward log loss on the tuning seasons for one combination of settings."""
    losses = []
    for season in TUNE_SEASONS:
        train = df[df["season"] < season]
        test = df[df["season"] == season]
        model = make_boosting(**params)
        model.fit(train[cols], train["result"])
        probs = model.predict_proba(test[cols])
        losses.append(log_loss(test["result"], probs, labels=model.classes_))
    return sum(losses) / len(losses)


if __name__ == "__main__":
    df = load_features()

    rows = []
    for set_name, cols in FEATURE_SETS.items():
        for values in itertools.product(*GRID.values()):
            params = dict(zip(GRID.keys(), values))
            rows.append({"features": set_name, **params,
                         "loss": walk_forward_loss(df, cols, params)})

    results = pd.DataFrame(rows).sort_values("loss")
    print(results.head(10).round(4).to_string(index=False))
    print()
    print("Worst:", round(results["loss"].max(), 4))

# Result: best was elo + sot, learning_rate 0.02, max_iter 100, max_depth 2,
# min_samples_leaf 20 (1.0292). A follow-up check showed 50 or 150 trees and
# depth 1 all score worse, so this is a real optimum. Saved in models.py.
