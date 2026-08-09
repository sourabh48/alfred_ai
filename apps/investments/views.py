from collections import defaultdict
from datetime import date

from django.db.models import Count, Max
from rest_framework.generics import ListAPIView, ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from django.db import transaction

from alfred_ai.services.materialized_cache import materialize_payload
from alfred_ai.services import record_parser_learning
from alfred_ai.services.upload_privacy import purge_uploaded_file_after_extraction
from apps.reports.services import operational_logging_service
from apps.integrations.services.verified_intelligence import proof_contract_payload
from .services.portfolio_intelligence import portfolio_intelligence_service
from .models import Investment, InvestmentImportDocument
from .serializers import InvestmentImportDocumentSerializer, InvestmentSerializer


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
        revision = _investment_revision(request.user)
        payload = materialize_payload(
            namespace="investments-summary",
            user_id=request.user.id,
            revision=revision,
            ttl_seconds=45,
            builder=lambda: _investment_summary_payload(request.user),
        )
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
        revision = _investment_revision(request.user)
        payload = materialize_payload(
            namespace="investments-growth",
            user_id=request.user.id,
            revision=revision,
            ttl_seconds=90,
            builder=lambda: _investment_growth_payload(request.user),
        )
        return Response(payload)


def _investment_revision(user) -> str:
    state = Investment.objects.filter(user=user).aggregate(count=Count("id"), latest=Max("updated_at"))
    return f"investments:{state['count']}:{state['latest'].isoformat() if state['latest'] else '0'}"


