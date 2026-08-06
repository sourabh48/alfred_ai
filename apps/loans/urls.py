from django.urls import path

from .views import (
    LoanDetailView,
    LoanImportDocumentListView,
    LoanListCreateView,
    LoanConsolidationView,
    LoanSummaryView,
    import_loan_pdf,
    payoff_loan,
    detect_loans_from_expenses,
    review_loan_payment,
    loan_metrics,
    calculate_networth,
)

urlpatterns = [
    path("", LoanListCreateView.as_view(), name="loan_list_create"),
    path("summary/", LoanSummaryView.as_view(), name="loan_summary"),
    path("import-uploads/", LoanImportDocumentListView.as_view(), name="loan_import_uploads"),
    path("import-pdf/", import_loan_pdf, name="import_loan_pdf"),
    path("consolidate/", LoanConsolidationView.as_view(), name="loan_consolidate"),
    path("detect-from-expenses/", detect_loans_from_expenses, name="detect_loans"),
    path("payment-history/<int:payment_id>/review/", review_loan_payment, name="loan_payment_review"),
    path("metrics/", loan_metrics, name="loan_metrics"),
    path("networth/", calculate_networth, name="calculate_networth"),
    path("<int:pk>/", LoanDetailView.as_view(), name="loan_detail"),
    path("<int:pk>/payoff/", payoff_loan, name="payoff_loan"),
]
