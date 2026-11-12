from django.urls import path
from .import_review_views import InvestmentImportReviewAPI, InvestmentImportConfirmAPI
from .alert_views import InvestmentReviewAlertView
from .look_through_views import FundLookThroughView, SavedFundPortfolioDetailView, SavedFundPortfolioView
from .research_views import ResearchDecisionDetailView, ResearchDecisionListCreateView, ResearchDecisionSettleView, ResearchHistoryView, ResearchLessonsView, ResearchChallengeView, ResearchPacketView, ResearchPersonalChallengeView
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
    path("look-through/analyze/", FundLookThroughView.as_view(), name="fund_look_through"),
    path("look-through/saved/", SavedFundPortfolioView.as_view(), name="fund_look_through_saved"),
    path("look-through/saved/<int:pk>/", SavedFundPortfolioDetailView.as_view(), name="fund_look_through_saved_detail"),
    path("research/", ResearchDecisionListCreateView.as_view(), name="research_decisions"),
    path("research/lessons/", ResearchLessonsView.as_view(), name="research_lessons"),
    path("research/history/", ResearchHistoryView.as_view(), name="research_history"),
    path("research/packet/", ResearchPacketView.as_view(), name="research_packet"),
    path("research/packet/challenge/", ResearchChallengeView.as_view(), name="research_packet_challenge"),
    path("research/packet/personal-challenge/", ResearchPersonalChallengeView.as_view(), name="research_packet_personal_challenge"),
    path("research/<int:pk>/", ResearchDecisionDetailView.as_view(), name="research_decision"),
    path("research/<int:pk>/settle/", ResearchDecisionSettleView.as_view(), name="research_decision_settle"),
    path("", InvestmentListCreateView.as_view()),
    path("summary/", InvestmentSummaryView.as_view()),
    path("import-uploads/", InvestmentImportDocumentListView.as_view()),
    path("import-uploads/<int:pk>/preview/", InvestmentImportReviewAPI.as_view()),
    path("import-uploads/<int:pk>/confirm/", InvestmentImportConfirmAPI.as_view()),
    path("import-pdf/", import_investment_pdf),
    path("allocation/", InvestmentAllocationView.as_view()),
    path("growth/", InvestmentGrowthView.as_view()),
    path("<int:pk>/", InvestmentDetailView.as_view()),
]
