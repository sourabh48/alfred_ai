"""
API Views for Integration module
"""
from django.utils.text import slugify
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta

from .models import CreditScore, CreditScoreFactor
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


def _metro_city(city: str) -> bool:
    return slugify(city or "") in {"mumbai", "delhi", "new-delhi", "bangalore", "bengaluru", "chennai", "hyderabad", "kolkata"}


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_credit_score(request):
    """Get latest credit score or fetch new one if expired."""
    bureau = request.GET.get('bureau', 'CIBIL')

    # Check for existing valid score
    latest_score = CreditScore.objects.filter(
        user=request.user,
        bureau=bureau,
        score_kind="official",
        is_active=True
    ).first()

    if latest_score and latest_score.is_valid:
        # Return cached score
        return Response({
            'success': True,
            'cached': True,
            'score': latest_score.score,
            'score_kind': latest_score.score_kind,
            'bureau': latest_score.bureau,
            'rating': latest_score.rating,
            'fetched_at': latest_score.fetched_at,
            'valid_until': latest_score.valid_until,
            'days_until_refresh': latest_score.days_until_refresh,
            'report_summary': {
                'total_accounts': latest_score.total_accounts,
                'active_accounts': latest_score.active_accounts,
                'closed_accounts': latest_score.closed_accounts,
                'delinquent_accounts': latest_score.delinquent_accounts,
                'total_credit_limit': latest_score.total_credit_limit,
                'credit_utilization': latest_score.credit_utilization,
            },
            'factors': [
                {
                    'name': f.factor_name,
                    'weight': f.weight,
                    'score': f.score,
                    'status': f.status
                }
                for f in latest_score.factors.all()
            ]
        })

    # Fetch new score
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


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def recommendation_overview(request):
    """Expose product recommendation engines to the frontend dashboard."""
    loan_amount = _query_float(request, "loan_amount", 0)
    investment_amount = _query_float(request, "investment_amount", 0)
    time_horizon = request.query_params.get("time_horizon", "long_term")

    return Response(
        {
            "profile": recommendation_engine.build_user_profile(request.user),
            "credit_cards": recommendation_engine.recommend_credit_cards(request.user),
            "loans": recommendation_engine.recommend_loans(
                request.user,
                loan_amount=loan_amount or None,
            ),
            "investments": recommendation_engine.recommend_investments(
                request.user,
                investment_amount=investment_amount or None,
                time_horizon=time_horizon,
            ),
            "insurance": recommendation_engine.recommend_insurance(request.user),
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def tax_optimizer_overview(request):
    """Return a user-ready tax dashboard based on current profile defaults."""
    annual_income = _query_float(
        request,
        "annual_income",
        (getattr(request.user, "monthly_income", 0) or 0) * 12,
    )
    deductions = tax_optimizer._calculate_current_deductions(request.user)
    basic_salary = _query_float(request, "basic_salary", annual_income / 24 if annual_income else 0)
    hra_received = _query_float(request, "hra_received", basic_salary * 0.4)
    rent_paid = _query_float(request, "rent_paid", getattr(request.user, "rent_or_emi", 0) or basic_salary * 0.45)
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

    return Response(
        {
            "annual_income": annual_income,
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
        }
    )
