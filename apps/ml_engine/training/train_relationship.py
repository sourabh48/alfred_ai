from __future__ import annotations

import os

import joblib

from apps.ml_engine.inference_adapters.relationship_model import MODEL_PATH, RelationshipModelPredictor
from apps.relationship.models import RelationshipProfile
from .simple_models import fit_linear_regression, mean_absolute_error, random_train_test_split


def train_relationship_model():
    rows = [_row(item) for item in RelationshipProfile.objects.select_related("user").filter(compatibility_score__gt=0)]
    sample_count = len(rows)
    if sample_count < 8:
        return _skip("Need at least 8 scored relationship profiles before relationship training is useful.", sample_count=sample_count)

    feature_names = RelationshipModelPredictor.FEATURE_NAMES
    X = [[row[name] for name in feature_names] for row in rows]
    y = [row["target_score"] for row in rows]

    X_train, X_test, y_train, y_test = random_train_test_split(X, y, test_size=0.25, random_state=42)
    model = fit_linear_regression(X_train, y_train)

    predictions = model.predict(X_test)
    mae = float(mean_absolute_error(y_test, predictions)) if len(y_test) else 100.0
    quality_score = round(max(0.0, min(100.0, 100.0 - mae)), 2)
    coverage_score = min(100.0, (sample_count / 30.0) * 100.0)
    confidence_estimate = round(max(18.0, (quality_score * 0.6) + (coverage_score * 0.4)), 2)

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump({"model": model, "feature_names": feature_names}, MODEL_PATH)

    return {
        "status": "ready",
        "sample_count": sample_count,
        "quality_score": quality_score,
        "confidence_estimate": confidence_estimate,
        "artifact_path": MODEL_PATH,
        "notes": f"Relationship regressor trained on {sample_count} scored profiles with holdout MAE {mae:.2f}.",
    }


def _row(item: RelationshipProfile) -> dict:
    monthly_income = float(getattr(item.user, "monthly_income", 0) or 0)
    return {
        "partner_financial_score": float(item.partner_financial_score or 0),
        "partner_savings_habits": float(item.partner_savings_habits or 0),
        "user_savings_rate": max(0.0, min(100.0, 100.0 - float(getattr(item.user, "rent_or_emi", 0) or 0) / monthly_income * 100.0)) if monthly_income else 0.0,
        "user_debt_pressure": min(100.0, (float(getattr(item.user, "rent_or_emi", 0) or 0) / monthly_income) * 100.0) if monthly_income else 0.0,
        "monthly_income_band": min(12.0, monthly_income / 25000.0),
        "target_score": float(item.compatibility_score or 0),
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
