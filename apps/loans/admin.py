from django.contrib import admin

from .models import Loan, LoanClosureDocument, LoanPaymentHistory
from .services.payment_review import review_loan_payment_match


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
    list_display = (
        "loan",
        "payment_date",
        "amount",
        "match_status",
        "loan_effect_applied",
        "detection_confidence",
        "is_auto_detected",
    )
    list_filter = ("match_status", "loan_effect_applied", "is_auto_detected")
    search_fields = ("loan__lender", "detection_reason", "matched_reference")
    actions = ("accept_review_matches", "reject_review_matches")

    @admin.action(description="Accept selected review-gated loan payments")
    def accept_review_matches(self, request, queryset):
        count = 0
        for payment in queryset.filter(match_status="review").select_related("loan"):
            review_loan_payment_match(
                user=payment.loan.user,
                payment_id=payment.id,
                decision="accept",
                reviewer=request.user,
                notes="Accepted from Django admin.",
            )
            count += 1
        self.message_user(request, f"Accepted {count} loan payment review row(s).")

    @admin.action(description="Reject selected review-gated loan payments")
    def reject_review_matches(self, request, queryset):
        count = 0
        for payment in queryset.filter(match_status="review").select_related("loan"):
            review_loan_payment_match(
                user=payment.loan.user,
                payment_id=payment.id,
                decision="reject",
                reviewer=request.user,
                notes="Rejected from Django admin.",
            )
            count += 1
        self.message_user(request, f"Rejected {count} loan payment review row(s).")


@admin.register(LoanClosureDocument)
class LoanClosureDocumentAdmin(admin.ModelAdmin):
    list_display = ("loan", "file_name", "verification_status", "closure_amount", "closure_date", "created_at")
    list_filter = ("verification_status",)
    search_fields = ("loan__lender", "loan__loan_account_number", "file_name", "verification_notes")
