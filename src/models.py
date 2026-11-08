from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from src.features import load_features

# Chosen with src/feature_test.py: shots on target help, recent goals do not
LOGISTIC_FEATURES = ["elo_diff", "home_sot5", "home_sota5", "away_sot5", "away_sota5"]

# Chosen with src/tune_boosting.py (log loss 1.0528 → 1.0292): few, shallow trees learning slowly
BOOSTING_FEATURES = LOGISTIC_FEATURES
BOOSTING_PARAMS = dict(learning_rate=0.02, max_iter=100, max_depth=2,
                       min_samples_leaf=20, l2_regularization=0.0)


def make_logistic():
    return make_pipeline(
        SimpleImputer(strategy="median"),   # fills each team's empty first match
        StandardScaler(),                   # puts all features on the same scale
        LogisticRegression(max_iter=1000),
    )


def make_boosting(**params):
    return HistGradientBoostingClassifier(**{**BOOSTING_PARAMS, **params}, random_state=0)


def make_models():
    # Each model → (model, the features it uses)
    return {
        "baseline": (DummyClassifier(strategy="prior"), ["elo_diff"]),
        "logistic": (make_logistic(), LOGISTIC_FEATURES),
        "boosting": (make_boosting(), BOOSTING_FEATURES),
    }


if __name__ == "__main__":
    df = load_features()

    # Quick check on one season
    train = df[df["season"] < "1920"]   # 2015/16 to 2018/19
    test = df[df["season"] == "1920"]   # 2019/20

    for name, (model, cols) in make_models().items():
        model.fit(train[cols], train["result"])
        probs = model.predict_proba(test[cols])
        loss = log_loss(test["result"], probs, labels=model.classes_)
        print(name, round(loss, 4))
