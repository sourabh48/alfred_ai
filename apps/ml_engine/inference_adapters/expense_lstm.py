import math

import joblib

from .base_adapter import BaseModelAdapter


MODEL_PATH = "ml_models/alfred/expense_lstm/model.pkl"


class ExpenseLSTMAdapter(BaseModelAdapter):
    WINDOW_SIZE = 10

    def load(self):
        payload = joblib.load(MODEL_PATH)
        self.model = payload["model"]
        self.window_size = int(payload.get("window_size", self.WINDOW_SIZE))
        self.transform = payload.get("transform", "")

    def preprocess(self, seq):
        values = [float(item or 0) for item in list(seq or [])]
        window = values[-self.window_size :]
        if len(window) < self.window_size:
            window = ([0.0] * (self.window_size - len(window))) + window
        if self.transform == "log1p":
            return [float(math.log1p(max(item, 0.0))) for item in window]
        return window

    def predict(self, seq):
        x = self.preprocess(seq)
        prediction = float(self.model.predict([x])[0])
        if self.transform == "log1p":
            return float(math.expm1(prediction))
        return prediction


expense_lstm = ExpenseLSTMAdapter()
