class AlfredExplainability:

    def explain_salary_prediction(self, input_data, prediction):
        return {
            "title": "Salary Growth Projection",
            "reasoning": [
                f"Experience, income patterns, and skill trends were analyzed.",
                f"Your projected salary growth is {round(prediction, 2)} per month."
            ],
            "factors": input_data
        }

    def explain_expense_forecast(self, sequence, prediction):
        return {
            "title": "Expense Forecast",
            "reasoning": [
                "LSTM analyzed your last 10–100 expenses.",
                "It detected trend stability and seasonality."
            ],
            "expected_next_expense": round(prediction, 2),
            "recent_pattern": sequence[-5:]
        }

    def explain_emotional_spending(self, input_data, result):
        return {
            "title": "Emotional Spending Detection",
            "is_emotional": result["is_emotional"],
            "confidence": result["confidence"],
            "reasoning": [
                "BERT interpreted your purchase description and category.",
                "The behavior was compared with your emotional signature."
            ]
        }

    def explain_burnout(self, features, score):
        return {
            "title": "Burnout Risk Analysis",
            "burnout_score": round(score, 2),
            "reasoning": [
                "Evaluated stress, sleep time, work hours, and emotional patterns.",
                "Higher score = higher probability of fatigue or burnout."
            ]
        }

    def explain_risk(self, features, result):
        return {
            "title": "Life Event Risk Radar",
            "risk_profile": result,
            "reasoning": [
                "Classifier used behavioral data + stress metrics.",
                "This helps predict possible near-future risk factors."
            ]
        }

explain_engine = AlfredExplainability()
