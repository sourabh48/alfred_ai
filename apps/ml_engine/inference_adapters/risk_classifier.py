from .artifacts import load_inference_artifact
from .base_adapter import BaseModelAdapter

MODEL_PATH = "ml_models/alfred/risk_classifier/model.json"

class RiskClassifier(BaseModelAdapter):
    FEATURE_NAMES = ["stress_score", "sleep_hours", "work_hours"]

    def load(self):
        self.model = (load_inference_artifact("risk_classifier", schema=self.FEATURE_NAMES) or {}).get("model")

    def predict(self, features):
        probs = self.model.predict_proba([features])[0]
        return {
            "layoff_risk": float(probs[1]),
            "illness_risk": float(probs[2]) if len(probs) > 2 else 0,
        }

risk_classifier = RiskClassifier()
