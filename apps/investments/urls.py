from django.urls import path
from .views import (
    InvestmentAllocationView,
    InvestmentDetailView,
    InvestmentGrowthView,
    InvestmentListCreateView,
    InvestmentSummaryView,
)

urlpatterns = [
    path("", InvestmentListCreateView.as_view()),
    path("summary/", InvestmentSummaryView.as_view()),
    path("allocation/", InvestmentAllocationView.as_view()),
    path("growth/", InvestmentGrowthView.as_view()),
    path("<int:pk>/", InvestmentDetailView.as_view()),
]
