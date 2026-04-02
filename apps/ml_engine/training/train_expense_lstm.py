from __future__ import annotations

import os

import joblib
import numpy as np

from apps.ml_engine.data_extractors.user_expenses import load_user_expense_history
from apps.ml_engine.inference_adapters.expense_lstm import MODEL_PATH, ExpenseLSTMAdapter
from .simple_models import fit_linear_regression, mean_absolute_error


def train_expense_lstm() -> dict:
    df = load_user_expense_history()
    if df.empty:
        return _skip("No expense history exists yet.", sample_count=0)

    df = df.sort_values(["timestamp", "user_id"]).copy()
    df["amount"] = df["amount"].astype(float)
    sequence = df["amount"].tolist()
    sample_count = len(sequence)
    window = ExpenseLSTMAdapter.WINDOW_SIZE

    if sample_count < (window + 18):
        return _skip(
            f"Need at least {window + 18} expense rows before the expense forecaster can be trained safely.",
            sample_count=sample_count,
        )

    X, y = [], []
    for index in range(len(sequence) - window):
        X.append(sequence[index : index + window])
        y.append(sequence[index + window])

    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    split_index = max(int(len(X) * 0.8), 1)
    if split_index >= len(X):
        split_index = len(X) - 1
    if split_index <= 0:
        return _skip("Not enough sliding-window samples for expense forecasting.", sample_count=sample_count)

    X_train, X_test = X[:split_index], X[split_index:]
    y_train, y_test = y[:split_index], y[split_index:]
    X_train_transformed = np.log1p(np.clip(X_train, a_min=0.0, a_max=None))
    X_test_transformed = np.log1p(np.clip(X_test, a_min=0.0, a_max=None))
    y_train_transformed = np.log1p(np.clip(y_train, a_min=0.0, a_max=None))
    model = fit_linear_regression(X_train_transformed, y_train_transformed)

    predictions = np.expm1(model.predict(X_test_transformed))
    if len(y_test):
        mae = float(mean_absolute_error(y_test, predictions))
        relative_error = float(np.mean(np.abs(y_test - predictions) / np.maximum(np.abs(y_test), 1.0)))
    else:
        fallback_predictions = np.expm1(model.predict(X_train_transformed))
        mae = float(mean_absolute_error(y_train, fallback_predictions))
        relative_error = float(np.mean(np.abs(y_train - fallback_predictions) / np.maximum(np.abs(y_train), 1.0)))
    quality_score = max(0.0, min(100.0, 100.0 - (min(relative_error, 2.0) * 100.0)))
    coverage_score = min(100.0, (sample_count / 120.0) * 100.0)
    confidence_estimate = round(max(25.0, (quality_score * 0.6) + (coverage_score * 0.4)), 2)

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump({"model": model, "window_size": window, "transform": "log1p"}, MODEL_PATH)

    return {
        "status": "ready",
        "sample_count": sample_count,
        "quality_score": round(quality_score, 2),
        "confidence_estimate": confidence_estimate,
        "artifact_path": MODEL_PATH,
        "notes": f"Windowed expense forecaster trained on {sample_count} expense rows with holdout MAE {mae:.2f} and relative error {relative_error:.2f}.",
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
