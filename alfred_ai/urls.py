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
    project_details_view,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("favicon.ico", RedirectView.as_view(url="/static/favicon.svg", permanent=True)),
    path("", RedirectView.as_view(pattern_name="dashboard", permanent=False)),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("accounts/login/", RedirectView.as_view(pattern_name="login", permanent=False)),

    path("dashboard/", dashboard_view, name="dashboard"),
    path("documents/", documents_view, name="documents"),
    path("project-details/", project_details_view, name="project_details"),
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
