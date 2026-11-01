from .artifacts import load_inference_artifact
from .base_adapter import BaseModelAdapter


MODEL_PATH = "ml_models/alfred/salary_model/model.json"


class SalaryPredictor(BaseModelAdapter):
    FEATURE_NAMES = [
        "variable_income",
        "rent_or_emi",
        "city_tier_score",
        "account_age_days",
    ]

    def load(self, *, model_path: str | None = None, force_reload: bool = False):
        payload = load_inference_artifact("salary_predictor", model_path, schema=self.FEATURE_NAMES)
        if payload is None:
            raise ValueError("Salary artifact has no valid evidence or uses obsolete features; retraining is required.")
        self.model = payload["model"]
        self.feature_names = payload["feature_names"]

    def preprocess(self, x):
        if isinstance(x, dict):
            return [float(x.get(name, 0) or 0) for name in self.feature_names]
        return [float(value or 0) for value in x]

    def predict(self, x, *, model_path: str | None = None, force_reload: bool = False):
        self.load(model_path=model_path, force_reload=force_reload)
        vector = self.preprocess(x)
        return float(self.model.predict([vector])[0])


salary_predictor = SalaryPredictor()
