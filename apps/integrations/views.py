"""
API Views for Integration module
"""
from datetime import timedelta
import os

from django.db import transaction
from django.db.models import Count, Max, Sum
from django.utils.text import slugify
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from alfred_ai.services import record_parser_learning
from alfred_ai.services.materialized_cache import materialize_payload
from alfred_ai.services.upload_privacy import purge_uploaded_file_after_extraction
from apps.expenses.models import Expense
from apps.expenses.services.financial_intelligence import resolve_canonical_financial_baseline
from apps.family.models import Dependent
from apps.investments.models import Investment
from apps.reports.services import operational_logging_service
from .models import CreditReportUpload, CreditScore, CreditScoreFactor, VerifiedExternalInsight
from .services import verified_intelligence
from .services.verified_intelligence import freshness_snapshot, proof_contract_payload
from .services.credit_loan_sync import sync_credit_report_loans
from .services.credit_report_parser import credit_report_parser
from .services.credit_score_tracker import credit_score_service
from apps.loans.models import Loan
from apps.ml_engine.services.recommendation_engine import recommendation_engine
from apps.ml_engine.services.tax_optimizer import tax_optimizer


def _query_float(request, key, default):
    value = request.query_params.get(key)
    if value in (None, ""):
        return float(default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _request_params_token(request, keys) -> str:
    return ":".join(f"{key}={request.query_params.get(key, '')}" for key in keys)


def _integration_dashboard_revision(user) -> str:
    expense_meta = Expense.objects.filter(user=user).aggregate(
        count=Count("id"),
        max_id=Max("id"),
        latest_date=Max("transaction_date"),
        total_amount=Sum("amount"),
    )
    loan_meta = Loan.objects.filter(user=user).aggregate(
        count=Count("id"),
        max_id=Max("id"),
        latest_update=Max("updated_at"),
        total_balance=Sum("remaining_balance"),
    )
    investment_meta = Investment.objects.filter(user=user).aggregate(
        count=Count("id"),
        max_id=Max("id"),
        latest_update=Max("updated_at"),
        total_value=Sum("current_value"),
    )
    dependent_meta = Dependent.objects.filter(user=user).aggregate(count=Count("id"), max_id=Max("id"))
    score_meta = CreditScore.objects.filter(user=user).aggregate(
        count=Count("id"),
        max_id=Max("id"),
        latest_score=Max("fetched_at"),
    )
    upload_meta = CreditReportUpload.objects.filter(user=user).aggregate(
        count=Count("id"),
        max_id=Max("id"),
        latest_update=Max("updated_at"),
    )
    evidence_meta = VerifiedExternalInsight.objects.filter(is_active=True).aggregate(
        count=Count("id"),
        max_id=Max("id"),
        latest_verified=Max("verified_at"),
    )
    profile_token = ":".join(
        str(value or "")
        for value in (
            getattr(user, "age", ""),
            getattr(user, "city", ""),
            getattr(user, "city_type", ""),
            getattr(user, "monthly_income", ""),
            getattr(user, "rent_or_emi", ""),
        )
    )
    return "|".join(
        str(value or "")
        for value in (
            "integrations-dashboard-v2",
            expense_meta["count"],
            expense_meta["max_id"],
            expense_meta["latest_date"],
            expense_meta["total_amount"],
            loan_meta["count"],
            loan_meta["max_id"],
            loan_meta["latest_update"],
            loan_meta["total_balance"],
            investment_meta["count"],
            investment_meta["max_id"],
            investment_meta["latest_update"],
            investment_meta["total_value"],
            dependent_meta["count"],
            dependent_meta["max_id"],
            score_meta["count"],
            score_meta["max_id"],
            score_meta["latest_score"],
            upload_meta["count"],
            upload_meta["max_id"],
            upload_meta["latest_update"],
            evidence_meta["count"],
            evidence_meta["max_id"],
            evidence_meta["latest_verified"],
            profile_token,
        )
    )


def _metro_city(city: str) -> bool:
    return slugify(city or "") in {"mumbai", "delhi", "new-delhi", "bangalore", "bengaluru", "chennai", "hyderabad", "kolkata"}


def _get_source_upload(score):
    try:
        return score.source_upload
    except Exception:
        return None


def _dedupe_evidence(items):
    seen = set()
    result = []
    for item in items or []:
        if not item:
            continue
        key = (
            item.get("source_url", ""),
            item.get("verified_at", ""),
            item.get("title", "") or item.get("source_name", ""),
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _proof_contract_payload(*, evidence_items, freshness, required_sources=None):
    return proof_contract_payload(
        evidence_items=evidence_items,
        freshness=freshness,
        required_sources=required_sources,
    )


def _grounding_payload(*, history, evidence=None, notes=None, required_sources=None):
    evidence_items = _dedupe_evidence(evidence or [])
    freshness = freshness_snapshot(evidence_items)
    return {
        "history": history,
        "evidence": evidence_items,
        "freshness": freshness,
        "proof_contract": _proof_contract_payload(
            evidence_items=evidence_items,
            freshness=freshness,
            required_sources=required_sources,
        ),
        "notes": notes or [],
    }


def _serialize_credit_score(score):
    source_upload = _get_source_upload(score)
    return {
        'success': True,
        'cached': score.is_valid,
        'stale': not score.is_valid,
        'score': score.score,
        'score_kind': score.score_kind,
        'bureau': score.bureau,
        'rating': score.rating,
        'fetched_at': score.fetched_at,
        'valid_until': score.valid_until,
        'days_until_refresh': score.days_until_refresh,
        'source_kind': 'uploaded_report' if source_upload else 'official_pull',
        'source_file_name': source_upload.file_name if source_upload else '',
        'parse_confidence': source_upload.parse_confidence if source_upload else 0,
        'parser_status': source_upload.parser_status if source_upload else '',
        'report_summary': {
            'total_accounts': score.total_accounts,
            'active_accounts': score.active_accounts,
            'closed_accounts': score.closed_accounts,
            'delinquent_accounts': score.delinquent_accounts,
            'total_credit_limit': score.total_credit_limit,
            'credit_utilization': score.credit_utilization,
        },
        'factors': [
            {
                'name': factor.factor_name,
                'weight': factor.weight,
                'score': factor.score,
                'status': factor.status,
            }
            for factor in score.factors.all()
        ],
    }


def _serialize_credit_report_upload(upload):
    extracted_payload = upload.extracted_payload or {}
    return {
        "id": upload.id,
        "file_name": upload.file_name,
        "bureau": upload.bureau,
        "parser_status": upload.parser_status,
        "parse_confidence": upload.parse_confidence,
        "summary": upload.summary,
        "parser_notes": upload.parser_notes,
        "applicant_name": upload.applicant_name,
        "report_number": upload.report_number,
        "report_date": upload.report_date,
        "uploaded_at": upload.created_at,
        "score": upload.parsed_credit_score.score if upload.parsed_credit_score else 0,
        "loan_accounts": extracted_payload.get("loan_accounts", []),
        "loan_account_overview": extracted_payload.get("loan_account_overview", {}),
        "loan_sync": extracted_payload.get("loan_sync", {}),
    }


def _persist_uploaded_credit_score(user, upload_record, parsed, bureau):
    bureau_name = bureau or parsed.bureau
    if bureau_name not in dict(CreditScore.BUREAU_CHOICES) or not parsed.payload.get("score"):
        return None

    CreditScore.objects.filter(
        user=user,
        bureau=bureau_name,
        score_kind="official",
        is_active=True,
    ).update(is_active=False)

    score = CreditScore.objects.create(
        user=user,
        bureau=bureau_name,
        score_kind="official",
        score=parsed.payload.get("score") or 0,
        score_range_min=credit_score_service.BUREAUS[bureau_name]["score_range"][0],
        score_range_max=credit_score_service.BUREAUS[bureau_name]["score_range"][1],
        rating=credit_score_service._get_rating(parsed.payload.get("score") or 0, bureau_name),
        total_accounts=parsed.payload.get("total_accounts") or 0,
        active_accounts=parsed.payload.get("active_accounts") or 0,
        closed_accounts=parsed.payload.get("closed_accounts") or 0,
        delinquent_accounts=parsed.payload.get("delinquent_accounts") or 0,
        total_credit_limit=parsed.payload.get("total_credit_limit") or 0,
        credit_utilization=parsed.payload.get("credit_utilization") or 0,
        valid_until=timezone.now() + timedelta(days=90),
        is_active=True,
    )
    for factor in parsed.factors:
        CreditScoreFactor.objects.create(
            credit_score=score,
            factor_name=factor.get("name", ""),
            weight=int(factor.get("weight", 0) or 0),
            score=float(factor.get("score", 0) or 0),
            status=factor.get("status", "Unknown"),
        )

    upload_record.parsed_credit_score = score
    upload_record.bureau = bureau_name
    upload_record.save(update_fields=["parsed_credit_score", "bureau", "updated_at"])
    return score


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_credit_score(request):
    """Get latest uploaded official score or fall back to Alfred estimate."""
    bureau = request.GET.get('bureau', 'CIBIL')
    latest_score = CreditScore.objects.filter(
        user=request.user,
        bureau=bureau,
        score_kind="official",
        is_active=True
    ).first()

    if latest_score:
        return Response(_serialize_credit_score(latest_score))

    result = credit_score_service.fetch_credit_score(request.user, bureau)

    if result.get('success'):
        if result.get("score_kind") != "official":
            return Response(result)

        # Save to database
        valid_until = timezone.now() + timedelta(days=30)

        credit_score = CreditScore.objects.create(
            user=request.user,
            bureau=bureau,
            score_kind=result.get("score_kind", "official"),
            score=result['score'],
            score_range_min=result['score_range'][0],
            score_range_max=result['score_range'][1],
            rating=result['rating'],
            total_accounts=result['report_summary']['total_accounts'],
            active_accounts=result['report_summary']['active_accounts'],
            closed_accounts=result['report_summary']['closed_accounts'],
            delinquent_accounts=result['report_summary']['delinquent_accounts'],
            total_credit_limit=result['report_summary']['total_credit_limit'],
            credit_utilization=result['report_summary']['credit_utilization'],
            valid_until=valid_until
        )

        # Save factors
        for factor in result['factors']:
            CreditScoreFactor.objects.create(
                credit_score=credit_score,
                factor_name=factor.get('name', ''),
                weight=factor.get('weight', 0),
                score=factor.get('score', 0),
                status=factor.get('status', 'Unknown')
            )

        return Response({
            'success': True,
            'cached': False,
            'score': credit_score.score,
            'score_kind': credit_score.score_kind,
            'bureau': credit_score.bureau,
            'rating': credit_score.rating,
            'fetched_at': credit_score.fetched_at,
            'valid_until': credit_score.valid_until,
            'days_until_refresh': 30,
            'report_summary': {
                'total_accounts': credit_score.total_accounts,
                'active_accounts': credit_score.active_accounts,
                'closed_accounts': credit_score.closed_accounts,
                'delinquent_accounts': credit_score.delinquent_accounts,
                'total_credit_limit': credit_score.total_credit_limit,
                'credit_utilization': credit_score.credit_utilization,
            },
            'factors': [
                {
                    'name': f.factor_name,
                    'weight': f.weight,
                    'score': f.score,
                    'status': f.status
                }
                for f in credit_score.factors.all()
            ]
        })

    return Response(result, status=400)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_all_bureau_scores(request):
    """Get scores from all bureaus."""
    result = credit_score_service.get_all_bureau_scores(request.user)
    return Response(result)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def analyze_credit_factors(request):
    """Get detailed factor analysis."""
    result = credit_score_service.analyze_score_factors(request.user)
    return Response(result)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_credit_score_trend(request):
    """Get 12-month credit score trend."""
    months = int(request.GET.get('months', 12))
    result = credit_score_service.get_score_trend(request.user, months)
    return Response(result)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_improvement_plan(request):
    """Get personalized credit score improvement plan."""
    result = credit_score_service.get_improvement_plan(request.user)
    return Response(result)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def compare_with_peers(request):
    """Compare credit score with peers."""
    result = credit_score_service.compare_with_peers(request.user)
    return Response(result)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def comprehensive_credit_report(request):
    """Get complete credit report with all analyses."""
    result = credit_score_service.get_comprehensive_report(request.user)
    return Response(result)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def refresh_credit_score(request):
    """Manually refresh credit score (if allowed)."""
    bureau = request.data.get('bureau', 'CIBIL')

    # Check if refresh is allowed
    latest_score = CreditScore.objects.filter(
        user=request.user,
        bureau=bureau,
        score_kind="official",
        is_active=True
    ).first()

    if latest_score and _get_source_upload(latest_score):
        return Response({
            'success': False,
            'error': 'Current official score came from an uploaded bureau report. Upload a newer report to replace it.',
        }, status=400)

    if latest_score and latest_score.is_valid:
        return Response({
            'success': False,
            'error': f'Score can be refreshed in {latest_score.days_until_refresh} days',
            'days_remaining': latest_score.days_until_refresh
        }, status=400)

    # Fetch new score
    result = credit_score_service.fetch_credit_score(request.user, bureau)

    if result.get('success'):
        if result.get("score_kind") != "official":
            return Response(result)

        # Deactivate old scores
        CreditScore.objects.filter(
            user=request.user,
            bureau=bureau
        ).update(is_active=False)

        # Create new score
        valid_until = timezone.now() + timedelta(days=30)

        credit_score = CreditScore.objects.create(
            user=request.user,
            bureau=bureau,
            score_kind=result.get("score_kind", "official"),
            score=result['score'],
            score_range_min=result['score_range'][0],
            score_range_max=result['score_range'][1],
            rating=result['rating'],
            total_accounts=result['report_summary']['total_accounts'],
            active_accounts=result['report_summary']['active_accounts'],
            closed_accounts=result['report_summary']['closed_accounts'],
            delinquent_accounts=result['report_summary']['delinquent_accounts'],
            total_credit_limit=result['report_summary']['total_credit_limit'],
            credit_utilization=result['report_summary']['credit_utilization'],
            valid_until=valid_until
        )

        return Response({
            'success': True,
            'message': 'Credit score refreshed successfully',
            'score': credit_score.score,
            'rating': credit_score.rating
        })

    return Response(result, status=400)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_credit_report_uploads(request):
    uploads = CreditReportUpload.objects.filter(user=request.user).select_related("parsed_credit_score")[:8]
    return Response([_serialize_credit_report_upload(upload) for upload in uploads])


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_credit_report(request):
    upload = request.FILES.get("report")
    if not upload:
        return Response({"success": False, "error": "Upload a credit report PDF or image first."}, status=400)

    bureau_override = str(request.data.get("bureau", "") or "").upper().strip()
    if bureau_override and bureau_override not in dict(CreditScore.BUREAU_CHOICES):
        return Response({"success": False, "error": "Unsupported bureau selection."}, status=400)

    parsed = credit_report_parser.parse(upload, filename=upload.name, user=request.user)
    effective_bureau = bureau_override or parsed.bureau or ""
    parser_status = parsed.parser_status
    if parser_status == "failed" and os.path.splitext(upload.name.lower())[1] in {".pdf", ".png", ".jpg", ".jpeg", ".webp"}:
        parser_status = "needs_review"

    with transaction.atomic():
        report_upload = CreditReportUpload.objects.create(
            user=request.user,
            uploaded_file=upload,
            file_name=upload.name,
            bureau=effective_bureau,
            parser_status=parser_status,
            parse_confidence=parsed.confidence,
            extracted_text=parsed.extracted_text,
            extracted_payload={**parsed.payload, "bureau": effective_bureau or parsed.payload.get("bureau", "")},
            summary=parsed.summary,
            parser_notes=parsed.parser_notes,
            applicant_name=parsed.payload.get("applicant_name", ""),
            report_number=parsed.payload.get("report_number", ""),
            report_date=parsed.payload.get("report_date") or None,
        )
        credit_score = _persist_uploaded_credit_score(request.user, report_upload, parsed, effective_bureau)
        loan_sync = sync_credit_report_loans(user=request.user, report_upload=report_upload)
        report_upload.extracted_payload = {
            **(report_upload.extracted_payload or {}),
            "loan_sync": loan_sync,
        }
        if loan_sync.get("processed_accounts"):
            report_upload.summary = (
                f"{report_upload.summary} {loan_sync.get('summary', '').strip()}".strip()
            )[:1000]
        report_upload.save(update_fields=["extracted_payload", "summary", "updated_at"])
        record_parser_learning(
            user=request.user,
            scope="credit_report",
            filename=upload.name,
            detected_type=effective_bureau or parsed.bureau or "credit_report",
            text=parsed.extracted_text,
            field_names=[key for key, value in parsed.payload.items() if value not in ("", None, 0)],
            parser_status=parser_status,
            confidence=parsed.confidence,
        )
        if not credit_score or report_upload.parser_status != "parsed":
            operational_logging_service.log(
                user=request.user,
                module="integrations",
                category="document",
                scope="credit_report",
                event_type="credit_report_needs_review",
                severity="warning",
                document_id=report_upload.id,
                file_name=report_upload.file_name,
                message="Credit report upload was saved, but Alfred could not populate a fully trusted score snapshot yet.",
                payload={
                    "parser_status": report_upload.parser_status,
                    "parse_confidence": report_upload.parse_confidence,
                    "bureau": report_upload.bureau,
                    "parser_notes": report_upload.parser_notes,
                },
            )

    raw_file_retention = purge_uploaded_file_after_extraction(
        report_upload,
        "uploaded_file",
        reason="credit_report_extraction_complete",
    )
    return Response(
        {
            "success": True,
            "message": "Credit report uploaded and parsed." if credit_score else "Credit report uploaded. Review the extracted result before relying on it.",
            "upload": _serialize_credit_report_upload(report_upload),
            "score": _serialize_credit_score(credit_score) if credit_score else None,
            "loan_sync": (report_upload.extracted_payload or {}).get("loan_sync", {}),
            "raw_file_retention": raw_file_retention,
        },
        status=201,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def recommendation_overview(request):
    """Expose product recommendation engines to the frontend dashboard."""
    revision = "|".join(
        (
            _integration_dashboard_revision(request.user),
            _request_params_token(request, ["investment_amount", "time_horizon"]),
        )
    )
    payload = materialize_payload(
        namespace="recommendation-overview",
        user_id=request.user.id,
        revision=revision,
        ttl_seconds=120,
        builder=lambda: _build_recommendation_overview_payload(request),
    )
    return Response(payload)


def _build_recommendation_overview_payload(request) -> dict:
    """Build product recommendation engines for the frontend dashboard."""
    investment_amount = _query_float(request, "investment_amount", 0)
    time_horizon = request.query_params.get("time_horizon", "long_term")
    market = verified_intelligence.market_snapshot()
    inflation = verified_intelligence.world_bank_indicator("FP.CPI.TOTL.ZG", "India inflation rate")
    profile = recommendation_engine.build_user_profile(request.user)
    financial_baseline = profile.get("financial_baseline", {})
    investments = recommendation_engine.recommend_investments(
        request.user,
        investment_amount=investment_amount or None,
        time_horizon=time_horizon,
    )
    insurance = recommendation_engine.recommend_insurance(request.user)

    investments_grounding = _grounding_payload(
        history={
            "monthly_income": round(profile.get("income", 0), 2),
            "monthly_expenses": round(profile.get("monthly_expenses", 0), 2),
            "monthly_savings": round(profile.get("monthly_savings", 0), 2),
            "savings_rate": round(profile.get("savings_rate", 0), 2),
            "risk_appetite": profile.get("risk_appetite", ""),
            "available_amount": round(investments.get("your_profile", {}).get("available_amount", 0), 2),
            "time_horizon": investments.get("your_profile", {}).get("time_horizon", time_horizon),
            "recommendation_count": len(investments.get("recommendations", [])),
        },
        evidence=[market.evidence, inflation.evidence],
        required_sources=["Yahoo Finance", "World Bank"],
        notes=[
            "Investment matching is grounded in your savings capacity, persona, and risk appetite, then contextualized with verified market and inflation evidence.",
            "External evidence shapes market posture and real-return context, not a guarantee that any product will outperform.",
        ],
    )
    insurance_grounding = _grounding_payload(
        history={
            "monthly_income": round(profile.get("income", 0), 2),
            "dependents": int(profile.get("dependents", 0) or 0),
            "age": int(profile.get("age", 0) or 0),
            "essential_recommendations": sum(1 for item in insurance.get("recommendations", []) if item.get("is_essential")),
            "total_annual_premium": round(insurance.get("total_annual_premium", 0), 2),
        },
        evidence=[inflation.evidence],
        required_sources=["World Bank"],
        notes=[
            "Insurance matching is grounded in household dependence, age, and affordability. Verified inflation evidence is attached only as protection-cost context.",
            "Coverage suggestions remain planning guidance, not insurer underwriting approval or premium quotes.",
        ],
    )
    credit_cards_grounding = _grounding_payload(
        history={
            "monthly_income": round(profile.get("income", 0), 2),
            "monthly_expenses": round(profile.get("monthly_expenses", 0), 2),
            "savings_rate": round(profile.get("savings_rate", 0), 2),
            "dti_ratio": round(profile.get("dti_ratio", 0), 2),
            "policy_state": "disabled",
        },
        evidence=[inflation.evidence],
        required_sources=["World Bank"],
        notes=[
            "Credit-card recommendations are intentionally disabled for this workspace, so no card ranking or acquisition advice is produced.",
            "The evidence contract is retained to distinguish a policy suppression from missing user data.",
        ],
    )
    personal_loans_grounding = _grounding_payload(
        history={
            "monthly_income": round(profile.get("income", 0), 2),
            "recurring_emi_burden": round(financial_baseline.get("recurring_emi_burden", 0), 2),
            "debt_burden_ratio": round(profile.get("dti_ratio", 0), 2),
            "liquid_runway_months": round(financial_baseline.get("liquid_runway_months", 0), 2),
            "policy_state": "disabled",
        },
        evidence=[market.evidence, inflation.evidence],
        required_sources=["Yahoo Finance", "World Bank"],
        notes=[
            "Personal-loan recommendations are intentionally disabled for this workspace, so no borrowing shortlist is produced.",
            "Market and inflation evidence is attached only to document the suppressed decision context.",
        ],
    )
    investments = {**investments, "grounding": investments_grounding}
    insurance = {**insurance, "grounding": insurance_grounding}
    combined_evidence = _dedupe_evidence(
        [
            *investments_grounding["evidence"],
            *insurance_grounding["evidence"],
            *credit_cards_grounding["evidence"],
            *personal_loans_grounding["evidence"],
        ]
    )
    combined_freshness = freshness_snapshot(combined_evidence)

    return {
        "profile": profile,
        "financial_baseline": financial_baseline,
        "credit_cards": {
            "enabled": False,
            "recommendations": [],
            "message": "Credit card suggestions are disabled for this workspace.",
            "grounding": credit_cards_grounding,
        },
        "loans": {
            "enabled": False,
            "recommendations": [],
            "message": "Personal loan suggestions are disabled for this workspace.",
            "grounding": personal_loans_grounding,
        },
        "investments": investments,
        "insurance": insurance,
        "disabled_modules": [
            {"key": "credit_cards", "label": "Credit cards", "reason": "Suppressed by product preference for this workspace."},
            {"key": "personal_loans", "label": "Personal loans", "reason": "Suppressed by product preference for this workspace."},
        ],
        "grounding": {
            "history": {
                "monthly_income": profile.get("income", 0),
                "monthly_expenses": round(profile.get("monthly_expenses", 0), 2),
                "savings_rate": round(profile.get("savings_rate", 0), 2),
                "dti_ratio": round(profile.get("dti_ratio", 0), 2),
                "tracked_personas": profile.get("persona", []),
            },
            "evidence": combined_evidence,
            "freshness": combined_freshness,
            "proof_contract": _proof_contract_payload(
                evidence_items=combined_evidence,
                freshness=combined_freshness,
                required_sources=["Yahoo Finance", "World Bank"],
            ),
            "modules": [
                {
                    "key": "investments",
                    "label": "Investment stack",
                    "freshness": investments_grounding["freshness"],
                    "evidence_count": len(investments_grounding["evidence"]),
                },
                {
                    "key": "insurance",
                    "label": "Insurance coverage",
                    "freshness": insurance_grounding["freshness"],
                    "evidence_count": len(insurance_grounding["evidence"]),
                },
                {
                    "key": "credit_cards",
                    "label": "Credit cards",
                    "freshness": credit_cards_grounding["freshness"],
                    "evidence_count": len(credit_cards_grounding["evidence"]),
                    "status": "disabled",
                },
                {
                    "key": "personal_loans",
                    "label": "Personal loans",
                    "freshness": personal_loans_grounding["freshness"],
                    "evidence_count": len(personal_loans_grounding["evidence"]),
                    "status": "disabled",
                },
            ],
            "notes": [
                "Recommendations are grounded in current user history plus verified external market context where relevant.",
                "Product matching is still rule-driven and evidence-blended, not a claim of institution-approved suitability.",
            ],
        },
    }


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def tax_optimizer_overview(request):
    """Return a user-ready tax dashboard based on current profile defaults."""
    revision = "|".join(
        (
            _integration_dashboard_revision(request.user),
            _request_params_token(request, ["annual_income", "basic_salary", "hra_received", "rent_paid", "metro"]),
        )
    )
    payload = materialize_payload(
        namespace="tax-optimizer-overview",
        user_id=request.user.id,
        revision=revision,
        ttl_seconds=120,
        builder=lambda: _build_tax_optimizer_overview_payload(request),
    )
    return Response(payload)


def _build_tax_optimizer_overview_payload(request) -> dict:
    """Build a user-ready tax dashboard based on current profile defaults."""
    financial_baseline = resolve_canonical_financial_baseline(request.user)
    annual_income = _query_float(
        request,
        "annual_income",
        financial_baseline.get("annual_income", 0) or 0,
    )
    deductions = tax_optimizer._calculate_current_deductions(request.user)
    basic_salary = _query_float(request, "basic_salary", annual_income / 24 if annual_income else 0)
    hra_received = _query_float(request, "hra_received", basic_salary * 0.4)
    rent_paid = _query_float(request, "rent_paid", financial_baseline.get("rent_burden", 0) or basic_salary * 0.45)
    metro_city = request.query_params.get("metro")
    if metro_city is None:
        metro_city = _metro_city(getattr(request.user, "city", ""))
    else:
        metro_city = str(metro_city).lower() in {"1", "true", "yes", "on"}

    home_loan = Loan.objects.filter(user=request.user, loan_type="home", is_active=True).order_by("-id").first()
    home_loan_benefits = None
    if home_loan:
        annual_emi = (home_loan.emi or 0) * 12
        estimated_interest = min(
            annual_emi,
            ((home_loan.remaining_balance or home_loan.principal or 0) * (home_loan.interest_rate or 0) / 100),
        )
        principal_paid = max(annual_emi - estimated_interest, 0)
        home_loan_benefits = tax_optimizer.calculate_home_loan_benefits(
            loan_principal_paid=principal_paid,
            loan_interest_paid=estimated_interest,
            is_first_home=True,
        )
    tax_regime = verified_intelligence.tax_regime_reference()
    nps_reference = verified_intelligence.nps_tax_reference()
    ppf_reference = verified_intelligence.ppf_reference()
    evidence_items = [tax_regime.evidence, nps_reference.evidence, ppf_reference.evidence]
    evidence_freshness = freshness_snapshot(evidence_items)

    return {
        "annual_income": annual_income,
        "financial_baseline": financial_baseline,
        "inputs": {
            "annual_income": annual_income,
            "basic_salary": basic_salary,
            "hra_received": hra_received,
            "rent_paid": rent_paid,
            "metro": metro_city,
        },
        "deductions": deductions,
        "regime_comparison": tax_optimizer.compare_regimes(annual_income, deductions),
        "tax_savings": tax_optimizer.suggest_tax_saving_investments(request.user),
        "hra": tax_optimizer.calculate_hra_exemption(
            basic_salary=basic_salary,
            hra_received=hra_received,
            rent_paid=rent_paid,
            metro_city=metro_city,
        ),
        "home_loan": home_loan_benefits,
        "deduction_catalog": [
            {
                "section": section,
                "name": value["name"],
                "max_limit": value["max_limit"],
                "instruments": value["instruments"],
            }
            for section, value in tax_optimizer.DEDUCTIONS.items()
        ],
        "tax_evidence": {
            "evidence": evidence_items,
            "freshness": evidence_freshness,
            "proof_contract": proof_contract_payload(
                evidence_items=evidence_items,
                freshness=evidence_freshness,
                required_sources=["Income Tax Department", "India Post", "NPS Trust"],
                advisory_surface="tax_optimizer",
            ),
            "notes": [
                "Tax guidance is grounded in stored user deductions plus official reference sources for regime and instrument treatment.",
                "This overview is still planning guidance, not a substitute for a chartered accountant or filed return review.",
            ],
        },
    }
