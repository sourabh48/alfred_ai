from rest_framework.generics import ListCreateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.integrations.services.verified_intelligence import freshness_snapshot
from .models import RiskSignal
from .serializers import RiskSignalSerializer
from .services import risk_intelligence

class RiskSignalListCreateView(ListCreateAPIView):
    serializer_class = RiskSignalSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return RiskSignal.objects.filter(user=self.request.user).order_by("-timestamp")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def risk_outlook(request):
    payload = risk_intelligence.build_outlook(request.user)
    return Response(
        {
            "history": RiskSignalSerializer(payload["history"], many=True).data,
            "latest": RiskSignalSerializer(payload["latest"]).data if payload["latest"] else None,
            "outlook": payload["outlook"],
            "summary": payload["summary"],
            "macro_context": payload["macro_context"],
            "consolidated_risks": payload["consolidated_risks"],
            "related_news": payload["related_news"],
            "action_items": payload["action_items"],
            "module_signals": payload["module_signals"],
            "evidence": payload["evidence"],
            "evidence_freshness": payload.get("evidence_freshness", freshness_snapshot(payload.get("evidence", []))),
            "insights": payload["insights"],
        }
    )
