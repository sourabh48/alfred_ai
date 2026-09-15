from __future__ import annotations

import joblib
import numpy as np
import pandas as pd
from django.utils import timezone

from apps.ml_engine.data_extractors.user_expenses import load_user_expense_history
from apps.ml_engine.inference_adapters.expense_lstm import MODEL_PATH, ExpenseLSTMAdapter
from .simple_models import fit_linear_regression, mean_absolute_error
from .quality import resolve_artifact_path, validation_blockers


def build_expense_windows(df, window: int):
    """Predict next spending transactions without crossing a user's history.

    This transaction sequence is not a daily cash-flow forecast. Import timestamps
    must not make old statements look like new spending.
    """
    df = df.copy()
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce", utc=True)
    df = df[np.isfinite(df["amount"]) & (df["amount"] > 0)].dropna(subset=["user_id", "transaction_date"])
    df = df.sort_values(["transaction_date", "id"], kind="stable")
    rows = []
    for _, history in df.groupby("user_id", sort=False):
        amounts = history["amount"].to_numpy(dtype=float)
        dates = history["transaction_date"].tolist()
        for index in range(window, len(history)):
            rows.append((dates[index], amounts[index - window:index], amounts[index]))
    rows.sort(key=lambda row: row[0])
    return rows, len(df)


def train_expense_lstm() -> dict:
    df = load_user_expense_history()
    if df.empty:
        return _skip("No debit spending history exists yet.")
    window = ExpenseLSTMAdapter.WINDOW_SIZE
    rows, sample_count = build_expense_windows(df, window)
    if len(rows) < 18:
        return _skip("Need at least 18 windows after each user's first 10 spending transactions.", sample_count=sample_count)

    # Keep the cutoff date in the holdout. No later event from another user may
    # appear in training before an earlier holdout prediction.
    cutoff = rows[min(int(len(rows) * 0.8), len(rows) - 1)][0]
    training = [row for row in rows if row[0] < cutoff]
    holdout = [row for row in rows if row[0] >= cutoff]
    if len(training) < 12 or len(holdout) < 4:
        return _skip("Need 12 training and 4 later holdout windows on distinct transaction dates.", sample_count=sample_count)

    X_train = np.asarray([row[1] for row in training])
    y_train = np.asarray([row[2] for row in training])
    X_test = np.asarray([row[1] for row in holdout])
    y_test = np.asarray([row[2] for row in holdout])
    model = fit_linear_regression(np.log1p(X_train), np.log1p(y_train), ridge=1.0)
    predictions = np.expm1(np.clip(model.predict(np.log1p(X_test)), 0.0, 708.0))
    baseline = np.median(X_test, axis=1)
    mae = mean_absolute_error(y_test, predictions)
    baseline_mae = mean_absolute_error(y_test, baseline)
    # WAPE avoids letting a few tiny transactions dominate the quality measure.
    relative_error = float(np.abs(y_test - predictions).sum() / max(np.abs(y_test).sum(), 1.0))
    quality_score = round(max(0.0, min(100.0, 100.0 * (1.0 - relative_error))), 2)
    evaluation = {
        "target": "next_debit_spending_transaction",
        "split": "chronological_transaction_date",
        "training_windows": len(training),
        "holdout_windows": len(holdout),
        "training_last_date": training[-1][0].date().isoformat(),
        "holdout_first_date": holdout[0][0].date().isoformat(),
        "holdout_last_date": holdout[-1][0].date().isoformat(),
        "mae": round(mae, 4),
        "wape": round(relative_error, 4),
        "baseline": "previous_10_transaction_median",
        "baseline_mae": round(baseline_mae, 4),
        "minimum_improvement": 0.05,
    }
    confidence = round(min(quality_score, min(100.0, len(holdout) * 5.0)), 2)
    blockers = validation_blockers("expense_forecaster", sample_count, quality_score, confidence)
    passes = np.isfinite(mae) and not blockers and baseline_mae > 0 and mae <= baseline_mae * 0.95
    evaluation["passed"] = bool(passes)
    evaluation["validation_blockers"] = blockers
    notes = (
        f"Next-transaction forecast: {len(training)} earlier training windows and {len(holdout)} later holdout windows; "
        f"MAE {mae:.2f}, WAPE {relative_error:.2f}, recent-median baseline MAE {baseline_mae:.2f}. "
    )
    result = {
        "status": "ready" if passes else "skipped",
        "sample_count": sample_count,
        "quality_score": quality_score,
        "confidence_estimate": confidence if passes else 0.0,
        "artifact_path": MODEL_PATH if passes else "",
        "notes": notes + ("Chronological quality and baseline gates passed." if passes else "Quality/baseline gate failed; use recent-history fallback."),
        "evaluation": evaluation,
    }
    if passes:
        artifact_path = resolve_artifact_path(MODEL_PATH)
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({
            "model": model, "window_size": window, "transform": "log1p",
            "trained_at": timezone.now().isoformat(), "freshness_hours": 12,
            "sample_count": sample_count, "quality_score": quality_score,
            "confidence_estimate": confidence, "evaluation": evaluation,
        }, artifact_path)
    else:
        resolve_artifact_path(MODEL_PATH).unlink(missing_ok=True)
    return result


def _skip(message: str, *, sample_count: int = 0) -> dict:
    resolve_artifact_path(MODEL_PATH).unlink(missing_ok=True)
    return {
        "status": "skipped", "sample_count": sample_count, "quality_score": 0.0,
        "confidence_estimate": 0.0, "artifact_path": "", "notes": message,
    }
