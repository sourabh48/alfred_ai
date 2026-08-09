from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Count, Max

from alfred_ai.services.materialized_cache import invalidate_user_materialized_payloads
from alfred_ai.services.materialized_cache import materialize_payload
from apps.expenses.services.financial_intelligence import resolve_canonical_financial_baseline
from apps.integrations.services import verified_intelligence
from apps.integrations.services.verified_intelligence import freshness_snapshot, proof_contract_payload
from .models import Dependent, FamilyAccountLink
from .serializers import DependentSerializer
from .services import (
    accept_family_link_code,
    build_family_link_snapshot,
    create_family_link_invite,
    family_context_user_ids,
    family_financial_user_ids,
    revoke_family_link,
)

class DependentListCreateView(ListCreateAPIView):
    serializer_class = DependentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Dependent.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
        invalidate_user_materialized_payloads(self.request.user.id, reason="family_dependent_changed")

class DependentDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = DependentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Dependent.objects.filter(user=self.request.user)

    def perform_update(self, serializer):
        serializer.save(user=self.request.user)
        invalidate_user_materialized_payloads(self.request.user.id, reason="family_dependent_changed")

    def perform_destroy(self, instance):
        user_id = self.request.user.id
        instance.delete()
        invalidate_user_materialized_payloads(user_id, reason="family_dependent_changed")


class FamilyAccountLinkListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(build_family_link_snapshot(request.user))

    def post(self, request):
        link, code = create_family_link_invite(request.user)
        invalidate_user_materialized_payloads(request.user.id, reason="family_link_invite_created")
        payload = build_family_link_snapshot(request.user)
        payload["invite"] = _serialize_one_time_invite(link, code)
        return Response(payload, status=status.HTTP_201_CREATED)


class FamilyAccountLinkAcceptView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            link = accept_family_link_code(request.user, request.data.get("invite_code") or request.data.get("code") or "")
        except ValidationError as exc:
            return Response({"detail": _validation_detail(exc)}, status=status.HTTP_400_BAD_REQUEST)
        invalidate_user_materialized_payloads(request.user.id, reason="family_link_accepted")
        invalidate_user_materialized_payloads(link.created_by_id, reason="family_link_accepted")
        return Response(build_family_link_snapshot(request.user))


class FamilyAccountLinkRevokeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            link = revoke_family_link(request.user, pk)
        except ValidationError as exc:
            return Response({"detail": _validation_detail(exc)}, status=status.HTTP_404_NOT_FOUND)
        invalidate_user_materialized_payloads(request.user.id, reason="family_link_revoked")
        if link.created_by_id and link.created_by_id != request.user.id:
            invalidate_user_materialized_payloads(link.created_by_id, reason="family_link_revoked")
        if link.linked_user_id and link.linked_user_id != request.user.id:
            invalidate_user_materialized_payloads(link.linked_user_id, reason="family_link_revoked")
        return Response(build_family_link_snapshot(request.user))


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
    context_user_ids = family_context_user_ids(user)
    financial_user_ids = family_financial_user_ids(user)
    dependent_meta = Dependent.objects.filter(user_id__in=context_user_ids).aggregate(count=Count("id"), max_id=Max("id"), max_age=Max("age"))
    link_meta = FamilyAccountLink.objects.filter(status=FamilyAccountLink.STATUS_ACCEPTED).filter(
        linked_user_id__in=set(context_user_ids) | set(financial_user_ids)
    ).aggregate(count=Count("id"), max_id=Max("id"), max_updated=Max("updated_at"))
    return "|".join(
        str(value or "")
        for value in [
            ",".join(str(item) for item in context_user_ids),
            ",".join(str(item) for item in financial_user_ids),
            dependent_meta["count"],
            dependent_meta["max_id"],
            dependent_meta["max_age"],
            link_meta["count"],
            link_meta["max_id"],
            link_meta["max_updated"],
            baseline.get("total_assets", 0),
            baseline.get("total_liabilities", 0),
            baseline.get("net_worth", 0),
            baseline.get("savings_capacity", 0),
        ]
    )


