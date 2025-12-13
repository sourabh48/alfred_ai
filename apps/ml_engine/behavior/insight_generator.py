class InsightGenerator:

    def generate_insights(self, signature, anomalies):
        insights = []

        if anomalies.get("expense_spike"):
            insights.append("You had a sudden expense spike. Let's review your categories.")

        if signature["stress_avg"] > 6:
            insights.append("Stress levels rising. Consider reducing workload or spending.")

        if signature["expense_volatility"] > 700:
            insights.append("Your expenses are highly volatile, consider setting soft limits.")

        if not insights:
            insights.append("All systems normal. Keep up the balanced spending!")

        return insights

insight_generator = InsightGenerator()
