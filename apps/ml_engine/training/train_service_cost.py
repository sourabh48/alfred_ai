from __future__ import annotations

import os
from collections import defaultdict

import joblib

from apps.ml_engine.inference_adapters.service_cost_predictor import (
    MODEL_PATH,
    ServiceCostPredictor,
    service_type_score,
    vehicle_type_score,
)
from apps.mobility.models import BikeServiceRecord
from .simple_models import fit_linear_regression, mean_absolute_percentage_error, random_train_test_split


def train_service_cost_model():
    records = list(
        BikeServiceRecord.objects.select_related("bike_profile")
        .filter(cost__gt=0)
        .order_by("bike_profile_id", "bike_name", "service_date", "id")
    )
    sample_count = len(records)
    if sample_count < 10:
        return _skip(
            "Need at least 10 paid service records before service-cost training is useful.",
            sample_count=sample_count,
        )

    rows = _feature_rows(records)
    if len(rows) < 10:
        return _skip(
            "Service-cost training could not build enough feature-complete records.",
            sample_count=len(rows),
        )

    feature_names = ServiceCostPredictor.FEATURE_NAMES
    X = [[row[name] for name in feature_names] for row in rows]
    y = [row["target_cost"] for row in rows]

    X_train, X_test, y_train, y_test = random_train_test_split(X, y, test_size=0.25, random_state=42)
    model = fit_linear_regression(X_train, y_train)

    predictions = model.predict(X_test)
    mape = float(mean_absolute_percentage_error(y_test, predictions)) if len(y_test) else 1.0
    quality_score = round(max(0.0, min(100.0, 100.0 - (mape * 100.0))), 2)
    coverage_score = min(100.0, (len(rows) / 50.0) * 100.0)
    confidence_estimate = round(max(18.0, (quality_score * 0.65) + (coverage_score * 0.35)), 2)

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump({"model": model, "feature_names": feature_names}, MODEL_PATH)

    return {
        "status": "ready",
        "sample_count": len(rows),
        "quality_score": quality_score,
        "confidence_estimate": confidence_estimate,
        "artifact_path": MODEL_PATH,
        "notes": f"Service-cost regressor trained on {len(rows)} service records with holdout MAPE {mape:.2f}.",
    }


def _feature_rows(records: list[BikeServiceRecord]) -> list[dict]:
    rows = []
    history_by_vehicle = defaultdict(list)

    for record in records:
        profile = getattr(record, "bike_profile", None)
        vehicle_key = profile.id if profile is not None else f"{record.vehicle_number or ''}:{record.bike_name or ''}"
        prior_costs = history_by_vehicle[vehicle_key]
        service_payload = ((record.parsed_payload or {}).get("service_payload") or {})
        parts_items = service_payload.get("parts_items") or []
        labour_items = service_payload.get("labour_items") or []
        line_item_count = int(
            service_payload.get("line_item_count")
            or len(parts_items) + len(labour_items)
            or 0
        )
        rows.append(
            {
                "vehicle_type_score": vehicle_type_score(getattr(profile, "vehicle_type", "")),
                "service_type_score": service_type_score(record.service_type),
                "odometer_band": round(float(record.odometer_km or 0) / 10000.0, 4),
                "engine_cc_band": round(float(getattr(profile, "engine_cc", 0) or 0) / 100.0, 4),
                "expected_mileage_band": round(float(getattr(profile, "expected_mileage_kmpl", 0) or 0) / 10.0, 4),
                "line_item_count": line_item_count,
                "parts_item_count": int(service_payload.get("parts_item_count") or len(parts_items)),
                "labour_item_count": int(service_payload.get("labour_item_count") or len(labour_items)),
                "recent_average_cost": round(sum(prior_costs[-3:]) / len(prior_costs[-3:]), 2) if prior_costs else 0.0,
                "target_cost": float(record.cost or 0),
            }
        )
        prior_costs.append(float(record.cost or 0))
    return rows


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