def _family_growth_payload(user, baseline: dict) -> dict:
    context_user_ids = family_context_user_ids(user)
    financial_summary = _family_financial_summary(user, own_baseline=baseline)
    family_baseline = financial_summary["family_financial_baseline"]
    dependents = Dependent.objects.filter(user_id__in=context_user_ids)
    own_dependents_count = Dependent.objects.filter(user=user).count()
    link_snapshot = build_family_link_snapshot(user)
    total_assets = float(family_baseline.get("total_assets", 0) or 0)
    total_liabilities = float(family_baseline.get("total_liabilities", 0) or 0)
    current_net_worth = float(family_baseline.get("net_worth", 0) or 0)
    savings_capacity = float(family_baseline.get("savings_capacity", 0) or 0)
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
            "own_dependents_count": own_dependents_count,
            "linked_family_account_count": link_snapshot["accepted_link_count"],
            "linked_family_dependent_count": link_snapshot["shared_dependent_count"],
            "linked_family_financial_account_count": max(0, family_baseline["member_count"] - 1),
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
        "own_dependents_count": own_dependents_count,
        "linked_family_account_count": link_snapshot["accepted_link_count"],
        "linked_family_dependent_count": link_snapshot["shared_dependent_count"],
        "linked_family_financial_account_count": max(0, family_baseline["member_count"] - 1),
        "shared_family_context": {
            "family_context_user_count": link_snapshot["family_context_user_count"],
            "linked_user_count": link_snapshot["linked_user_count"],
            "financial_member_count": family_baseline["member_count"],
            "share_dependents": True,
            "financial_baseline_scope": "accepted_family_financial_summary",
        },
        "growth_rate": 8.0,
        "projection_basis": "heuristic_8_percent_compound_projection",
        "financial_baseline": family_baseline,
        "own_financial_baseline": baseline,
        "family_financial_members": financial_summary["members"],
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


def _family_financial_summary(user, *, own_baseline: dict) -> dict:
    user_model = get_user_model()
    users_by_id = {
        item.id: item
        for item in user_model.objects.filter(id__in=family_financial_user_ids(user)).order_by("id")
    }
    totals = {
        "monthly_income": 0.0,
        "savings_capacity": 0.0,
        "total_assets": 0.0,
        "total_liabilities": 0.0,
        "net_worth": 0.0,
    }
    members = []

    for user_id in family_financial_user_ids(user):
        member = users_by_id.get(user_id)
        if not member:
            continue
        member_baseline = own_baseline if member.id == user.id else resolve_canonical_financial_baseline(member)
        member_summary = _family_member_financial_summary(
            requesting_user=user,
            member=member,
            baseline=member_baseline,
        )
        members.append(member_summary)
        for key in totals:
            totals[key] += float(member_summary.get(key, 0) or 0)

    family_baseline = {
        "scope": "accepted_family_financial_summary",
        "member_count": len(members),
        "monthly_income": round(totals["monthly_income"], 2),
        "savings_capacity": round(totals["savings_capacity"], 2),
        "total_assets": round(totals["total_assets"], 2),
        "total_liabilities": round(totals["total_liabilities"], 2),
        "net_worth": round(totals["total_assets"] - totals["total_liabilities"], 2),
    }
    return {
        "family_financial_baseline": family_baseline,
        "members": members,
    }


def _family_member_financial_summary(*, requesting_user, member, baseline: dict) -> dict:
    full_name = f"{member.first_name} {member.last_name}".strip()
    return {
        "user_id": member.id,
        "username": member.username,
        "display_name": full_name or member.username,
        "role": "self" if member.id == requesting_user.id else "linked",
        "city": member.city,
        "country": member.country,
        "monthly_income": round(float(baseline.get("monthly_income", 0) or 0), 2),
        "savings_capacity": round(float(baseline.get("savings_capacity", 0) or 0), 2),
        "total_assets": round(float(baseline.get("total_assets", 0) or 0), 2),
        "total_liabilities": round(float(baseline.get("total_liabilities", 0) or 0), 2),
        "net_worth": round(float(baseline.get("net_worth", 0) or 0), 2),
        "source": "canonical_financial_baseline",
    }


def _serialize_one_time_invite(link: FamilyAccountLink, code: str) -> dict:
    return {
        "id": link.id,
        "invite_code": code,
        "expires_at": link.expires_at.isoformat(),
        "status": link.status,
        "stored_as": "sha256_hmac",
    }


def _validation_detail(exc: ValidationError) -> str:
    if hasattr(exc, "messages"):
        return " ".join(str(item) for item in exc.messages)
    return str(exc)
