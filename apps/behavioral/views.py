from django.db.models import Count, Max, Sum
from rest_framework.generics import ListCreateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from alfred_ai.services.materialized_cache import materialize_payload
from apps.expenses.models import Expense

from .models import BehavioralSignal
from .serializers import BehavioralSignalSerializer
from .services import build_behavioral_fingerprint, build_behavioral_stress

class BehavioralSignalListCreateView(ListCreateAPIView):
    serializer_class = BehavioralSignalSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return BehavioralSignal.objects.filter(user=self.request.user).order_by("-timestamp", "-id")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def behavioral_fingerprint(request):
    """Get user's behavioral fingerprint."""
    try:
        payload = materialize_payload(
            namespace="behavioral-fingerprint",
            user_id=request.user.id,
            revision=_behavioral_dashboard_revision(request.user),
            ttl_seconds=60,
            builder=lambda: build_behavioral_fingerprint(request.user),
        )
        return Response(payload)
    except Exception as e:
        return Response({"error": str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def behavioral_stress(request):
    """Get stress analysis."""
    try:
        payload = materialize_payload(
            namespace="behavioral-stress",
            user_id=request.user.id,
            revision=_behavioral_dashboard_revision(request.user),
            ttl_seconds=60,
            builder=lambda: build_behavioral_stress(request.user),
        )
        return Response(payload)
    except Exception as e:
        return Response({"error": str(e)}, status=500)


def _behavioral_dashboard_revision(user) -> str:
    signal_meta = BehavioralSignal.objects.filter(user=user).aggregate(
        count=Count("id"),
        max_id=Max("id"),
        latest_signal=Max("timestamp"),
    )
    expense_meta = Expense.objects.filter(user=user).aggregate(
        count=Count("id"),
        max_id=Max("id"),
        latest_expense=Max("transaction_date"),
        total_amount=Sum("amount"),
    )
    profile_token = ":".join(
        str(value or "")
        for value in (
            getattr(user, "monthly_income", ""),
            getattr(user, "rent_or_emi", ""),
            getattr(user, "city_type", ""),
        )
    )
    return "|".join(
        str(value or "")
        for value in (
            "behavioral-dashboard-v2",
            signal_meta["count"],
            signal_meta["max_id"],
            signal_meta["latest_signal"],
            expense_meta["count"],
            expense_meta["max_id"],
            expense_meta["latest_expense"],
            expense_meta["total_amount"],
            profile_token,
        )
    )
