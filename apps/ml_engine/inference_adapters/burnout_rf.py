import joblib
import os
from .base_adapter import BaseModelAdapter

MODEL_PATH = "ml_models/alfred/burnout_rf/model.pkl"

class BurnoutRF(BaseModelAdapter):

    def load(self):
        self.model = joblib.load(MODEL_PATH)

    def predict(self, data):
        return float(self.model.predict([data])[0])

burnout_rf = BurnoutRF()
