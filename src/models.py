from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import log_loss

from src.features import FEATURES, load_features

def make_models():
    # Each model → (model, the features it uses)
    return {
        "baseline": (DummyClassifier(strategy="prior"), ["elo_diff"]),
        "logistic": (LogisticRegression(), ["elo_diff"]),
        "boosting": (HistGradientBoostingClassifier(
                        max_iter=200, learning_rate=0.05, max_depth=3), FEATURES),
    }

if __name__ == "__main__":
    df = load_features()

    # 1. Split by season
    train = df[df["season"] < "1920"]   # (2015/16 to 2019/20)
    test  = df[df["season"] == "1920"]  # (2019/20)

    for name, (model, cols) in make_models().items():
        model.fit(train[cols], train["result"])
        probs = model.predict_proba(test[cols])
        loss = log_loss(test["result"], probs, labels=model.classes_)
        print (name, round(loss,4))