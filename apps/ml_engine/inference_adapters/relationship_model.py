from __future__ import annotations

import os

import joblib


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
        if self._artifact is None:
            if not os.path.exists(MODEL_PATH):
                return None
            self._artifact = joblib.load(MODEL_PATH)
        model = self._artifact.get("model")
        feature_names = self._artifact.get("feature_names") or self.FEATURE_NAMES
        row = [[float(features.get(name, 0) or 0) for name in feature_names]]
        try:
            prediction = model.predict(row)
        except Exception:
            return None
        if prediction is None or not len(prediction):
            return None
        return float(max(0.0, min(100.0, prediction[0])))


relationship_model_predictor = RelationshipModelPredictor()
