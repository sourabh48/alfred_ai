import math
from datetime import datetime, timedelta, timezone
from statistics import median

import joblib

from apps.ml_engine.training.quality import resolve_artifact_path, validation_blockers
from .base_adapter import BaseModelAdapter


MODEL_PATH = "ml_models/alfred/expense_lstm/model.pkl"


class ExpenseLSTMAdapter(BaseModelAdapter):
    WINDOW_SIZE = 10

    def load(self):
        self.window_size = self.WINDOW_SIZE
        self.transform = ""
        self.model = None
        self.fallback_reason = "missing_or_unvalidated_artifact"
        try:
            payload = joblib.load(resolve_artifact_path(MODEL_PATH))
            trained_at = datetime.fromisoformat(payload.get("trained_at", ""))
            now = datetime.now(timezone.utc)
            freshness_hours = float(payload.get("freshness_hours", 12))
            if (trained_at.tzinfo is None or not 0 < freshness_hours <= 12
                    or trained_at > now or now >= trained_at + timedelta(hours=freshness_hours)):
                self.fallback_reason = "stale_artifact"
                return
            if payload.get("evaluation", {}).get("passed") is not True:
                return
            if validation_blockers("expense_forecaster", payload.get("sample_count"),
                                   payload.get("quality_score"), payload.get("confidence_estimate")):
                return
            window_size = int(payload.get("window_size", self.WINDOW_SIZE))
            if window_size != self.WINDOW_SIZE or not callable(getattr(payload["model"], "predict", None)):
                return
            self.model = payload["model"]
            self.window_size = window_size
            self.transform = payload.get("transform", "")
            self.fallback_reason = ""
        except Exception:
            # A truncated or obsolete local artifact must not break forecasting.
            return

    def preprocess(self, seq):
        values = [float(item or 0) for item in list(seq or [])]
        window = values[-self.window_size :]
        if len(window) < self.window_size:
            window = ([0.0] * (self.window_size - len(window))) + window
        if self.transform == "log1p":
            return [float(math.log1p(max(item, 0.0))) for item in window]
        return window

    def predict(self, seq):
        self.load()
        values = []
        for item in seq if seq is not None else []:
            try:
                value = float(item)
            except (TypeError, ValueError):
                continue
            if math.isfinite(value) and value > 0:
                values.append(value)
        fallback = float(median(values[-self.window_size:])) if values else 0.0
        if self.model is None or len(values) < self.window_size:
            return fallback
        x = self.preprocess(values)
        try:
            prediction = float(self.model.predict([x])[0])
        except Exception:
            return fallback
        if not math.isfinite(prediction):
            return fallback
        if self.transform == "log1p":
            return float(math.expm1(min(max(prediction, 0.0), 708.0)))
        return max(0.0, prediction)


expense_lstm = ExpenseLSTMAdapter()
