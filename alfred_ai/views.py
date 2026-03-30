from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from apps.integrations.services import verified_intelligence
from .project_details import project_details_payload

@login_required
def dashboard_view(request):
    return render(request, "dashboard.html")


@login_required
def documents_view(request):
    return render(request, "documents.html")


@login_required
def project_details_view(request):
    if not request.user.is_superuser:
        raise PermissionDenied("Project details are restricted to superusers.")
    return render(
        request,
        "project_details.html",
        project_details_payload(verified_intelligence.guardrail_snapshot()),
    )

@login_required
def credit_score_view(request):
    return render(request, "integrations/credit_score.html")

@login_required
def recommendations_view(request):
    return render(request, "integrations/recommendations.html")

@login_required
def tax_optimizer_view(request):
    return render(request, "integrations/tax_optimizer.html")

@login_required
def insights_view(request):
    return render(request, "ai_insights.html")


@login_required
def expenses_view(request):
    return render(request, "expenses/list.html")

@login_required
def budgets_view(request):
    return render(request, "budgets/list.html")

@login_required
def loans_view(request):
    return render(request, "loans/list.html")

@login_required
def investments_view(request):
    return render(request, "investments/list.html")

@login_required
def family_view(request):
    return render(request, "family/list.html")

@login_required
def career_view(request):
    return render(request, "career/list.html")

@login_required
def behavioral_view(request):
    return render(request, "behavioral/list.html")

@login_required
def relationship_view(request):
    return render(request, "relationship/list.html")

@login_required
def risk_view(request):
    return render(request, "risk/list.html")

@login_required
def reports_view(request):
    if not request.user.is_superuser:
        raise PermissionDenied("Reports are restricted to superusers.")
    return render(request, "reports/list.html")

@login_required
def mobility_view(request):
    return render(request, "mobility/dashboard.html")


@login_required
def bike_service_view(request):
    return render(request, "mobility/bike_service_dashboard.html")
