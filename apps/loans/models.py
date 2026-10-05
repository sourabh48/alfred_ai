from django.conf import settings
from django.db import models
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from .money import LoanMoneyField, loan_money


class Loan(models.Model):
    VERIFICATION_CHOICES = [
        ("estimated", "Estimated - needs review"),
        ("needs_review", "Needs review"),
        ("confirmed", "Confirmed"),
    ]
    VERIFICATION_SOURCE_CHOICES = [
        ("user", "User recorded"),
        ("emi_pattern", "Recurring payment estimate"),
        ("legacy_inference", "Legacy inferred record"),
        ("bureau", "Bureau report"),
    ]
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
    principal = LoanMoneyField(max_digits=14, decimal_places=2)
    interest_rate = models.FloatField()
    emi = LoanMoneyField(max_digits=14, decimal_places=2)
    tenure_months = models.PositiveIntegerField(default=12)
    remaining_balance = LoanMoneyField(max_digits=14, decimal_places=2, null=True, blank=True)
    home_purchase_price = LoanMoneyField(max_digits=14, decimal_places=2, default=0)
    home_down_payment = LoanMoneyField(max_digits=14, decimal_places=2, default=0)
    home_other_upfront_payments = LoanMoneyField(max_digits=14, decimal_places=2, default=0)
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
    verification_status = models.CharField(max_length=20, choices=VERIFICATION_CHOICES, default="confirmed")
    verification_source = models.CharField(max_length=30, choices=VERIFICATION_SOURCE_CHOICES, default="user")
    verified_at = models.DateTimeField(null=True, blank=True)
    last_payment_date = models.DateField(null=True, blank=True)
    total_paid = LoanMoneyField(max_digits=14, decimal_places=2, default=0)
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
    def is_confirmed(self) -> bool:
        return self.verification_status == "confirmed"

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
        principal = loan_money(self.principal)
        remaining = loan_money(self.remaining_balance if self.remaining_balance is not None else self.principal)
        return float(min(100, (principal - remaining) / principal * 100))

    @property
    def resolved_home_purchase_price(self) -> float:
        if self.loan_type != "home":
            return 0.0
        purchase_price = max(loan_money(self.home_purchase_price), 0)
        if purchase_price > 0:
            return float(purchase_price)
        financed_amount = max(loan_money(self.principal), 0)
        down_payment = max(loan_money(self.home_down_payment), 0)
        return float(financed_amount + down_payment)

    @property
    def resolved_home_down_payment(self) -> float:
        if self.loan_type != "home":
            return 0.0
        financed_amount = max(loan_money(self.principal), 0)
        purchase_price = max(loan_money(self.home_purchase_price), 0)
        if purchase_price > 0:
            return float(max(purchase_price - financed_amount, 0))
        return float(max(loan_money(self.home_down_payment), 0))

    @property
    def resolved_home_other_upfront_payments(self) -> float:
        if self.loan_type != "home":
            return 0.0
        return float(max(loan_money(self.home_other_upfront_payments), 0))

    @property
    def resolved_home_upfront_cash_invested(self) -> float:
        return float(loan_money(self.resolved_home_down_payment) + loan_money(self.resolved_home_other_upfront_payments))

    @property
    def resolved_home_property_acquisition_cost(self) -> float:
        if self.loan_type != "home":
            return 0.0
        # A computed property total can exceed the limit of a single stored field.
        return float(Decimal(str(self.resolved_home_purchase_price)) + loan_money(self.resolved_home_other_upfront_payments))


class LoanMoneySnapshot(models.Model):
    """Retained pre-cutover values; not exposed through the loan API."""

    loan = models.ForeignKey(Loan, null=True, on_delete=models.SET_NULL, related_name="money_snapshots")
    original_loan_id = models.PositiveBigIntegerField(unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="loan_money_snapshots")
    source_values = models.JSONField()
    normalized_values = models.JSONField()
    policy = models.CharField(max_length=30, default="loan-money-v1")
    created_at = models.DateTimeField(auto_now_add=True)
    applied_at = models.DateTimeField(null=True, blank=True)


