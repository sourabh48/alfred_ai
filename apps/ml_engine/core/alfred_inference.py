from .alfred_safetylayer import alfred_safety
from .alfred_preprocessor import preprocessor
from .alfred_registry import model_registry

class AlfredInferenceEngine:

    def predict_emotional_spend(self, expense_data):
        """Predict whether an expense is emotional or normal."""

        # Step 1 – Preprocess
        clean = preprocessor.preprocess_expense(expense_data)

        # Step 2 – Validate
        ok, msg = alfred_safety.validate_expense(clean)
        if not ok:
            return {"error": msg}

        # Step 3 – Placeholder ML logic
        # (In Phase 4 this becomes a real ML model call)
        trust_score = alfred_safety.compute_trust_score(clean)

        is_emotional = clean["category"] in ["shopping", "food"] and trust_score < 0.8

        return {
            "is_emotional": is_emotional,
            "confidence": trust_score,
        }

alfred_engine = AlfredInferenceEngine()
