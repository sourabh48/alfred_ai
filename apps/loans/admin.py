from django.contrib import admin

from .models import Loan, LoanClosureDocument, LoanPaymentHistory


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "loan_type",
        "lender",
        "loan_account_number",
        "principal",
        "remaining_balance",
        "interest_rate",
        "emi",
        "tenure_months",
        "start_date",
        "closed_on",
        "is_active",
    )
    list_filter = ("loan_type", "is_active")
    search_fields = ("loan_type", "lender", "loan_account_number", "notes")


@admin.register(LoanPaymentHistory)
class LoanPaymentHistoryAdmin(admin.ModelAdmin):
    list_display = ("loan", "payment_date", "amount", "match_status", "detection_confidence", "is_auto_detected")
    list_filter = ("match_status", "is_auto_detected")
    search_fields = ("loan__lender", "detection_reason", "matched_reference")


@admin.register(LoanClosureDocument)
class LoanClosureDocumentAdmin(admin.ModelAdmin):
    list_display = ("loan", "file_name", "verification_status", "closure_amount", "closure_date", "created_at")
    list_filter = ("verification_status",)
    search_fields = ("loan__lender", "loan__loan_account_number", "file_name", "verification_notes")
