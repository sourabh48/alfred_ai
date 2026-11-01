from .artifacts import load_inference_artifact
from .base_adapter import BaseModelAdapter

MODEL_PATH = "ml_models/alfred/burnout_rf/model.json"

class BurnoutRF(BaseModelAdapter):
    FEATURE_NAMES = ["stress_score", "sleep_hours", "work_hours"]

    def load(self):
        self.model = (load_inference_artifact("burnout_rf", schema=self.FEATURE_NAMES) or {}).get("model")

    def predict(self, data):
        return float(self.model.predict([data])[0])

burnout_rf = BurnoutRF()
