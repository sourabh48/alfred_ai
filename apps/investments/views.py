from collections import defaultdict
from datetime import date
from decimal import Decimal, DecimalException, localcontext

from django.db.models import Count, Max
from rest_framework.generics import ListAPIView, ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from django.utils import timezone

from alfred_ai.services.materialized_cache import materialize_payload
from apps.integrations.services.verified_intelligence import freshness_snapshot, proof_contract_payload
from alfred_ai.services.currency import RUPEE
from alfred_ai.services.exchange_rates import approximate
from .services.beginner_guide import beginner_guide
from .services.portfolio_intelligence import portfolio_intelligence_service
from .models import Investment, InvestmentImportDocument
from .money import investment_money, investment_total_float
from .serializers import InvestmentImportDocumentSerializer, InvestmentSerializer


class FundSearchView(APIView):
    """AMFI funds by name, so a holding gets its scheme code without the person knowing it."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .services.fund_prices import search_funds
        return Response({"funds": search_funds(request.query_params.get("q", "")[:80])})


class InvestmentListCreateView(ListCreateAPIView):
    serializer_class = InvestmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Investment.objects.filter(user=self.request.user).order_by("-current_value", "-id")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class InvestmentDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = InvestmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Investment.objects.filter(user=self.request.user)


class InvestmentImportDocumentListView(ListAPIView):
    serializer_class = InvestmentImportDocumentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return InvestmentImportDocument.objects.filter(user=self.request.user).prefetch_related("linked_investments")


class InvestmentSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        revision = f"{_investment_revision(request.user)}:market-v3:{timezone.localdate().isoformat()}"
        payload = materialize_payload(
            namespace="investments-summary",
            user_id=request.user.id,
            revision=revision,
            ttl_seconds=45,
            builder=lambda: _investment_summary_payload(request.user),
        )
        # Cached owner totals cannot extend a provider's evidence lifetime.
        context = payload.get("market_context") or {}
        context_freshness = freshness_snapshot(context.get("evidence") or [])
        if not context_freshness["proof_complete"]:
            payload["market_context"] = {**context, "freshness": context_freshness, "suggestions": [{
                "type": "source_unavailable", "message": "Market guidance unavailable: source evidence expired or is missing. Recorded holdings are unchanged."
            }]}
        watchlist = payload.get("watchlist") or {}
        if watchlist.get("available"):
            evidence = watchlist.get("evidence") or []
            freshness = freshness_snapshot(evidence[:3])
            if len(evidence) < 3 or not freshness["proof_complete"]:
                payload["watchlist"] = {**watchlist, "available": False, "items": [], "freshness": freshness,
                    "summary": "Watchlist unavailable: cached source evidence expired. Recorded holdings are unchanged."}
        payload["beginner"] = beginner_guide(request.user, payload["watchlist"])  # after the freshness check above
        # Display only, after the cache: the viewer's currency and today's rate are not part of the stored totals.
        summary = payload["summary"]
        groups = summary.get("other_currencies") or []
        summary["other_currencies"], summary["display_currency"] = approximate(
            request, groups, ("total_value", "total_invested", "monthly_sip"),
            {"total_value": [(summary["total_value"], RUPEE)] + [(group["total_value"], group["currency"]) for group in groups]})
        return Response(payload)


class InvestmentAllocationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        revision = _investment_revision(request.user)
        payload = materialize_payload(
            namespace="investments-allocation",
            user_id=request.user.id,
            revision=revision,
            ttl_seconds=60,
            builder=lambda: _investment_allocation_payload(request.user),
        )
        return Response(payload)


class InvestmentGrowthView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        as_of = timezone.localdate()
        revision = f"{_investment_revision(request.user)}:growth-v3:{as_of:%Y-%m}"
        payload = materialize_payload(
            namespace="investments-growth",
            user_id=request.user.id,
            revision=revision,
            ttl_seconds=90,
            builder=lambda: _investment_growth_payload(request.user, as_of=as_of),
        )
        return Response(payload)


def _investment_revision(user) -> str:
    state = Investment.objects.filter(user=user).aggregate(count=Count("id"), latest=Max("updated_at"))
    return f"investments-money-v1:{state['count']}:{state['latest'].isoformat() if state['latest'] else '0'}"


def _other_currency_groups(positions) -> list[dict]:
    """Per-currency totals for positions outside rupee totals; never converted or added to INR."""
    groups: dict[str, dict] = {}
    for item in positions:
        if item.currency and item.currency != RUPEE:
            group = groups.setdefault(item.currency, dict(currency=item.currency, positions=0, total_value=Decimal("0"),
                                                          total_invested=Decimal("0"), monthly_sip=Decimal("0")))
            group["positions"] += 1
            group["total_value"] += item.current_value
            group["total_invested"] += item.invested_amount
            group["monthly_sip"] += item.monthly_sip
    money = ("total_value", "total_invested", "monthly_sip")
    return [{**group, **{key: format(group[key], ".2f") for key in money}} for _, group in sorted(groups.items())]


def _investment_summary_payload(user) -> dict:
    positions = list(Investment.objects.filter(user=user).order_by("-current_value", "-id"))
    investments = [item for item in positions if item.currency in (None, RUPEE)]
    total_value = sum(item.current_value for item in investments)
    total_invested = sum(item.invested_amount for item in investments)
    total_sip = sum(item.monthly_sip for item in investments)
    weighted_return = (
        sum(item.current_value * Decimal(str(item.annual_return_rate)) for item in investments) / total_value if total_value else 0.0
    )
    with localcontext() as context:
        context.prec = max(28, Decimal(str(weighted_return)).adjusted() + 4)
        annual_return = float(round(weighted_return, 2))
    gain_loss = total_value - total_invested
    analysis = portfolio_intelligence_service.analyze_portfolio_risk(user)
    market_context = portfolio_intelligence_service.get_market_trends_and_suggestions(user)
    watchlist = portfolio_intelligence_service.build_short_horizon_watchlist(user)
    evidence = market_context.get("evidence", [])
    evidence_freshness = market_context.get("freshness", {})

    return {
        "summary": {
            "total_value": investment_total_float(total_value),
            "total_invested": investment_total_float(total_invested),
            "monthly_sip": investment_total_float(total_sip),
            "annual_return": annual_return,
            "gain_loss": investment_total_float(gain_loss),
            "risk": _portfolio_risk(investments),
            "positions": len(positions),
            "positions_in_rupee_totals": len(investments),
            "other_currencies": _other_currency_groups(positions),
        },
        "analysis": analysis,
        "market_context": market_context,
        "watchlist": watchlist,
        "positions": InvestmentSerializer(positions, many=True).data,
        "grounding": {
            "history": {
                "positions": len(investments),
                "total_value": investment_total_float(total_value),
                "total_invested": investment_total_float(total_invested),
                "monthly_sip": investment_total_float(total_sip),
            },
            "evidence": evidence,
            "freshness": evidence_freshness,
            "proof_contract": proof_contract_payload(
                evidence_items=evidence,
                freshness=evidence_freshness,
                required_sources=["Yahoo Finance", "World Bank"],
                advisory_surface="investment_summary",
            ),
            "notes": [
                "Portfolio guidance is grounded in user-held positions plus verified market and macro context.",
                "Advice remains allocation guidance, not a claim of advisor-licensed suitability.",
            ],
        },
    }


def _investment_allocation_payload(user) -> dict:
    investments = list(Investment.objects.filter(user=user).in_rupee_totals())
    buckets: dict[str, Decimal] = defaultdict(Decimal)
    labels = dict(Investment.ASSET_TYPES)

    for item in investments:
        buckets[item.asset_type] += item.current_value

    ordered = sorted(buckets.items(), key=lambda pair: pair[1], reverse=True)
    return {
        "labels": [labels.get(key, key.replace("_", " ").title()) for key, _ in ordered],
        "values": [investment_total_float(value) for _, value in ordered],
    }


def _investment_growth_payload(user, *, as_of: date | None = None) -> dict:
    investments = list(Investment.objects.filter(user=user).in_rupee_totals())
    today = (as_of or timezone.localdate()).replace(day=1)
    labels = []
    values = []
    months_elapsed = list(range(13))

    for month_index in months_elapsed:
        target_year = today.year + ((today.month - 1 + month_index) // 12)
        target_month = ((today.month - 1 + month_index) % 12) + 1
        labels.append(date(target_year, target_month, 1).strftime("%b %Y"))

    unavailable_reason = ""
    try:
        for month_index in months_elapsed:
            projected_value = Decimal("0")
            for item in investments:
                projected_value += _project_position_money(
                    current_value=item.current_value,
                    monthly_sip=item.monthly_sip,
                    annual_return_rate=item.annual_return_rate,
                    months=month_index,
                )
            values.append(investment_total_float(projected_value))
    except (ValueError, DecimalException, OverflowError):
        values = []
        unavailable_reason = "Projection unavailable: a recorded return or forecast is outside the supported numeric range. Review your entered return assumptions; recorded holdings are unchanged."

    return {
        "labels": labels,
        "values": values,
        "months_elapsed": months_elapsed,
        "available": not unavailable_reason,
        "unavailable_reason": unavailable_reason,
        "assumptions": {
            "month_zero": "recorded_current_value",
            "contribution_timing": "beginning_of_month",
            "annual_return_rate_source": "user_entered",
            "monthly_return_rate_formula": "annual_return_rate / 1200",
            "note": "Future months add the entered monthly SIP before applying one month's assumed return; actual returns can differ.",
        },
    }


def _portfolio_risk(investments: list[Investment]) -> str:
    if not investments:
        return "No data"

    total_value = sum(item.current_value for item in investments) or Decimal("1")
    high_risk_weight = sum(
        item.current_value
        for item in investments
        if item.asset_type in {"equity", "crypto", "reit"} or item.risk_level.lower() == "high"
    )
    ratio = high_risk_weight / total_value
    if ratio >= Decimal("0.65"):
        return "High"
    if ratio >= Decimal("0.35"):
        return "Moderate"
    return "Conservative"


def _project_position_value(**kwargs) -> float:
    """Preserve the numeric helper contract for existing projection callers."""
    return float(_project_position_money(**kwargs))


def _project_position_money(*, current_value, monthly_sip, annual_return_rate, months: int) -> Decimal:
    """Start at the recorded value; each future month adds SIP before growth.

    The user-entered annual percentage is divided by 1200 to obtain the
    assumed monthly rate. Month zero includes no new contribution or growth.
    """
    value = investment_money(current_value)
    monthly_rate = Decimal(str(annual_return_rate or 0)) / Decimal("1200")
    if not monthly_rate.is_finite():
        raise ValueError("Return rate must be finite.")
    contribution = investment_money(monthly_sip)
    for _ in range(months):
        value = (value + contribution) * (1 + monthly_rate)
    return value


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def import_investment_pdf(request):
    upload = request.FILES.get("file")
    if not upload:
        return Response({"error": "Upload an investment PDF or statement first."}, status=status.HTTP_400_BAD_REQUEST)
    if not upload.name.lower().endswith('.pdf'):
        return Response({'detail': 'Choose a PDF investment source.'}, status=400)

    from alfred_ai.services.api_errors import safe_error_details
    from alfred_ai.services.upload_limits import UploadLimitExceeded, UploadFormatError, UploadStorageUnavailable, UploadProtectionUnavailable
    from .services.import_review import stage_investment_document
    try:
        parsed = portfolio_intelligence_service.parse_portfolio_pdf(upload, request.user, filename=upload.name)
        document = InvestmentImportDocument.objects.get(pk=parsed['upload_id'], user=request.user)
    except (UploadLimitExceeded, UploadFormatError, UploadStorageUnavailable, UploadProtectionUnavailable) as exc:
        return Response(safe_error_details(exc, type(exc).default_detail, logger_name=__name__), status=exc.status_code)
    except Exception as exc:
        diagnostic = safe_error_details(exc, 'Investment extraction could not complete. The source is retained for review.', logger_name=__name__)
        try:
            document = stage_investment_document(user=request.user, parsed={}, upload_file=upload)
            document.extracted_payload.update(error_code='investment_extraction_failed', error_id=diagnostic['error_id'])
            document.save(update_fields=['extracted_payload'])
        except Exception as persistence_error:
            return Response(safe_error_details(persistence_error, 'The source could not be saved. Keep the original and retry.', logger_name=__name__), status=500)
    return Response(dict(success=True, message=document.summary, investments=[],
        upload=InvestmentImportDocumentSerializer(document, context={'request': request}).data,
        raw_file_retention={'deleted': False, 'enabled': False}), status=201)
