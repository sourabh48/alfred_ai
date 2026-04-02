TASK_ALIASES = {
    "emotion-expense": "emotional-spend",
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
        from apps.ml_engine.inference_adapters.relationship_siamese import relationship_siamese
        return relationship_siamese
    if task == "invest-rl":
        from apps.ml_engine.inference_adapters.rl_agent import rl_agent
        return rl_agent
    return None


class AlfredRouter:
    def route(self, task, payload):
        canonical_task = TASK_ALIASES.get(task, task)
        adapter = _load_adapter(canonical_task)
        if adapter is None:
            return {"error": "Invalid task"}

        adapter.load()
        if canonical_task == "relationship":
            return adapter.predict(payload["user"], payload["partner"])
        return adapter.predict(payload)


alfred_router = AlfredRouter()
