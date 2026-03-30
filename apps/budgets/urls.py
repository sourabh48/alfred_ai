from django.urls import path
from .views import BudgetListCreateView, BudgetDetailView, get_budget_dashboard

urlpatterns = [
    path("", BudgetListCreateView.as_view()),
    path("<int:pk>/", BudgetDetailView.as_view()),
    path("dashboard/", get_budget_dashboard),
]
