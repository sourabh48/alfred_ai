from __future__ import annotations

import os

import joblib

from apps.ml_engine.data_extractors.user_behavior import load_behavior_data
from apps.ml_engine.inference_adapters.burnout_rf import MODEL_PATH
from .simple_models import fit_linear_regression, mean_absolute_error, random_train_test_split


def train_burnout_model() -> dict:
    df = load_behavior_data()
    if df.empty:
        return _skip("No behavioral history exists yet.", sample_count=0)

    df = df.dropna(subset=["stress_score", "sleep_hours", "work_hours"]).copy()
    sample_count = len(df)
    if sample_count < 12:
        return _skip("Need at least 12 behavioral snapshots before burnout training is useful.", sample_count=sample_count)

    X = df[["stress_score", "sleep_hours", "work_hours"]].astype(float).values
    y = (df["stress_score"].astype(float) * 0.4) + (df["work_hours"].astype(float) * 0.6)
    X_train, X_test, y_train, y_test = random_train_test_split(X, y.values, test_size=0.25, random_state=42)

    model = fit_linear_regression(X_train, y_train)

    predictions = model.predict(X_test)
    mae = float(mean_absolute_error(y_test, predictions))
    scale = max(float(abs(y_test).mean()), 1.0)
    normalized_error = min(mae / scale, 2.0)
    quality_score = max(0.0, min(100.0, 100.0 - (normalized_error * 100.0)))
    coverage_score = min(100.0, (sample_count / 60.0) * 100.0)
    confidence_estimate = round(max(20.0, (quality_score * 0.65) + (coverage_score * 0.35)), 2)

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(model, MODEL_PATH)

    return {
        "status": "ready",
        "sample_count": sample_count,
        "quality_score": round(quality_score, 2),
        "confidence_estimate": confidence_estimate,
        "artifact_path": MODEL_PATH,
        "notes": f"Burnout regressor trained on {sample_count} behavioral rows with holdout MAE {mae:.2f}.",
    }


def _skip(message: str, *, sample_count: int = 0, details: str = "") -> dict:
    note = message if not details else f"{message} {details}"
    return {
        "status": "skipped",
        "sample_count": sample_count,
        "quality_score": 0.0,
        "confidence_estimate": 0.0,
        "artifact_path": "",
        "notes": note.strip(),
    }
