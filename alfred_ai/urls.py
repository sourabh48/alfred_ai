from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.views import LogoutView
from django.views.generic import RedirectView
from .native_views import private_media
from .diagnostics_views import diagnostics_view
from .data_sources_views import data_sources_view
from .statement_review_views import statement_review_view
from apps.loans.import_review_views import loan_import_review_view
from apps.investments.import_review_views import investment_import_review_view
from .views import statement_evidence_view
from .views import investment_evidence_view
from .views import loan_import_evidence_view
from .views import canonical_evidence_view
from .views import loan_closure_evidence_view
from .views import (
    index_view,
    dashboard_view, insights_view,
    expenses_view, budgets_view, loans_view,
    investments_view, family_view, career_view,
    behavioral_view, relationship_view, risk_view,
    reports_view, recommendations_view,
    tax_optimizer_view, mobility_view, map_tile_view, map_tile_status_view, bike_service_view,
    documents_view,
    document_center_item_delete_api_view,
    document_diagnostics_api_view,
    document_review_correction_api_view,
    document_review_queue_api_view,
    document_review_retry_api_view,
    client_operational_log_api_view,
    health_api_view,
    health_live_api_view,
    health_ready_api_view,
    session_ping_api_view,
    online_services_api_view, offline_maps_api_view, offline_tile_view,
    data_version_api_view,
    account_settings_view,
    project_details_career_outcome_view,
    project_details_view,
    project_details_api_view,
    signup_view,
    social_start_view,
    social_callback_view,
    AlfredLoginView,
)

from apps.career.views import career_tailored_cv_print

urlpatterns = [
    path("media/<path:path>", private_media, name="private_media"),
    path("admin/", admin.site.urls),
    path("health/", health_api_view, name="health"),
    path("health/live/", health_live_api_view, name="health_live"),
    path("health/ready/", health_ready_api_view, name="health_ready"),
    path("favicon.ico", RedirectView.as_view(url="/static/favicon.svg", permanent=True)),
    path("", index_view, name="index"),
    path("signup/", signup_view, name="signup"),
    path("login/", AlfredLoginView.as_view(), name="login"),
    path("auth/<str:provider>/start/", social_start_view, name="social_start"),
    path("auth/<str:provider>/callback/", social_callback_view, name="social_callback"),
    path("signin/", RedirectView.as_view(pattern_name="login", permanent=False), name="signin"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("accounts/login/", RedirectView.as_view(pattern_name="login", permanent=False)),

    path("dashboard/", dashboard_view, name="dashboard"),
    path("documents/", documents_view, name="documents"),
    path("data-sources/", data_sources_view, name="data_sources"),
    path("expenses/uploads/<int:pk>/review/", statement_review_view, name="statement_review"),
    path("loans/import-uploads/<int:pk>/review/", loan_import_review_view, name="loan_import_review"),
    path("investments/import-uploads/<int:pk>/review/", investment_import_review_view, name="investment_import_review"),
    path('documents/statements/<int:document_id>/transactions/<int:transaction_id>/', statement_evidence_view, name='statement_evidence'),
    path('documents/loan-closures/<int:document_id>/', loan_closure_evidence_view, name='loan_closure_evidence'),
    path('documents/investments/<int:document_id>/records/<int:identity>/', investment_evidence_view, name='investment_evidence'),
    path('documents/loans/<int:document_id>/records/<int:identity>/', loan_import_evidence_view, name='loan_import_evidence'),
    path('ai/financial-records/<str:kind>/<int:identity>/', canonical_evidence_view, name='canonical_evidence'),
    path("api/documents/review-queue/", document_review_queue_api_view, name="document_review_queue_api"),
    path("api/documents/review-queue/resolve/", document_review_correction_api_view, name="document_review_correction_api"),
    path("api/documents/review-queue/retry/", document_review_retry_api_view, name="document_review_retry_api"),
    path("api/documents/items/<str:scope>/<int:pk>/", document_center_item_delete_api_view, name="document_center_item_delete_api"),
    path("api/documents/diagnostics/", document_diagnostics_api_view, name="document_diagnostics_api"),
    path("api/session/ping/", session_ping_api_view, name="session_ping_api"),
    path("api/settings/online-services/", online_services_api_view, name="online_services_api"),
    path("api/settings/offline-maps/", offline_maps_api_view, name="offline_maps_api"),
    path("api/session/data-version/", data_version_api_view, name="data_version_api"),
    path("api/operational/logs/client/", client_operational_log_api_view, name="client_operational_log_api"),
    path("settings/", account_settings_view, name="account_settings"),
    path("settings/diagnostics/", diagnostics_view, name="diagnostics"),
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
    path("career/job-analyses/<int:pk>/tailored-cv/", career_tailored_cv_print, name="career_tailored_cv_print"),
    path("behavioral/", behavioral_view, name="behavioral"),
    path("relationship/", relationship_view, name="relationship"),
    path("risk/", risk_view, name="risk"),
    path("reports/", reports_view, name="reports"),
    path("bike-service/", bike_service_view, name="bike_service"),
    path("mobility/", mobility_view, name="mobility"),
    path("mobility/map-tiles/<int:z>/<int:x>/<int:y>.png", map_tile_view, name="map_tile"),
    path("mobility/map-tiles/status/", map_tile_status_view, name="map_tile_status"),
    path("mobility/offline-tiles/<int:z>/<int:x>/<int:y>.mvt", offline_tile_view, name="offline_tile"),
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

if getattr(settings, "ALFRED_NATIVE_RUNTIME", False):
    from .native_views import native_health
    urlpatterns += [
        path("health/native/", native_health, name="native_health"),
    ]

handler404 = "alfred_ai.views.not_found_view"
handler500 = "alfred_ai.views.server_error_view"
