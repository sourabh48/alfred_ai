from django.urls import path
from .views import InvestmentListCreateView, InvestmentDetailView

urlpatterns = [
    path("", InvestmentListCreateView.as_view()),
    path("<int:pk>/", InvestmentDetailView.as_view()),
]
