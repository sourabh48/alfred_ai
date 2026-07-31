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
        ("foreclosure_pending", "Foreclosure Pending"),
        ("foreclosed", "Foreclosed"),
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
    home_purchase_price = models.FloatField(default=0)
    home_down_payment = models.FloatField(default=0)
    home_other_upfront_payments = models.FloatField(default=0)
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
        if self.status == "foreclosure_pending":
            return "foreclosure_pending"
        if self.status in {"foreclosed", "closed", "prepaid", "defaulted"}:
            return self.status
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

    @property
    def resolved_home_purchase_price(self) -> float:
        if self.loan_type != "home":
            return 0.0
        purchase_price = max(float(self.home_purchase_price or 0), 0.0)
        if purchase_price > 0:
            return round(purchase_price, 2)
        financed_amount = max(float(self.principal or 0), 0.0)
        down_payment = max(float(self.home_down_payment or 0), 0.0)
        return round(financed_amount + down_payment, 2) if (financed_amount or down_payment) else 0.0

    @property
    def resolved_home_down_payment(self) -> float:
        if self.loan_type != "home":
            return 0.0
        financed_amount = max(float(self.principal or 0), 0.0)
        purchase_price = max(float(self.home_purchase_price or 0), 0.0)
        if purchase_price > 0:
            return round(max(purchase_price - financed_amount, 0.0), 2)
        return round(max(float(self.home_down_payment or 0), 0.0), 2)

    @property
    def resolved_home_other_upfront_payments(self) -> float:
        if self.loan_type != "home":
            return 0.0
        return round(max(float(self.home_other_upfront_payments or 0), 0.0), 2)

    @property
    def resolved_home_upfront_cash_invested(self) -> float:
        return round(self.resolved_home_down_payment + self.resolved_home_other_upfront_payments, 2)

    @property
    def resolved_home_property_acquisition_cost(self) -> float:
        if self.loan_type != "home":
            return 0.0
        return round(self.resolved_home_purchase_price + self.resolved_home_other_upfront_payments, 2)


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
    principal_paid = models.FloatField(default=0)
    interest_paid = models.FloatField(default=0)
    charges_paid = models.FloatField(default=0)
    penalties_paid = models.FloatField(default=0)
    tax_paid = models.FloatField(default=0)
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
    PARSER_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("parsed", "Parsed"),
        ("needs_review", "Needs Review"),
        ("failed", "Failed"),
    ]
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
    parser_status = models.CharField(max_length=20, choices=PARSER_STATUS_CHOICES, default="pending")
    parse_confidence = models.FloatField(default=0)
    verification_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    verification_notes = models.TextField(blank=True)
    closure_amount = models.FloatField(default=0)
    closure_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        ordering = ["-updated_at", "-id"]
        indexes = [
            models.Index(fields=["loan", "verification_status", "created_at"]),
            models.Index(fields=["loan", "parser_status", "updated_at"]),
        ]

    def __str__(self):
        return f"{self.loan_id} | {self.file_name}"


class LoanForeclosureSnapshot(models.Model):
    DOCUMENT_TYPE_CHOICES = [
        ("foreclosure_statement", "Foreclosure Statement"),
        ("closure_letter", "Closure Letter"),
        ("noc", "No Objection / No Due"),
        ("loan_statement", "Loan Statement"),
        ("other", "Other"),
    ]
    RECONCILIATION_STATUS_CHOICES = [
        ("unmatched", "Unmatched"),
        ("partial_match", "Partial Match"),
        ("full_match", "Full Match"),
        ("mismatch", "Mismatch"),
    ]

    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name="foreclosure_snapshots")
    closure_document = models.OneToOneField(
        LoanClosureDocument,
        on_delete=models.CASCADE,
        related_name="foreclosure_snapshot",
    )
    document_type = models.CharField(max_length=40, choices=DOCUMENT_TYPE_CHOICES, default="other")
    lender_name = models.CharField(max_length=120, blank=True)
    borrower_name = models.CharField(max_length=180, blank=True)
    loan_account_number = models.CharField(max_length=64, blank=True)
    statement_date = models.DateField(null=True, blank=True)
    effective_closure_date = models.DateField(null=True, blank=True)
    due_by_date = models.DateField(null=True, blank=True)
    outstanding_principal = models.FloatField(default=0)
    accrued_interest = models.FloatField(default=0)
    foreclosure_charges = models.FloatField(default=0)
    taxes_gst = models.FloatField(default=0)
    overdue_charges = models.FloatField(default=0)
    total_amount_payable = models.FloatField(default=0)
    classification_confidence = models.FloatField(default=0)
    linkage_confidence = models.FloatField(default=0)
    linkage_notes = models.TextField(blank=True)
    reconciliation_status = models.CharField(
        max_length=20,
        choices=RECONCILIATION_STATUS_CHOICES,
        default="unmatched",
    )
    reconciliation_confidence = models.FloatField(default=0)
    matched_payment_total = models.FloatField(default=0)
    matched_emi_transaction_ids = models.JSONField(default=list, blank=True)
    matched_closure_transaction_ids = models.JSONField(default=list, blank=True)
    reconciliation_notes = models.TextField(blank=True)
    audit_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-id"]
        indexes = [
            models.Index(fields=["loan", "document_type", "updated_at"]),
            models.Index(fields=["loan", "reconciliation_status", "updated_at"]),
        ]

    def __str__(self):
        return f"{self.loan_id} | {self.document_type} | {self.reconciliation_status}"


class LoanImportDocument(models.Model):
    PARSER_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("parsed", "Parsed"),
        ("needs_review", "Needs Review"),
        ("failed", "Failed"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="loan_import_documents")
    uploaded_file = models.FileField(upload_to="loan_imports/%Y/%m/")
    file_name = models.CharField(max_length=255)
    document_type = models.CharField(max_length=40, blank=True)
    parser_status = models.CharField(max_length=20, choices=PARSER_STATUS_CHOICES, default="pending")
    parse_confidence = models.FloatField(default=0)
    extracted_text = models.TextField(blank=True)
    extracted_payload = models.JSONField(default=dict, blank=True)
    summary = models.TextField(blank=True)
    linked_loans = models.ManyToManyField(Loan, blank=True, related_name="source_documents")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["user", "document_type", "created_at"]),
            models.Index(fields=["user", "parser_status", "created_at"]),
        ]

    def __str__(self):
        document_type = self.document_type or "other"
        return f"{self.user.username} | {document_type} | {self.file_name}"
