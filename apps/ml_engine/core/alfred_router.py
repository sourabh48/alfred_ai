from apps.ml_engine.inference_adapters.salary_predictor import salary_predictor
from apps.ml_engine.inference_adapters.expense_lstm import expense_lstm
from apps.ml_engine.inference_adapters.emotional_bert import emotional_bert
from apps.ml_engine.inference_adapters.burnout_rf import burnout_rf
from apps.ml_engine.inference_adapters.risk_classifier import risk_classifier
from apps.ml_engine.inference_adapters.relationship_siamese import relationship_siamese
from apps.ml_engine.inference_adapters.rl_agent import rl_agent

class AlfredRouter:

    def route(self, task, payload):

        if task == "salary":
            salary_predictor.load()
            return salary_predictor.predict(payload)

        if task == "expense-forecast":
            expense_lstm.load()
            return expense_lstm.predict(payload)

        if task == "emotional-spend":
            emotional_bert.load()
            return emotional_bert.predict(payload)

        if task == "burnout":
            burnout_rf.load()
            return burnout_rf.predict(payload)

        if task == "risk":
            risk_classifier.load()
            return risk_classifier.predict(payload)

        if task == "relationship":
            relationship_siamese.load()
            return relationship_siamese.predict(payload["user"], payload["partner"])

        if task == "invest-rl":
            rl_agent.load()
            return rl_agent.predict(payload)

        return {"error": "Invalid task"}

alfred_router = AlfredRouter()
