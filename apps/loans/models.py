from django.conf import settings
from django.db import models
from django.utils import timezone
from datetime import timedelta


class Loan(models.Model):
    LOAN_TYPE_CHOICES = [
        ("home", "Home Loan"),
        ("personal", "Personal Loan"),
        ("car", "Car Loan"),
        ("education", "Education Loan"),
        ("business", "Business Loan"),
        ("credit_card", "Credit Card Debt"),
        ("other", "Other"),
    ]

    STATUS_CHOICES = [
        ("active", "Active"),
        ("closed", "Closed"),
        ("defaulted", "Defaulted"),
        ("prepaid", "Prepaid"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="loans")
    loan_type = models.CharField(max_length=50, choices=LOAN_TYPE_CHOICES, default="other")
    lender = models.CharField(max_length=120, blank=True)
    loan_account_number = models.CharField(max_length=64, blank=True)
    principal = models.FloatField()
    interest_rate = models.FloatField()
    emi = models.FloatField()
    tenure_months = models.PositiveIntegerField(default=12)
    remaining_balance = models.FloatField(null=True, blank=True)
    start_date = models.DateField()
    closed_on = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    consolidated_into = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="consolidated_loans",
    )
    consolidation_group = models.CharField(max_length=64, blank=True)
    closure_reason = models.CharField(max_length=30, blank=True)

    # ML-tracked fields
    auto_detected = models.BooleanField(default=False)
    last_payment_date = models.DateField(null=True, blank=True)
    total_paid = models.FloatField(default=0)
    missed_payments = models.PositiveIntegerField(default=0)

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_date", "-id"]
        indexes = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["user", "status"]),
            models.Index(fields=["user", "consolidation_group"]),
        ]

    def __str__(self):
        lender = f" | {self.lender}" if self.lender else ""
        return f"{self.user.username} | {self.loan_type}{lender}"

    @property
    def current_status(self) -> str:
        if self.closed_on or not self.is_active:
            return "closed"
        return self.status

    @property
    def months_remaining(self) -> int:
        if not self.is_active or self.closed_on:
            return 0
        today = timezone.now().date()
        end_date = self.start_date + timedelta(days=self.tenure_months * 30)
        return max(0, (end_date.year - today.year) * 12 + (end_date.month - today.month))

    @property
    def completion_percentage(self) -> float:
        if self.principal <= 0:
            return 100.0
        paid = self.principal - (self.remaining_balance or self.principal)
        return min(100.0, (paid / self.principal) * 100)


class LoanPaymentHistory(models.Model):
    MATCH_STATUS_CHOICES = [
        ("matched", "Matched"),
        ("review", "Needs Review"),
    ]

    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name="payment_history")
    payment_date = models.DateField()
    amount = models.FloatField()
    principal_component = models.FloatField(default=0)
    interest_component = models.FloatField(default=0)
    remaining_balance = models.FloatField(null=True, blank=True)
    is_auto_detected = models.BooleanField(default=False)
    detection_confidence = models.FloatField(default=0)
    detection_reason = models.CharField(max_length=255, blank=True)
    matched_reference = models.CharField(max_length=120, blank=True)
    match_status = models.CharField(max_length=20, choices=MATCH_STATUS_CHOICES, default="matched")
    expense_reference = models.ForeignKey(
        "expenses.Expense",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="linked_loan_payments",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-payment_date"]
        indexes = [
            models.Index(fields=["loan", "payment_date"]),
            models.Index(fields=["loan", "match_status", "payment_date"]),
        ]

    def __str__(self):
        return f"{self.loan.user.username} | {self.loan.loan_type} | {self.amount} on {self.payment_date}"


class LoanClosureDocument(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("verified", "Verified"),
        ("rejected", "Rejected"),
    ]

    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name="closure_documents")
    uploaded_file = models.FileField(upload_to="loan_closures/%Y/%m/")
    file_name = models.CharField(max_length=255)
    extracted_text = models.TextField(blank=True)
    extracted_payload = models.JSONField(default=dict, blank=True)
    verification_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    verification_notes = models.TextField(blank=True)
    closure_amount = models.FloatField(default=0)
    closure_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["loan", "verification_status", "created_at"]),
        ]

    def __str__(self):
        return f"{self.loan_id} | {self.file_name}"
