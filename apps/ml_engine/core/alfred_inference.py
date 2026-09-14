from .alfred_preprocessor import preprocessor
from .alfred_safetylayer import alfred_safety


class AlfredInferenceEngine:
    def predict_emotional_spend(self, expense_data):
        """Predict whether an expense looks impulse-led from local signals."""
        clean = preprocessor.preprocess_expense(expense_data)

        ok, msg = alfred_safety.validate_expense(clean)
        if not ok:
            return {"error": msg}

        trust_score = alfred_safety.compute_trust_score(clean)
        impulse_score, reasons = self._impulse_score(clean)
        confidence = max(0.05, min((trust_score * 0.35) + (impulse_score * 0.65), 0.99))
        is_emotional = impulse_score >= 0.55 and trust_score >= 0.45

        return {
            "is_emotional": is_emotional,
            "confidence": round(confidence, 3),
            "reason": "; ".join(reasons[:3]) if reasons else "expense does not match known impulse-spend signals",
        }

    def _impulse_score(self, expense):
        category = expense.get("category", "")
        description = expense.get("description", "")
        amount = float(expense.get("amount") or 0)
        score = 0.12
        reasons = []

        discretionary_categories = {"shopping", "food", "entertainment", "subscription", "travel"}
        essential_categories = {"rent", "utilities", "bills", "fuel", "health", "loan", "investment", "groceries"}
        impulse_terms = {
            "sale", "flash", "deal", "discount", "premium", "sneaker", "late night",
            "comfort", "craving", "impulse", "offer", "limited", "cart",
        }
        planned_terms = {"emi", "rent", "bill", "premium due", "sip", "mutual fund", "insurance", "medicine"}

        if category in discretionary_categories:
            score += 0.28
            reasons.append(f"{category} is discretionary")
        if category in essential_categories:
            score -= 0.18
            reasons.append(f"{category} is usually planned or essential")

        matched_impulse = [term for term in impulse_terms if term in description]
        if matched_impulse:
            score += min(0.3, 0.1 + (0.05 * len(matched_impulse)))
            reasons.append("description contains impulse-spend language")

        if any(term in description for term in planned_terms):
            score -= 0.25
            reasons.append("description contains planned-payment language")

        if amount >= 5000 and category in discretionary_categories:
            score += 0.12
            reasons.append("large discretionary amount")
        elif amount <= 250:
            score -= 0.05

        return max(0.0, min(score, 1.0)), reasons


alfred_engine = AlfredInferenceEngine()