class LoanPaymentHistory(models.Model):
    MATCH_STATUS_CHOICES = [
        ("matched", "Matched"),
        ("review", "Needs Review"),
        ("rejected", "Rejected"),
    ]

    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name="payment_history")
    payment_date = models.DateField()
    amount = LoanMoneyField(max_digits=14, decimal_places=2)
    principal_component = LoanMoneyField(max_digits=14, decimal_places=2, default=0)
    interest_component = LoanMoneyField(max_digits=14, decimal_places=2, default=0)
    principal_paid = LoanMoneyField(max_digits=14, decimal_places=2, default=0)
    interest_paid = LoanMoneyField(max_digits=14, decimal_places=2, default=0)
    charges_paid = LoanMoneyField(max_digits=14, decimal_places=2, default=0)
    penalties_paid = LoanMoneyField(max_digits=14, decimal_places=2, default=0)
    tax_paid = LoanMoneyField(max_digits=14, decimal_places=2, default=0)
    remaining_balance = LoanMoneyField(max_digits=14, decimal_places=2, null=True, blank=True)
    is_auto_detected = models.BooleanField(default=False)
    detection_confidence = models.FloatField(default=0)
    detection_reason = models.CharField(max_length=255, blank=True)
    matched_reference = models.CharField(max_length=120, blank=True)
    match_status = models.CharField(max_length=20, choices=MATCH_STATUS_CHOICES, default="matched")
    loan_effect_applied = models.BooleanField(default=False)
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
    closure_amount = LoanMoneyField(max_digits=14, decimal_places=2, default=0)
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
    outstanding_principal = LoanMoneyField(max_digits=14, decimal_places=2, default=0)
    accrued_interest = LoanMoneyField(max_digits=14, decimal_places=2, default=0)
    foreclosure_charges = LoanMoneyField(max_digits=14, decimal_places=2, default=0)
    taxes_gst = LoanMoneyField(max_digits=14, decimal_places=2, default=0)
    overdue_charges = LoanMoneyField(max_digits=14, decimal_places=2, default=0)
    total_amount_payable = LoanMoneyField(max_digits=14, decimal_places=2, default=0)
    classification_confidence = models.FloatField(default=0)
    linkage_confidence = models.FloatField(default=0)
    linkage_notes = models.TextField(blank=True)
    reconciliation_status = models.CharField(
        max_length=20,
        choices=RECONCILIATION_STATUS_CHOICES,
        default="unmatched",
    )
    reconciliation_confidence = models.FloatField(default=0)
    matched_payment_total = LoanMoneyField(max_digits=14, decimal_places=2, default=0)
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


class LoanRelatedMoneySnapshot(models.Model):
    """Retained ancillary currency and original linkage; not exposed by APIs."""

    source_model = models.CharField(max_length=40)
    original_source_id = models.PositiveBigIntegerField()
    original_loan_id = models.PositiveBigIntegerField()
    original_parent_ids = models.JSONField(default=dict)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="loan_related_money_snapshots")
    loan = models.ForeignKey(Loan, null=True, on_delete=models.SET_NULL, related_name="related_money_snapshots")
    payment_history = models.ForeignKey(LoanPaymentHistory, null=True, on_delete=models.SET_NULL, related_name="money_snapshots")
    closure_document = models.ForeignKey(LoanClosureDocument, null=True, on_delete=models.SET_NULL, related_name="money_snapshots")
    foreclosure_snapshot = models.ForeignKey(LoanForeclosureSnapshot, null=True, on_delete=models.SET_NULL, related_name="money_snapshots")
    source_values = models.JSONField()
    normalized_values = models.JSONField()
    policy = models.CharField(max_length=30, default="loan-money-v1")
    created_at = models.DateTimeField(auto_now_add=True)
    applied_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["source_model", "original_source_id"], name="loan_related_money_source_unique")]


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
