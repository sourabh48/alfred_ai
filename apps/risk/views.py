from django.db.models import Count, Max, Sum
from rest_framework.generics import ListCreateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from alfred_ai.services.materialized_cache import materialize_payload
from apps.behavioral.models import BehavioralSignal
from apps.career.models import CareerJobAnalysis, CareerProfile
from apps.expenses.models import Expense
from apps.family.models import Dependent
from apps.integrations.models import VerifiedExternalInsight
from apps.integrations.services.verified_intelligence import freshness_snapshot
from apps.mobility.models import (
    BikeConditionSnapshot,
    BikeDocument,
    BikeIssueReport,
    BikeProfile,
    BikeServiceRecord,
    FuelRefillLog,
    TripLog,
)

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
    payload = materialize_payload(
        namespace="risk-outlook",
        user_id=request.user.id,
        revision=_risk_outlook_revision(request.user),
        ttl_seconds=60,
        builder=lambda: _build_risk_outlook_payload(request.user),
    )
    return Response(payload)


def _risk_outlook_revision(user) -> str:
    risk_meta = RiskSignal.objects.filter(user=user).aggregate(
        count=Count("id"),
        max_id=Max("id"),
        latest_signal=Max("timestamp"),
    )
    behavior_meta = BehavioralSignal.objects.filter(user=user).aggregate(
        count=Count("id"),
        max_id=Max("id"),
        latest_signal=Max("timestamp"),
    )
    profile = CareerProfile.objects.filter(user=user).values("id", "role", "experience_years", "skills", "last_salary").first() or {}
    job_meta = CareerJobAnalysis.objects.filter(user=user).aggregate(
        count=Count("id"),
        max_id=Max("id"),
        latest_update=Max("updated_at"),
    )
    expense_meta = Expense.objects.filter(user=user).aggregate(
        count=Count("id"),
        max_id=Max("id"),
        latest_expense=Max("transaction_date"),
        total_amount=Sum("amount"),
    )
    dependent_meta = Dependent.objects.filter(user=user).aggregate(count=Count("id"), max_id=Max("id"))
    bike_profile_meta = BikeProfile.objects.filter(user=user).aggregate(
        count=Count("id"),
        max_id=Max("id"),
        latest_update=Max("updated_at"),
    )
    service_meta = BikeServiceRecord.objects.filter(user=user).aggregate(
        count=Count("id"),
        max_id=Max("id"),
        latest_service=Max("service_date"),
    )
    fuel_meta = FuelRefillLog.objects.filter(user=user).aggregate(
        count=Count("id"),
        max_id=Max("id"),
        latest_refill=Max("refill_date"),
    )
    trip_meta = TripLog.objects.filter(user=user).aggregate(
        count=Count("id"),
        max_id=Max("id"),
        latest_trip=Max("log_date"),
    )
    issue_meta = BikeIssueReport.objects.filter(user=user).aggregate(
        count=Count("id"),
        max_id=Max("id"),
        latest_update=Max("updated_at"),
    )
    document_meta = BikeDocument.objects.filter(user=user).aggregate(
        count=Count("id"),
        max_id=Max("id"),
        latest_update=Max("updated_at"),
    )
    condition_meta = BikeConditionSnapshot.objects.filter(user=user).aggregate(
        count=Count("id"),
        max_id=Max("id"),
        latest_capture=Max("captured_at"),
    )
    evidence_meta = VerifiedExternalInsight.objects.filter(is_active=True).aggregate(
        count=Count("id"),
        max_id=Max("id"),
        latest_verified=Max("verified_at"),
    )
    profile_token = ":".join(
        str(value or "")
        for value in (
            profile.get("id"),
            profile.get("role"),
            profile.get("experience_years"),
            profile.get("skills"),
            profile.get("last_salary"),
            getattr(user, "monthly_income", ""),
            getattr(user, "rent_or_emi", ""),
            getattr(user, "city", ""),
            getattr(user, "city_type", ""),
        )
    )
    return "|".join(
        str(value or "")
        for value in (
            "risk-outlook-v2",
            risk_meta["count"],
            risk_meta["max_id"],
            risk_meta["latest_signal"],
            behavior_meta["count"],
            behavior_meta["max_id"],
            behavior_meta["latest_signal"],
            job_meta["count"],
            job_meta["max_id"],
            job_meta["latest_update"],
            expense_meta["count"],
            expense_meta["max_id"],
            expense_meta["latest_expense"],
            expense_meta["total_amount"],
            dependent_meta["count"],
            dependent_meta["max_id"],
            bike_profile_meta["count"],
            bike_profile_meta["max_id"],
            bike_profile_meta["latest_update"],
            service_meta["count"],
            service_meta["max_id"],
            service_meta["latest_service"],
            fuel_meta["count"],
            fuel_meta["max_id"],
            fuel_meta["latest_refill"],
            trip_meta["count"],
            trip_meta["max_id"],
            trip_meta["latest_trip"],
            issue_meta["count"],
            issue_meta["max_id"],
            issue_meta["latest_update"],
            document_meta["count"],
            document_meta["max_id"],
            document_meta["latest_update"],
            condition_meta["count"],
            condition_meta["max_id"],
            condition_meta["latest_capture"],
            evidence_meta["count"],
            evidence_meta["max_id"],
            evidence_meta["latest_verified"],
            profile_token,
        )
    )


def _build_risk_outlook_payload(user) -> dict:
    payload = risk_intelligence.build_outlook(user)
    return {
        "history": RiskSignalSerializer(payload["history"], many=True).data,
        "latest": RiskSignalSerializer(payload["latest"]).data if payload["latest"] else None,
        "outlook": payload["outlook"],
        "summary": payload["summary"],
        "macro_context": payload["macro_context"],
        "consolidated_risks": payload["consolidated_risks"],
        "related_news": payload["related_news"],
        "action_items": payload["action_items"],
        "module_signals": payload["module_signals"],
        "financial_baseline": payload.get("financial_baseline", {}),
        "evidence": payload["evidence"],
        "evidence_freshness": payload.get("evidence_freshness", freshness_snapshot(payload.get("evidence", []))),
        "grounding": payload.get("grounding", {}),
        "insights": payload["insights"],
    }
