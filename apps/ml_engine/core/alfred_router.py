from math import isfinite

from apps.ml_engine.models import AdaptiveModelState
from apps.ml_engine.training.quality import resolve_artifact_path


TASK_ALIASES = {
    "emotion-expense": "emotional-spend",
}

# Recorded training evidence, not a file on disk, decides whether a learned role may serve.
ROLE_MODEL_KEYS = {
    "salary": "salary_predictor",
    "expense-forecast": "expense_forecaster",
    "burnout": "burnout_rf",
    "risk": "risk_classifier",
    "relationship": "relationship_model",
    "service-cost": "service_cost_predictor",
    "parser-confidence": "parser_confidence_calibrator",
}
PLANNED_ROLES = {"invest-rl": "rl_agent"}
# Its label is a work-hours threshold, so it stays off even if its scores ever pass: it cannot support "layoff risk".
UNVALIDATED_LABEL_ROLES = {"risk"}
PREDICT_METHODS = {
    "relationship": "predict_score",
    "service-cost": "predict_cost",
    "parser-confidence": "predict_probability",
}


def _load_adapter(task):
    if task == "salary":
        from apps.ml_engine.inference_adapters.salary_predictor import salary_predictor
        return salary_predictor
    if task == "expense-forecast":
        from apps.ml_engine.inference_adapters.expense_lstm import expense_lstm
        return expense_lstm
    if task == "emotional-spend":
        from apps.ml_engine.inference_adapters.emotional_bert import emotional_bert
        return emotional_bert
    if task == "burnout":
        from apps.ml_engine.inference_adapters.burnout_rf import burnout_rf
        return burnout_rf
    if task == "risk":
        from apps.ml_engine.inference_adapters.risk_classifier import risk_classifier
        return risk_classifier
    if task == "relationship":
        from apps.ml_engine.inference_adapters.relationship_model import relationship_model_predictor
        return relationship_model_predictor
    if task == "service-cost":
        from apps.ml_engine.inference_adapters.service_cost_predictor import service_cost_predictor
        return service_cost_predictor
    if task == "parser-confidence":
        from apps.ml_engine.inference_adapters.parser_confidence_calibrator import parser_confidence_calibrator
        return parser_confidence_calibrator
    return None


def _unavailable(task, reason):
    return {"status": "unavailable", "task": task, "reason": reason}


class AlfredRouter:
    def route(self, task, payload):
        if task == "gemini-development-smoke":
            from apps.ml_engine.services.gemini_development import smoke_test
            return smoke_test(payload)
        canonical_task = TASK_ALIASES.get(task, task)
        if canonical_task in PLANNED_ROLES:
            return _unavailable(canonical_task, "planned_not_implemented")
        adapter = _load_adapter(canonical_task)
        if adapter is None:
            return {"error": "Invalid task"}

        model_key = ROLE_MODEL_KEYS.get(canonical_task)
        if model_key is None:
            adapter.load()
            return adapter.predict(payload)

        # This adapter verifies its own evidence and owns the median fallback.
        if canonical_task == "expense-forecast":
            return adapter.predict(payload)
        state = AdaptiveModelState.objects.filter(model_key=model_key).first()
        if state is None or not state.inference_ready or canonical_task in UNVALIDATED_LABEL_ROLES:
            return _unavailable(canonical_task, "not_inference_ready")
        try:
            if canonical_task == "salary":
                result = adapter.predict(payload, model_path=str(resolve_artifact_path(state.artifact_path)))
            elif canonical_task in PREDICT_METHODS:
                result = getattr(adapter, PREDICT_METHODS[canonical_task])(payload)
            else:
                adapter.load()
                result = adapter.predict(payload)
        except Exception:
            # A corrupt artifact or unusable input must not surface as a server error.
            return _unavailable(canonical_task, "inference_failed")
        if result is None or (isinstance(result, float) and not isfinite(result)):
            return _unavailable(canonical_task, "model_declined")
        return result


alfred_router = AlfredRouter()
