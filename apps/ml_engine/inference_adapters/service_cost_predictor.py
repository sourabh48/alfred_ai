from __future__ import annotations

import joblib
from pathlib import Path


MODEL_PATH = "ml_models/alfred/service_cost_predictor/model.pkl"

VEHICLE_TYPE_SCORES = {
    "motorcycle": 1.0,
    "scooter": 1.2,
    "car": 2.2,
}

SERVICE_TYPE_SCORES = {
    "routine": 1.0,
    "periodic_service": 1.1,
    "repair": 1.8,
    "accidental": 2.5,
    "breakdown": 2.2,
    "inspection": 0.8,
    "work_note": 0.9,
}


def vehicle_type_score(value: str) -> float:
    return VEHICLE_TYPE_SCORES.get(str(value or "").strip().lower(), 1.0)


def service_type_score(value: str) -> float:
    return SERVICE_TYPE_SCORES.get(str(value or "").strip().lower(), 1.0)


class ServiceCostPredictor:
    FEATURE_NAMES = [
        "vehicle_type_score",
        "service_type_score",
        "odometer_band",
        "engine_cc_band",
        "expected_mileage_band",
        "line_item_count",
        "parts_item_count",
        "labour_item_count",
        "recent_average_cost",
    ]

    def __init__(self):
        self._artifact = None

    def load(self, *, model_path: str | None = None, force_reload: bool = False):
        resolved_path = str(Path(model_path or MODEL_PATH))
        if self._artifact is not None and not force_reload and getattr(self, "_loaded_from", None) == resolved_path:
            return
        self._artifact = joblib.load(resolved_path)
        self._loaded_from = resolved_path

    def predict_cost(self, features: dict, *, model_path: str | None = None, force_reload: bool = False) -> float | None:
        resolved_path = Path(model_path or MODEL_PATH)
        if not resolved_path.exists():
            return None
        self.load(model_path=str(resolved_path), force_reload=force_reload)
        model = (self._artifact or {}).get("model")
        feature_names = (self._artifact or {}).get("feature_names") or self.FEATURE_NAMES
        row = [[float(features.get(name, 0) or 0) for name in feature_names]]
        try:
            prediction = model.predict(row)
        except Exception:
            return None
        if prediction is None or not len(prediction):
            return None
        return float(max(0.0, prediction[0]))


service_cost_predictor = ServiceCostPredictor()
