from __future__ import annotations

import os

import joblib

from apps.ml_engine.data_extractors.user_behavior import load_behavior_data
from apps.ml_engine.inference_adapters.risk_classifier import MODEL_PATH
from .simple_models import accuracy_score, fit_binary_logistic_regression, random_train_test_split


def train_risk_classifier() -> dict:
    df = load_behavior_data()
    if df.empty:
        return _skip("No behavioral history exists yet.", sample_count=0)

    df = df.dropna(subset=["stress_score", "sleep_hours", "work_hours"]).copy()
    df["label"] = (df["work_hours"].astype(float) > 10).astype(int)
    sample_count = len(df)
    if sample_count < 12:
        return _skip("Need at least 12 behavioral snapshots before risk classification is useful.", sample_count=sample_count)
    if df["label"].nunique() < 2:
        return _skip("Risk classifier needs at least two outcome classes in behavioral history.", sample_count=sample_count)

    X = df[["stress_score", "sleep_hours", "work_hours"]].astype(float).values
    y = df["label"].astype(int).values
    X_train, X_test, y_train, y_test = random_train_test_split(
        X,
        y,
        test_size=0.25,
        random_state=42,
        stratify=y,
    )

    model = fit_binary_logistic_regression(X_train, y_train, iterations=1400, learning_rate=0.08)

    predictions = model.predict(X_test)
    accuracy = float(accuracy_score(y_test, predictions))
    quality_score = round(max(0.0, min(100.0, accuracy * 100.0)), 2)
    coverage_score = min(100.0, (sample_count / 60.0) * 100.0)
    confidence_estimate = round(max(20.0, (quality_score * 0.7) + (coverage_score * 0.3)), 2)

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(model, MODEL_PATH)

    return {
        "status": "ready",
        "sample_count": sample_count,
        "quality_score": quality_score,
        "confidence_estimate": confidence_estimate,
        "artifact_path": MODEL_PATH,
        "notes": f"Risk classifier trained on {sample_count} behavioral rows with holdout accuracy {accuracy:.2f}.",
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
