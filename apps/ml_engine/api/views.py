from apps.ml_engine.core.alfred_router import alfred_router

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.ml_engine.behavior.behavior_signature import behavior_signature
from apps.ml_engine.behavior.anomaly_detector import anomaly_detector
from apps.ml_engine.behavior.personalizer import personalizer
from apps.ml_engine.behavior.insight_generator import insight_generator

from apps.ml_engine.self_improve.advanced_engine import self_improve_engine

class EmotionalSpendAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        result = alfred_router.route("emotion-expense", request.data)
        return Response(result)

class AlfredExplainAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        payload = request.data

        expenses = payload.get("expenses", [])
        stress = payload.get("stress", [])
        prediction = payload.get("prediction", 0)

        sig = behavior_signature.generate_signature(expenses, stress)

        expense_spike, amount = anomaly_detector.detect_expense_spike(expenses)
        anomalies = {
            "expense_spike": expense_spike,
            "spike_amount": amount
        }

        insights = insight_generator.generate_insights(sig, anomalies)

        tone = personalizer.personalize_ai_tone(sig["stress_avg"])

        return Response({
            "signature": sig,
            "anomalies": anomalies,
            "insights": insights,
            "recommended_tone": tone
        })

class SelfImproveAPI(APIView):
    def get(self, request):
        from apps.ml_engine.self_improve.advanced_engine import self_improve_engine
        result = self_improve_engine.run_full_analysis()
        return Response(result)