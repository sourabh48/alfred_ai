import joblib
from pathlib import Path

from .base_adapter import BaseModelAdapter


MODEL_PATH = "ml_models/alfred/salary_model/model.pkl"


class SalaryPredictor(BaseModelAdapter):
    FEATURE_NAMES = [
        "variable_income",
        "rent_or_emi",
        "city_tier_score",
        "account_age_days",
    ]

    def load(self, *, model_path: str | None = None, force_reload: bool = False):
        resolved_path = str(Path(model_path or MODEL_PATH))
        artifact_stat = Path(resolved_path).stat()
        artifact_version = (artifact_stat.st_mtime_ns, artifact_stat.st_size)
        if (self.model is not None and not force_reload
                and getattr(self, "_loaded_from", None) == resolved_path
                and getattr(self, "_loaded_version", None) == artifact_version):
            return
        payload = joblib.load(resolved_path)
        feature_names = payload.get("feature_names", self.FEATURE_NAMES)
        if set(feature_names) != set(self.FEATURE_NAMES) or len(feature_names) != len(self.FEATURE_NAMES):
            raise ValueError("Salary artifact uses obsolete or unsupported features; retraining is required.")
        self.model = payload["model"]
        self.feature_names = feature_names
        self._loaded_from = resolved_path
        self._loaded_version = artifact_version

    def preprocess(self, x):
        if isinstance(x, dict):
            return [float(x.get(name, 0) or 0) for name in self.feature_names]
        return [float(value or 0) for value in x]

    def predict(self, x, *, model_path: str | None = None, force_reload: bool = False):
        self.load(model_path=model_path, force_reload=force_reload)
        vector = self.preprocess(x)
        return float(self.model.predict([vector])[0])


salary_predictor = SalaryPredictor()
