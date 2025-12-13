from django.contrib import admin
from django.urls import path, include
from .views import (
    dashboard_view, insights_view,
    expenses_view, budgets_view, loans_view,
    investments_view, family_view, career_view,
    behavioral_view, relationship_view, risk_view,
    reports_view
)

urlpatterns = [
    path("admin/", admin.site.urls),

    path("dashboard/", dashboard_view, name="dashboard"),
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
    path("api/ai/", include("apps.ml_engine.api.urls")),
]
