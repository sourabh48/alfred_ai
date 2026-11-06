from django.urls import path
from .alert_views import InvestmentReviewAlertView
from .research_views import ResearchDecisionDetailView, ResearchDecisionListCreateView, ResearchDecisionSettleView, ResearchLessonsView, ResearchPacketView
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
    path("research/", ResearchDecisionListCreateView.as_view(), name="research_decisions"),
    path("research/lessons/", ResearchLessonsView.as_view(), name="research_lessons"),
    path("research/packet/", ResearchPacketView.as_view(), name="research_packet"),
    path("research/<int:pk>/", ResearchDecisionDetailView.as_view(), name="research_decision"),
    path("research/<int:pk>/settle/", ResearchDecisionSettleView.as_view(), name="research_decision_settle"),
    path("", InvestmentListCreateView.as_view()),
    path("summary/", InvestmentSummaryView.as_view()),
    path("import-uploads/", InvestmentImportDocumentListView.as_view()),
    path("import-pdf/", import_investment_pdf),
    path("allocation/", InvestmentAllocationView.as_view()),
    path("growth/", InvestmentGrowthView.as_view()),
    path("<int:pk>/", InvestmentDetailView.as_view()),
]
