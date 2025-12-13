import joblib
import os
from sklearn.ensemble import RandomForestRegressor
from apps.ml_engine.data_extractors.user_behavior import load_behavior_data
from apps.ml_engine.inference_adapters.burnout_rf import MODEL_PATH

def train_burnout_model():
    df = load_behavior_data()

    if df.empty:
        print("No behavior data.")
        return

    features = ["stress_score", "sleep_hours", "work_hours"]
    df = df.dropna()

    X = df[features].values
    y = df["stress_score"].values * 0.4 + df["work_hours"] * 0.6

    model = RandomForestRegressor()
    model.fit(X, y)

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(model, MODEL_PATH)

    print("Burnout model retrained.")
