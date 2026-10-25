from django.urls import path
from .alert_views import InvestmentReviewAlertView
from .views import (
    InvestmentAllocationView,
    InvestmentDetailView,
    InvestmentGrowthView,
    InvestmentImportDocumentListView,
    InvestmentListCreateView,
    InvestmentSummaryView,
    import_investment_pdf,
)

urlpatterns = [
    path("review-alerts/", InvestmentReviewAlertView.as_view()),
    path("", InvestmentListCreateView.as_view()),
    path("summary/", InvestmentSummaryView.as_view()),
    path("import-uploads/", InvestmentImportDocumentListView.as_view()),
    path("import-pdf/", import_investment_pdf),
    path("allocation/", InvestmentAllocationView.as_view()),
    path("growth/", InvestmentGrowthView.as_view()),
    path("<int:pk>/", InvestmentDetailView.as_view()),
]
