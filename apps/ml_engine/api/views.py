from apps.ml_engine.core.alfred_router import alfred_router
from apps.ml_engine.runtime_control import build_runtime_status, grant_training_consent, revoke_training_consent
from apps.ml_engine.training.orchestrator import run_training_cycle, training_health_snapshot
from apps.expenses.services.financial_intelligence import build_financial_intelligence

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied, ValidationError
from apps.ml_engine.behavior.behavior_signature import behavior_signature
from apps.ml_engine.behavior.anomaly_detector import anomaly_detector
from apps.ml_engine.behavior.personalizer import personalizer
from apps.ml_engine.behavior.insight_generator import insight_generator

class EmotionalSpendAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        payload = request.data.copy()
        payload["user"] = request.user
        result = alfred_router.route("emotional-spend", payload)
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


class AlfredPersonalInsightsAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        intelligence = build_financial_intelligence(request.user)
        return Response(intelligence)


class SelfImproveAPI(APIView):
    def get(self, request):
        from apps.ml_engine.self_improve.advanced_engine import self_improve_engine
        result = self_improve_engine.run_full_analysis()
        return Response(result)


class MLRuntimeStatusAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        payload = build_runtime_status(request.user)
        payload["training_health"] = training_health_snapshot()
        return Response(payload)


class MLRuntimeControlAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not request.user.is_superuser:
            raise PermissionDenied("Only superusers can manage ALFRED training startup.")

        action = str(request.data.get("action") or "").strip().lower()
        if action == "approve":
            grant_training_consent(request.user)
            return Response(
                {
                    "detail": "ALFRED startup auto-training has been approved for this environment.",
                    "status": build_runtime_status(request.user),
                }
            )
        if action == "revoke":
            revoke_training_consent(request.user)
            return Response(
                {
                    "detail": "ALFRED startup auto-training approval has been revoked.",
                    "status": build_runtime_status(request.user),
                }
            )
        if action == "run_now":
            status = build_runtime_status(request.user)
            if not status["approval"]["granted"]:
                raise ValidationError({"detail": "Approve startup training first."})
            if not status["runtime"]["ready"]:
                raise ValidationError({"detail": status["runtime"]["reason"] or "Training runtime is unavailable."})
            result = run_training_cycle(trigger="superuser_manual", force=True)
            return Response(
                {
                    "detail": "ALFRED training cycle finished.",
                    "status": build_runtime_status(request.user),
                    "training_result": result,
                }
            )
        raise ValidationError({"detail": "Unsupported action."})
