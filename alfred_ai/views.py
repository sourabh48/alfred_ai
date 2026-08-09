import json
import logging

from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import render
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from django.core.serializers.json import DjangoJSONEncoder
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from apps.career.forms import CareerOpportunityOutcomeForm
from apps.integrations.services import verified_intelligence
from apps.ml_engine.runtime_control import build_runtime_status
from apps.reports.services import operational_logging_service
from apps.users.forms import AlfredSignUpForm
from .services.document_review import apply_correction, build_review_queue, delete_document, retry_review_item
from .project_details import project_details_payload

LOGGER = logging.getLogger("alfred.health")


@require_http_methods(["GET"])
def health_api_view(request):
    checks = {"database": "ok", "cache": "ok", "ml_runtime": "ok", "ml_startup_gate": "ok"}
    status_code = 200

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        checks["database"] = "error"
        status_code = 503

    try:
        cache.set("alfred:healthcheck", "ok", timeout=30)
        if cache.get("alfred:healthcheck") != "ok":
            raise RuntimeError("cache probe mismatch")
    except Exception:
        checks["cache"] = "error"
        status_code = 503

    try:
        runtime_status = build_runtime_status()
        if not runtime_status["runtime"]["ready"]:
            checks["ml_runtime"] = "degraded"
        if runtime_status["auto_train_enabled"] and not runtime_status["approval"]["granted"]:
            checks["ml_startup_gate"] = "awaiting_approval"
        elif runtime_status["auto_train_enabled"] and not runtime_status["startup_ready"]:
            checks["ml_startup_gate"] = "degraded"
    except Exception:
        checks["ml_runtime"] = "error"
        checks["ml_startup_gate"] = "error"
        status_code = 503

    if status_code != 200:
        LOGGER.warning(
            "health_check status=degraded database=%s cache=%s ml_runtime=%s ml_startup_gate=%s",
            checks["database"],
            checks["cache"],
            checks["ml_runtime"],
            checks["ml_startup_gate"],
        )

    return JsonResponse(
        {
            "status": "ok" if status_code == 200 else "degraded",
            "checks": checks,
        },
        status=status_code,
        encoder=DjangoJSONEncoder,
    )


def signup_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    form = AlfredSignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect("dashboard")

    return render(
        request,
        "registration/signup.html",
        {
            "form": form,
            "hide_sidebar": True,
            "hide_nav_auth_actions": True,
        },
    )


def not_found_view(request, exception):
    return render(
        request,
        "404.html",
        {
            "hide_sidebar": True,
            "hide_nav_auth_actions": True,
            "requested_path": request.path,
            "exception": exception,
        },
        status=404,
    )


def server_error_view(request):
    return render(
        request,
        "500.html",
        {
            "hide_sidebar": True,
            "hide_nav_auth_actions": True,
        },
        status=500,
    )


@login_required
def dashboard_view(request):
    return render(request, "dashboard.html")


@login_required
def documents_view(request):
    return render(request, "documents.html")


@login_required
@require_http_methods(["GET"])
def document_review_queue_api_view(request):
    return JsonResponse({"results": build_review_queue(request.user)}, encoder=DjangoJSONEncoder)


@login_required
@require_http_methods(["POST"])
def document_review_correction_api_view(request):
    payload = json.loads(request.body or "{}")
    item = apply_correction(
        request.user,
        scope=str(payload.get("scope") or ""),
        document_id=int(payload.get("id") or 0),
        corrections=payload.get("corrections") or {},
    )
    return JsonResponse({"item": item}, encoder=DjangoJSONEncoder)


@login_required
@require_http_methods(["POST"])
def document_review_retry_api_view(request):
    payload = json.loads(request.body or "{}")
    item = retry_review_item(
        request.user,
        scope=str(payload.get("scope") or ""),
        document_id=int(payload.get("id") or 0),
    )
    return JsonResponse({"item": item}, encoder=DjangoJSONEncoder)


@login_required
@require_http_methods(["DELETE"])
def document_center_item_delete_api_view(request, scope, pk):
    delete_document(request.user, scope=scope, document_id=pk)
    return JsonResponse({"success": True}, encoder=DjangoJSONEncoder)


@login_required
@require_http_methods(["GET"])
def document_diagnostics_api_view(request):
    results = [
        operational_logging_service.serialize(entry)
        for entry in operational_logging_service.recent_for_user(request.user, limit=18)
    ]
    return JsonResponse({"results": results}, encoder=DjangoJSONEncoder)


@login_required
@require_http_methods(["POST"])
def client_operational_log_api_view(request):
    payload = json.loads(request.body or "{}")
    event = operational_logging_service.log(
        user=request.user,
        module=str(payload.get("module") or "frontend"),
        category=str(payload.get("category") or "visualization"),
        scope=str(payload.get("scope") or ""),
        event_type=str(payload.get("event_type") or "client_issue"),
        severity=str(payload.get("severity") or "warning"),
        document_id=payload.get("document_id"),
        file_name=str(payload.get("file_name") or ""),
        message=str(payload.get("message") or "Client issue logged."),
        payload=payload.get("payload") or {},
    )
    return JsonResponse({"result": operational_logging_service.serialize(event)}, encoder=DjangoJSONEncoder)


@login_required
def project_details_view(request):
    if not request.user.is_superuser:
        raise PermissionDenied("Project details are restricted to superusers.")
    return render(
        request,
        "project_details.html",
        _project_details_context(),
    )


@login_required
def project_details_api_view(request):
    if not request.user.is_superuser:
        raise PermissionDenied("Project details are restricted to superusers.")
    return JsonResponse(
        project_details_payload(verified_intelligence.guardrail_snapshot()),
        encoder=DjangoJSONEncoder,
    )


def _project_details_context(*, career_outcome_form=None) -> dict:
    context = project_details_payload(verified_intelligence.guardrail_snapshot())
    context["career_outcome_form"] = career_outcome_form or CareerOpportunityOutcomeForm()
    return context


@login_required
@require_http_methods(["POST"])
def project_details_career_outcome_view(request):
    if not request.user.is_superuser:
        raise PermissionDenied("Career outcome entry is restricted to superusers.")

    form = CareerOpportunityOutcomeForm(request.POST)
    if not form.is_valid():
        return render(
            request,
            "project_details.html",
            _project_details_context(career_outcome_form=form),
            status=400,
        )

    analysis = form.save()
    contract_status = form.contract_status or {}
    messages.success(
        request,
        (
            f"Career outcome saved for job analysis #{analysis.id}; "
            f"maturity contract {'valid' if contract_status.get('valid') else 'not valid'}."
        ),
    )
    return redirect(f"{reverse('project_details')}#careerOutcomeEntry")

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
