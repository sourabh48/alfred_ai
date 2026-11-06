from django.urls import path
from .views import BudgetListCreateView, BudgetDetailView, SavingsGoalDetailView, SavingsGoalListCreateView, SavingsGoalPlanView, get_budget_dashboard

urlpatterns = [
    path("", BudgetListCreateView.as_view()),
    path("goals/", SavingsGoalListCreateView.as_view(), name="savings_goals"),
    path("goals/<int:pk>/", SavingsGoalDetailView.as_view(), name="savings_goal_detail"),
    path("goals/<int:pk>/plan/", SavingsGoalPlanView.as_view(), name="savings_goal_plan"),
    path("<int:pk>/", BudgetDetailView.as_view()),
    path("dashboard/", get_budget_dashboard),
]
