class AlfredPreprocessor:

    def clean_text(self, text):
        if not text:
            return ""
        return str(text).strip().lower()

    def normalize_amount(self, value):
        try:
            return float(value)
        except:
            return 0.0

    def preprocess_expense(self, data):
        return {
            "amount": self.normalize_amount(data.get("amount")),
            "category": self.clean_text(data.get("category")),
            "description": self.clean_text(data.get("description")),
        }

preprocessor = AlfredPreprocessor()
