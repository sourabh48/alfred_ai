class Personalizer:

    def suggest_savings_strategy(self, signature):
        if signature["avg_expense"] > signature["stress_avg"] * 100:
            return "You may be stress-spending. Let's set a cap and build a buffer."
        elif signature["expense_volatility"] > 500:
            return "Your spending fluctuates. A fixed monthly budget will help."
        else:
            return "Your spending is stable. Let's optimize investments."

    def personalize_ai_tone(self, stress_level):
        if stress_level > 7:
            return "gentle"
        elif stress_level > 4:
            return "encouraging"
        else:
            return "energetic"

personalizer = Personalizer()
