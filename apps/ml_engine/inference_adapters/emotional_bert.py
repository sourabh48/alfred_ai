import os

from .base_adapter import BaseModelAdapter
from apps.ml_engine.core.alfred_inference import alfred_engine

MODEL_PATH = "ml_models/alfred/emotional_bert/"

class EmotionalBERT(BaseModelAdapter):
    def __init__(self):
        super().__init__()
        self.tokenizer = None
        self._torch = None
        self._load_attempted = False
        self._model_available = False

    def load(self):
        if self._load_attempted:
            return

        self._load_attempted = True
        if not os.path.isdir(MODEL_PATH):
            return

        try:
            from transformers import BertTokenizer, BertForSequenceClassification
            import torch

            self.tokenizer = BertTokenizer.from_pretrained(MODEL_PATH)
            self.model = BertForSequenceClassification.from_pretrained(MODEL_PATH)
            self.model.eval()
            self._torch = torch
            self._model_available = True
        except Exception:
            self.tokenizer = None
            self.model = None
            self._torch = None
            self._model_available = False

    def predict(self, payload):
        normalized = self._normalize_payload(payload)
        base = self._predict_with_context(normalized)
        text_probability = self._predict_text_probability(normalized["description"])

        reasons: list[str] = []
        if base.get("reason"):
            reasons.append(str(base["reason"]))
        if text_probability is not None and text_probability >= 0.65:
            reasons.append("language pattern resembles impulse-led spending")

        base_confidence = float(base.get("confidence", 0) or 0)
        confidence = base_confidence
        if text_probability is not None:
            confidence = ((base_confidence * 0.7) + (text_probability * 0.3))
        confidence = round(max(0.05, min(confidence, 0.99)), 3)

        is_emotional = bool(base.get("is_emotional"))
        if text_probability is not None and text_probability >= 0.72:
            is_emotional = True

        analysis_source = "behavioral-history" if normalized.get("user") is not None else "expense-inference"
        if text_probability is not None:
            analysis_source += "+text-model"
        else:
            analysis_source += "+fallback"

        return {
            "is_emotional": is_emotional,
            "confidence": confidence,
            "reason": "; ".join(reasons[:3]) if reasons else "spend pattern stays within the normal baseline",
            "analysis_source": analysis_source,
        }

    def _normalize_payload(self, payload):
        if isinstance(payload, dict):
            data = payload
        else:
            data = {"description": str(payload or "")}

        return {
            "user": data.get("user"),
            "amount": self._as_float(data.get("amount")),
            "category": str(data.get("category") or "other"),
            "description": str(
                data.get("description")
                or data.get("raw_description")
                or data.get("merchant")
                or ""
            ),
            "merchant": str(data.get("merchant") or ""),
            "direction": str(data.get("direction") or "debit"),
            "transaction_date": data.get("transaction_date"),
        }

    def _predict_with_context(self, payload: dict) -> dict:
        user = payload.get("user")
        if user is not None:
            from apps.expenses.services.transaction_intelligence import _detect_emotional_spend

            return _detect_emotional_spend(
                user=user,
                amount=payload["amount"],
                category=payload["category"],
                direction=payload["direction"],
                merchant=payload["merchant"],
                description=payload["description"],
                transaction_date=payload.get("transaction_date"),
                instance=None,
            )

        base = alfred_engine.predict_emotional_spend(
            {
                "amount": payload["amount"],
                "category": payload["category"],
                "description": payload["description"],
            }
        )
        if "error" in base:
            return {
                "is_emotional": False,
                "confidence": 0.05,
                "reason": str(base["error"]),
            }
        return {
            "is_emotional": bool(base.get("is_emotional")),
            "confidence": float(base.get("confidence", 0) or 0),
            "reason": "baseline expense inference was used",
        }

    def _predict_text_probability(self, description: str) -> float | None:
        if not self._model_available or not description:
            return None

        inputs = self.tokenizer(description, return_tensors="pt", truncation=True)
        with self._torch.no_grad():
            output = self.model(**inputs)
        scores = self._torch.softmax(output.logits, dim=1)
        if scores.shape[1] >= 2:
            return float(scores[0][1])
        return float(self._torch.max(scores))

    def _as_float(self, value) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

emotional_bert = EmotionalBERT()
