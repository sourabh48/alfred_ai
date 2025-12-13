import joblib
import os
from sklearn.linear_model import LogisticRegression
from apps.ml_engine.data_extractors.user_behavior import load_behavior_data
from apps.ml_engine.inference_adapters.risk_classifier import MODEL_PATH

def train_risk_classifier():
    df = load_behavior_data()

    if df.empty:
        print("No behavior data.")
        return

    df["label"] = (df["work_hours"] > 10).astype(int)

    X = df[["stress_score", "sleep_hours", "work_hours"]].values
    y = df["label"].values

    model = LogisticRegression()
    model.fit(X, y)

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(model, MODEL_PATH)

    print("Risk classifier retrained.")
