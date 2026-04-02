from __future__ import annotations

import os

import joblib
from django.utils import timezone

from apps.ml_engine.data_extractors.user_profile import load_user_profiles
from apps.ml_engine.inference_adapters.salary_predictor import MODEL_PATH, SalaryPredictor
from .simple_models import fit_linear_regression, mean_absolute_percentage_error, random_train_test_split


CITY_TIER_SCORES = {
    "mumbai": 1.0,
    "bangalore": 0.95,
    "bengaluru": 0.95,
    "delhi": 0.92,
    "gurgaon": 0.9,
    "noida": 0.88,
    "pune": 0.86,
    "hyderabad": 0.83,
    "chennai": 0.82,
    "kolkata": 0.78,
}


def train_salary_model() -> dict:
    df = load_user_profiles()
    if df.empty:
        return _skip("No user profiles exist yet.", sample_count=0)

    df = df.fillna({"monthly_income": 0, "variable_income": 0, "rent_or_emi": 0, "city": ""}).copy()
    df = df[df["monthly_income"] > 0]
    sample_count = len(df)
    if sample_count < 8:
        return _skip("Need at least 8 income-bearing user profiles before salary training is useful.", sample_count=sample_count)

    now = timezone.now()
    created_at = df.get("created_at")
    if created_at is None:
        account_age_days = [0] * sample_count
    else:
        created_at = created_at.fillna(now)
        account_age_days = (now - created_at).dt.days.clip(lower=0)

    df["city_tier_score"] = df["city"].astype(str).str.lower().map(CITY_TIER_SCORES).fillna(0.75)
    df["income_variability_ratio"] = (
        df["variable_income"].astype(float) / df["monthly_income"].astype(float).replace(0, 1)
    ).clip(lower=0, upper=2)
    df["account_age_days"] = account_age_days

    feature_names = SalaryPredictor.FEATURE_NAMES
    X = df[feature_names].astype(float).values
    y = df["monthly_income"].astype(float).values

    X_train, X_test, y_train, y_test = random_train_test_split(X, y, test_size=0.25, random_state=42)
    model = fit_linear_regression(X_train, y_train)

    predictions = model.predict(X_test)
    mape = float(mean_absolute_percentage_error(y_test, predictions)) if len(y_test) else 1.0
    quality_score = max(0.0, min(100.0, 100.0 - (mape * 100.0)))
    coverage_score = min(100.0, (sample_count / 40.0) * 100.0)
    confidence_estimate = round(max(22.0, (quality_score * 0.65) + (coverage_score * 0.35)), 2)

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump({"model": model, "feature_names": feature_names}, MODEL_PATH)

    return {
        "status": "ready",
        "sample_count": sample_count,
        "quality_score": round(quality_score, 2),
        "confidence_estimate": confidence_estimate,
        "artifact_path": MODEL_PATH,
        "notes": f"Linear salary regressor trained on {sample_count} user profiles with holdout MAPE {mape:.2f}.",
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
