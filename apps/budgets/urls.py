from django.urls import path
from .views import BudgetListCreateView, BudgetDetailView, SavingsGoalDetailView, SavingsGoalListCreateView, get_budget_dashboard

urlpatterns = [
    path("", BudgetListCreateView.as_view()),
    path("goals/", SavingsGoalListCreateView.as_view(), name="savings_goals"),
    path("goals/<int:pk>/", SavingsGoalDetailView.as_view(), name="savings_goal_detail"),
    path("<int:pk>/", BudgetDetailView.as_view()),
    path("dashboard/", get_budget_dashboard),
]
