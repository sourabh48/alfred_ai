from __future__ import annotations

import os

import math

from .artifacts import load_inference_artifact


MODEL_PATH = os.path.join("ml_models", "alfred", "parser_confidence", "model.pkl")


class ParserConfidenceCalibrator:
    FEATURE_NAMES = [
        "successful_count",
        "review_count",
        "failed_count",
        "correction_count",
        "retry_success_count",
        "retry_failure_count",
        "average_confidence",
        "observed_fields_count",
        "observed_keywords_count",
        "accepted_field_hints_count",
        "scope_hash",
        "extension_hash",
    ]

    def __init__(self):
        self._artifact = None

    def predict_probability(self, features: dict) -> float | None:
        self._artifact = load_inference_artifact("parser_confidence_calibrator")
        if self._artifact is None:
            return None
        model = self._artifact.get("model")
        feature_names = self._artifact.get("feature_names") or self.FEATURE_NAMES
        row = [[float(features.get(name, 0) or 0) for name in feature_names]]
        try:
            probabilities = model.predict_proba(row)
        except Exception:
            return None
        value = float(probabilities[0][1]) if probabilities is not None and len(probabilities[0]) > 1 else None
        return value if value is not None and math.isfinite(value) else None


parser_confidence_calibrator = ParserConfidenceCalibrator()
