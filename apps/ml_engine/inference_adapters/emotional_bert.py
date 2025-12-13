from transformers import BertTokenizer, BertForSequenceClassification
import torch
import os
from .base_adapter import BaseModelAdapter

MODEL_PATH = "ml_models/alfred/emotional_bert/"

class EmotionalBERT(BaseModelAdapter):

    def load(self):
        self.tokenizer = BertTokenizer.from_pretrained(MODEL_PATH)
        self.model = BertForSequenceClassification.from_pretrained(MODEL_PATH)
        self.model.eval()

    def predict(self, text):
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True)
        with torch.no_grad():
            out = self.model(**inputs)
        scores = torch.softmax(out.logits, dim=1)
        return {
            "is_emotional": bool(torch.argmax(scores)),
            "confidence": float(torch.max(scores))
        }

emotional_bert = EmotionalBERT()
