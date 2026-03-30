from django.urls import path

from .views import (
    BankAccountDetailView,
    BankAccountListCreateView,
    ExpenseChartView,
    ExpenseDashboardView,
    ExpenseDetailView,
    ExpenseListCreateView,
    ExpenseStatementImportView,
    StatementUploadListView,
    ExpenseTimelineView,
)

urlpatterns = [
    path("", ExpenseListCreateView.as_view()),
    path("accounts/", BankAccountListCreateView.as_view()),
    path("accounts/<int:pk>/", BankAccountDetailView.as_view()),
    path("dashboard/", ExpenseDashboardView.as_view()),
    path("timeline/", ExpenseTimelineView.as_view()),
    path("chart/", ExpenseChartView.as_view()),
    path("uploads/", StatementUploadListView.as_view()),
    path("import-statement/", ExpenseStatementImportView.as_view()),
    path("<int:pk>/", ExpenseDetailView.as_view()),
]
