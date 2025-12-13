import joblib
from .base_adapter import BaseModelAdapter

MODEL_PATH = "ml_models/alfred/risk_classifier/model.pkl"

class RiskClassifier(BaseModelAdapter):

    def load(self):
        self.model = joblib.load(MODEL_PATH)

    def predict(self, features):
        probs = self.model.predict_proba([features])[0]
        return {
            "layoff_risk": float(probs[1]),
            "illness_risk": float(probs[2]) if len(probs) > 2 else 0,
        }

risk_classifier = RiskClassifier()
