from __future__ import annotations

import os

import math

from .artifacts import load_inference_artifact


MODEL_PATH = os.path.join("ml_models", "alfred", "relationship_model", "model.pkl")


class RelationshipModelPredictor:
    FEATURE_NAMES = [
        "partner_financial_score",
        "partner_savings_habits",
        "user_savings_rate",
        "user_debt_pressure",
        "monthly_income_band",
    ]

    def __init__(self):
        self._artifact = None

    def predict_score(self, features: dict) -> float | None:
        self._artifact = load_inference_artifact("relationship_model")
        if self._artifact is None:
            return None
        model = self._artifact.get("model")
        feature_names = self._artifact.get("feature_names") or self.FEATURE_NAMES
        row = [[float(features.get(name, 0) or 0) for name in feature_names]]
        try:
            prediction = model.predict(row)
        except Exception:
            return None
        if prediction is None or not len(prediction):
            return None
        value = float(prediction[0])
        return max(0.0, min(100.0, value)) if math.isfinite(value) else None


relationship_model_predictor = RelationshipModelPredictor()
