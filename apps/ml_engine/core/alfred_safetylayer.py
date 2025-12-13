class AlfredSafetyLayer:

    def validate_numerical(self, key, value, min_val=0, max_val=1_000_000):
        try:
            v = float(value)
            if v < min_val or v > max_val:
                return False, f"{key} out of valid range"
            return True, v
        except:
            return False, f"{key} invalid"

    def validate_expense(self, exp):
        ok, amt = self.validate_numerical("amount", exp.get("amount"))
        if not ok:
            return False, ok

        # suspicious pattern protections
        if amt > 10_00_000:
            return False, "Unrealistic expense amount"

        return True, "OK"

    def compute_trust_score(self, exp):
        """Higher trust score means data is high quality."""
        score = 1.0

        if exp.get("amount", 0) <= 0:
            score -= 0.3

        if exp.get("category") in ["other", "", None]:
            score -= 0.1

        return max(min(score, 1.0), 0.0)

alfred_safety = AlfredSafetyLayer()
