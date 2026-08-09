from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.views import LoginView, LogoutView
from django.views.generic import RedirectView
from .views import (
    dashboard_view, insights_view,
    expenses_view, budgets_view, loans_view,
    investments_view, family_view, career_view,
    behavioral_view, relationship_view, risk_view,
    reports_view, credit_score_view, recommendations_view,
    tax_optimizer_view, mobility_view, bike_service_view,
    documents_view,
    document_center_item_delete_api_view,
    document_diagnostics_api_view,
    document_review_correction_api_view,
    document_review_queue_api_view,
    document_review_retry_api_view,
    client_operational_log_api_view,
    health_api_view,
    project_details_career_outcome_view,
    project_details_view,
    project_details_api_view,
    signup_view,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health_api_view, name="health"),
    path("favicon.ico", RedirectView.as_view(url="/static/favicon.svg", permanent=True)),
    path("", RedirectView.as_view(pattern_name="dashboard", permanent=False)),
    path("signup/", signup_view, name="signup"),
    path(
        "login/",
        LoginView.as_view(
            extra_context={
                "hide_sidebar": True,
                "hide_nav_auth_actions": True,
            }
        ),
        name="login",
    ),
    path("signin/", RedirectView.as_view(pattern_name="login", permanent=False), name="signin"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("accounts/login/", RedirectView.as_view(pattern_name="login", permanent=False)),

    path("dashboard/", dashboard_view, name="dashboard"),
    path("documents/", documents_view, name="documents"),
    path("api/documents/review-queue/", document_review_queue_api_view, name="document_review_queue_api"),
    path("api/documents/review-queue/resolve/", document_review_correction_api_view, name="document_review_correction_api"),
    path("api/documents/review-queue/retry/", document_review_retry_api_view, name="document_review_retry_api"),
    path("api/documents/items/<str:scope>/<int:pk>/", document_center_item_delete_api_view, name="document_center_item_delete_api"),
    path("api/documents/diagnostics/", document_diagnostics_api_view, name="document_diagnostics_api"),
    path("api/operational/logs/client/", client_operational_log_api_view, name="client_operational_log_api"),
    path("project-details/", project_details_view, name="project_details"),
    path("project-details/career-outcomes/", project_details_career_outcome_view, name="project_details_career_outcome"),
    path("api/project-details/", project_details_api_view, name="project_details_api"),
    path("ai/insights/", insights_view, name="ai_insights"),

    # Frontend UI pages
    path("expenses/", expenses_view, name="expenses"),
    path("budgets/", budgets_view, name="budgets"),
    path("loans/", loans_view, name="loans"),
    path("investments/", investments_view, name="investments"),
    path("family/", family_view, name="family"),
    path("career/", career_view, name="career"),
    path("behavioral/", behavioral_view, name="behavioral"),
    path("relationship/", relationship_view, name="relationship"),
    path("risk/", risk_view, name="risk"),
    path("reports/", reports_view, name="reports"),
    path("bike-service/", bike_service_view, name="bike_service"),
    path("mobility/", mobility_view, name="mobility"),
    path("credit-score/", credit_score_view, name="credit_score"),
    path("recommendations/", recommendations_view, name="recommendations"),
    path("tax-optimizer/", tax_optimizer_view, name="tax_optimizer"),

    # Backend APIs
    path("api/users/", include("apps.users.urls")),
    path("api/expenses/", include("apps.expenses.urls")),
    path("api/budgets/", include("apps.budgets.urls")),
    path("api/loans/", include("apps.loans.urls")),
    path("api/investments/", include("apps.investments.urls")),
    path("api/family/", include("apps.family.urls")),
    path("api/career/", include("apps.career.urls")),
    path("api/behavioral/", include("apps.behavioral.urls")),
    path("api/relationship/", include("apps.relationship.urls")),
    path("api/risk/", include("apps.risk.urls")),
    path("api/reports/", include("apps.reports.urls")),
    path("api/mobility/", include("apps.mobility.urls")),
    path("api/ai/", include("apps.ml_engine.api.urls")),
    path("api/integrations/", include("apps.integrations.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = "alfred_ai.views.not_found_view"
handler500 = "alfred_ai.views.server_error_view"
