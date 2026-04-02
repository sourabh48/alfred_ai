import joblib
from pathlib import Path

from .base_adapter import BaseModelAdapter


MODEL_PATH = "ml_models/alfred/salary_model/model.pkl"


class SalaryPredictor(BaseModelAdapter):
    FEATURE_NAMES = [
        "variable_income",
        "rent_or_emi",
        "city_tier_score",
        "income_variability_ratio",
        "account_age_days",
    ]

    def load(self, *, model_path: str | None = None, force_reload: bool = False):
        resolved_path = str(Path(model_path or MODEL_PATH))
        if self.model is not None and not force_reload and getattr(self, "_loaded_from", None) == resolved_path:
            return
        payload = joblib.load(resolved_path)
        self.model = payload["model"]
        self.feature_names = payload.get("feature_names", self.FEATURE_NAMES)
        self._loaded_from = resolved_path

    def preprocess(self, x):
        if isinstance(x, dict):
            return [float(x.get(name, 0) or 0) for name in self.feature_names]
        return [float(value or 0) for value in x]

    def predict(self, x, *, model_path: str | None = None, force_reload: bool = False):
        self.load(model_path=model_path, force_reload=force_reload)
        vector = self.preprocess(x)
        return float(self.model.predict([vector])[0])


salary_predictor = SalaryPredictor()