def _investment_summary_payload(user) -> dict:
    investments = list(Investment.objects.filter(user=user).order_by("-current_value", "-id"))
    total_value = sum(item.current_value for item in investments)
    total_invested = sum(item.invested_amount for item in investments)
    total_sip = sum(item.monthly_sip for item in investments)
    weighted_return = (
        sum(item.current_value * item.annual_return_rate for item in investments) / total_value if total_value else 0.0
    )
    gain_loss = total_value - total_invested
    analysis = portfolio_intelligence_service.analyze_portfolio_risk(user)
    market_context = portfolio_intelligence_service.get_market_trends_and_suggestions(user)
    watchlist = portfolio_intelligence_service.build_short_horizon_watchlist(user)
    evidence = market_context.get("evidence", [])
    evidence_freshness = market_context.get("freshness", {})

    return {
        "summary": {
            "total_value": round(total_value, 2),
            "total_invested": round(total_invested, 2),
            "monthly_sip": round(total_sip, 2),
            "annual_return": round(weighted_return, 2),
            "gain_loss": round(gain_loss, 2),
            "risk": _portfolio_risk(investments),
            "positions": len(investments),
        },
        "analysis": analysis,
        "market_context": market_context,
        "watchlist": watchlist,
        "positions": InvestmentSerializer(investments, many=True).data,
        "grounding": {
            "history": {
                "positions": len(investments),
                "total_value": round(total_value, 2),
                "total_invested": round(total_invested, 2),
                "monthly_sip": round(total_sip, 2),
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
    investments = list(Investment.objects.filter(user=user))
    buckets: dict[str, float] = defaultdict(float)
    labels = dict(Investment.ASSET_TYPES)

    for item in investments:
        buckets[item.asset_type] += item.current_value

    ordered = sorted(buckets.items(), key=lambda pair: pair[1], reverse=True)
    return {
        "labels": [labels.get(key, key.replace("_", " ").title()) for key, _ in ordered],
        "values": [round(value, 2) for _, value in ordered],
    }


def _investment_growth_payload(user) -> dict:
    investments = list(Investment.objects.filter(user=user))
    today = date.today().replace(day=1)
    labels = []
    values = []

    for month_index in range(12):
        target_year = today.year + ((today.month - 1 + month_index) // 12)
        target_month = ((today.month - 1 + month_index) % 12) + 1
        labels.append(date(target_year, target_month, 1).strftime("%b %Y"))
        projected_value = 0.0
        for item in investments:
            projected_value += _project_position_value(
                current_value=item.current_value,
                monthly_sip=item.monthly_sip,
                annual_return_rate=item.annual_return_rate,
                months=month_index,
            )
        values.append(round(projected_value, 2))

    return {"labels": labels, "values": values}


def _portfolio_risk(investments: list[Investment]) -> str:
    if not investments:
        return "No data"

    total_value = sum(item.current_value for item in investments) or 1.0
    high_risk_weight = sum(
        item.current_value
        for item in investments
        if item.asset_type in {"equity", "crypto", "reit"} or item.risk_level.lower() == "high"
    )
    ratio = high_risk_weight / total_value
    if ratio >= 0.65:
        return "High"
    if ratio >= 0.35:
        return "Moderate"
    return "Conservative"


def _project_position_value(*, current_value: float, monthly_sip: float, annual_return_rate: float, months: int) -> float:
    value = float(current_value or 0)
    monthly_rate = float(annual_return_rate or 0) / 1200
    for _ in range(months + 1):
        value = (value + float(monthly_sip or 0)) * (1 + monthly_rate)
    return value


def _investment_import_parser_status(parsed: dict) -> str:
    investments = parsed.get("investments") or []
    confidence = float(parsed.get("confidence") or 0)
    text = (parsed.get("extracted_text") or "").strip()
    if investments:
        return "parsed"
    if text or confidence >= 0.2:
        return "needs_review"
    return "failed"


def _investment_import_summary(parsed: dict, linked_investments: list[Investment]) -> str:
    broker = parsed.get("broker") or "investment"
    if linked_investments:
        return f"{len(linked_investments)} investment record(s) were created or updated from the {broker} document."
    if parsed.get("extracted_text"):
        return f"The {broker} portfolio document was saved, but Alfred could not extract enough structured holdings yet."
    return "The uploaded investment document was saved for review because Alfred could not recover enough readable portfolio data."


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def import_investment_pdf(request):
    upload = request.FILES.get("file")
    if not upload:
        return Response({"error": "Upload an investment PDF or statement first."}, status=status.HTTP_400_BAD_REQUEST)

    parsed = portfolio_intelligence_service.parse_portfolio_pdf(upload, request.user, filename=upload.name)
    linked_investments = list(parsed.get("investments") or [])

    with transaction.atomic():
        upload.seek(0)
        document = InvestmentImportDocument.objects.create(
            user=request.user,
            uploaded_file=upload,
            file_name=upload.name,
            broker_name=(parsed.get("broker") or "")[:120],
            parser_status=_investment_import_parser_status(parsed),
            parse_confidence=float(parsed.get("confidence") or 0),
            extracted_text=parsed.get("extracted_text") or "",
            extracted_payload=parsed.get("payload") or {},
            summary=_investment_import_summary(parsed, linked_investments),
        )
        if linked_investments:
            document.linked_investments.set(linked_investments)
        record_parser_learning(
            user=request.user,
            scope="investment_document",
            filename=upload.name,
            detected_type=(parsed.get("broker") or "portfolio_statement").lower().replace(" ", "_"),
            text=parsed.get("extracted_text") or "",
            field_names=sorted({key for item in (parsed.get("payload", {}).get("investments") or []) for key, value in item.items() if value not in ("", None, 0)}),
            parser_status=document.parser_status,
            confidence=document.parse_confidence,
        )
        if document.parser_status != "parsed":
            operational_logging_service.log(
                user=request.user,
                module="investments",
                category="document",
                scope="investment_document",
                event_type="investment_document_needs_review",
                severity="warning",
                document_id=document.id,
                file_name=document.file_name,
                message="Investment document upload was saved, but Alfred could not populate fully trusted structured holdings yet.",
                payload={
                    "parser_status": document.parser_status,
                    "parse_confidence": document.parse_confidence,
                    "broker_name": document.broker_name,
                    "linked_investments": len(linked_investments),
                },
            )

    raw_file_retention = purge_uploaded_file_after_extraction(
        document,
        "uploaded_file",
        reason="investment_document_extraction_complete",
    )
    return Response(
        {
            "success": True,
            "message": document.summary,
            "investments": InvestmentSerializer(linked_investments, many=True).data,
            "upload": InvestmentImportDocumentSerializer(document, context={"request": request}).data,
            "raw_file_retention": raw_file_retention,
        },
        status=status.HTTP_201_CREATED,
    )
