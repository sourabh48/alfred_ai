from rest_framework.decorators import api_view, permission_classes
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Count, Max

from alfred_ai.services.materialized_cache import materialize_payload
from apps.expenses.services.financial_intelligence import resolve_canonical_financial_baseline
from apps.integrations.services import verified_intelligence
from apps.integrations.services.verified_intelligence import freshness_snapshot, proof_contract_payload
from .models import Dependent
from .serializers import DependentSerializer

class DependentListCreateView(ListCreateAPIView):
    serializer_class = DependentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Dependent.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class DependentDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = DependentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Dependent.objects.filter(user=self.request.user)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def family_growth(request):
    """Get family net-worth growth projection."""
    try:
        baseline = resolve_canonical_financial_baseline(request.user)
        payload = materialize_payload(
            namespace="family-growth",
            user_id=request.user.id,
            revision=_family_growth_revision(request.user, baseline),
            ttl_seconds=60,
            builder=lambda: _family_growth_payload(request.user, baseline),
        )
        return Response(payload)
    except Exception as e:
        return Response({"error": str(e)}, status=500)


def _family_growth_revision(user, baseline: dict) -> str:
    dependent_meta = Dependent.objects.filter(user=user).aggregate(count=Count("id"), max_id=Max("id"), max_age=Max("age"))
    return "|".join(
        str(value or "")
        for value in [
            dependent_meta["count"],
            dependent_meta["max_id"],
            dependent_meta["max_age"],
            baseline.get("total_assets", 0),
            baseline.get("total_liabilities", 0),
            baseline.get("net_worth", 0),
            baseline.get("savings_capacity", 0),
        ]
    )


def _family_growth_payload(user, baseline: dict) -> dict:
    dependents = Dependent.objects.filter(user=user)
    total_assets = float(baseline.get("total_assets", 0) or 0)
    total_liabilities = float(baseline.get("total_liabilities", 0) or 0)
    current_net_worth = float(baseline.get("net_worth", 0) or 0)
    savings_capacity = float(baseline.get("savings_capacity", 0) or 0)
    evidence = []
    for result in (verified_intelligence.ppf_reference(), verified_intelligence.nps_tax_reference()):
        evidence.append(result.evidence)
    evidence_freshness = freshness_snapshot(evidence)

    projections = []
    for year in range(1, 11):
        projected_value = current_net_worth * (1.08 ** year)
        projections.append({
            "year": year,
            "projected_net_worth": round(projected_value, 2),
        })

    grounding = {
        "history": {
            "current_net_worth": round(current_net_worth, 2),
            "total_assets": round(total_assets, 2),
            "total_liabilities": round(total_liabilities, 2),
            "savings_capacity": round(savings_capacity, 2),
            "dependents_count": dependents.count(),
        },
        "evidence": evidence,
        "freshness": evidence_freshness,
        "proof_contract": proof_contract_payload(
            evidence_items=evidence,
            freshness=evidence_freshness,
            required_sources=["India Post", "NPS Trust"],
            advisory_surface="family_growth",
        ),
        "notes": [
            "The 8 percent growth rate remains a planning heuristic, not a guaranteed return forecast.",
            "Official long-term savings references are attached as planning context, not as a recommendation to choose a specific product.",
        ],
    }

    return {
        "current_net_worth": round(current_net_worth, 2),
        "total_assets": round(total_assets, 2),
        "total_liabilities": round(total_liabilities, 2),
        "dependents_count": dependents.count(),
        "growth_rate": 8.0,
        "projection_basis": "heuristic_8_percent_compound_projection",
        "financial_baseline": baseline,
        "projections": projections,
        "grounding": grounding,
        "evidence_freshness": grounding["freshness"],
        "insights": [
            f"Current family net worth from canonical balance sheet: INR {current_net_worth:,.0f}",
            f"Supporting {dependents.count()} dependents",
            "Projection uses a simple 8% annual heuristic, not a guaranteed forecast",
            "Consider increasing SIP investments for faster growth",
            "Emergency fund should cover 6 months of expenses",
        ],
    }
