"""Load the artifact whose recorded training evidence permits inference."""

import joblib

from apps.ml_engine.models import AdaptiveModelState
from apps.ml_engine.training.quality import resolve_artifact_path


def load_inference_artifact(model_key, model_path=None):
    state = AdaptiveModelState.objects.filter(model_key=model_key).first()
    if state is None or not state.inference_ready:
        return None
    artifact_path = resolve_artifact_path(state.artifact_path)
    if model_path is not None and resolve_artifact_path(model_path).resolve() != artifact_path.resolve():
        return None
    try:
        payload = joblib.load(artifact_path)
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None
