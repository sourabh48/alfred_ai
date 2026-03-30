from django.conf import settings
from django.db import models
from django.utils import timezone


class BankAccount(models.Model):
    ACCOUNT_TYPE_CHOICES = [
        ("savings", "Savings"),
        ("current", "Current"),
        ("salary", "Salary"),
        ("credit", "Credit Card"),
        ("investment", "Investment"),
        ("other", "Other"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bank_accounts")
    bank_name = models.CharField(max_length=120, blank=True)
    nickname = models.CharField(max_length=120, blank=True)
    account_holder = models.CharField(max_length=255, blank=True)
    account_number = models.CharField(max_length=64)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPE_CHOICES, default="savings")
    current_balance = models.FloatField(null=True, blank=True)
    is_primary = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["bank_name", "account_number"]
        constraints = [
            models.UniqueConstraint(fields=["user", "account_number"], name="expenses_unique_user_account_number"),
        ]

    def __str__(self):
        return f"{self.user.username} | {self.display_name}"

    @property
    def masked_account_number(self) -> str:
        digits = "".join(char for char in self.account_number if char.isdigit())
        if len(digits) < 4:
            return self.account_number
        return f"****{digits[-4:]}"

    @property
    def display_name(self) -> str:
        label = self.nickname or self.bank_name or "Bank Account"
        return f"{label} {self.masked_account_number}".strip()


class StatementUpload(models.Model):
    SOURCE_CHOICES = [
        ("bank_statement", "Bank Statement"),
        ("credit_card_statement", "Credit Card Statement"),
        ("loan_statement", "Loan Statement"),
        ("investment_statement", "Investment Statement"),
        ("other_statement", "Other Statement"),
        ("email", "Email"),
    ]
    PARSER_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("parsed", "Parsed"),
        ("needs_review", "Needs Review"),
        ("failed", "Failed"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    bank_account = models.ForeignKey(
        BankAccount,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="statement_uploads",
    )
    source = models.CharField(max_length=30, choices=SOURCE_CHOICES, default="bank_statement")
    original_file = models.FileField(upload_to="statement_uploads/%Y/%m/", blank=True)
    file_name = models.CharField(max_length=255)
    bank_name = models.CharField(max_length=120, blank=True)
    account_holder = models.CharField(max_length=255, blank=True)
    account_number = models.CharField(max_length=64, blank=True)
    institution_name = models.CharField(max_length=120, blank=True)
    statement_start = models.DateField(null=True, blank=True)
    statement_end = models.DateField(null=True, blank=True)
    parser_status = models.CharField(max_length=20, choices=PARSER_STATUS_CHOICES, default="pending")
    parse_confidence = models.FloatField(default=0)
    extracted_payload = models.JSONField(default=dict, blank=True)
    imported_count = models.PositiveIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.user.username} | {self.file_name}"


class Expense(models.Model):
    CLASSIFICATION_CHOICES = [
        ("expense", "Expense"),
        ("loan", "Loan"),
        ("other", "Other"),
    ]

    CATEGORY_CHOICES = [
        ("food", "Food"),
        ("groceries", "Groceries"),
        ("shopping", "Shopping"),
        ("bills", "Bills"),
        ("utilities", "Utilities"),
        ("travel", "Travel"),
        ("fuel", "Fuel"),
        ("health", "Health"),
        ("subscription", "Subscription"),
        ("entertainment", "Entertainment"),
        ("rent", "Rent"),
        ("loan", "Loan / EMI"),
        ("credit_card", "Credit Card Payment"),
        ("investment", "Investment"),
        ("transfer", "Transfer"),
        ("income", "Income / Refund"),
        ("other", "Other"),
    ]

    SOURCE_CHOICES = [
        ("manual", "Manual"),
        ("bank_statement", "Bank Statement"),
        ("email", "Email"),
    ]

    DIRECTION_CHOICES = [
        ("debit", "Debit"),
        ("credit", "Credit"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    bank_account = models.ForeignKey(
        BankAccount,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expenses",
    )
    statement_upload = models.ForeignKey(
        StatementUpload,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expenses",
    )
    amount = models.FloatField()
    classification = models.CharField(max_length=20, choices=CLASSIFICATION_CHOICES, default="expense")
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default="other")
    payment_mode = models.CharField(max_length=50, default="UPI")
    merchant = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    raw_description = models.TextField(blank=True)
    transaction_date = models.DateField(default=timezone.localdate)
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES, default="debit")
    source = models.CharField(max_length=30, choices=SOURCE_CHOICES, default="manual")
    external_reference = models.CharField(max_length=120, blank=True)
    transaction_fingerprint = models.CharField(max_length=64, blank=True, db_index=True)
    closing_balance = models.FloatField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    counterparty = models.CharField(max_length=255, blank=True)
    company_name = models.CharField(max_length=255, blank=True)
    ai_summary = models.CharField(max_length=255, blank=True)

    # Alfred AI fields
    is_emotional = models.BooleanField(default=False)
    model_confidence = models.FloatField(default=0)

    class Meta:
        ordering = ["-transaction_date", "-id"]
        indexes = [
            models.Index(fields=["user", "bank_account", "transaction_date"]),
            models.Index(fields=["user", "bank_account", "transaction_fingerprint"]),
            models.Index(fields=["user", "bank_account", "external_reference", "transaction_date"]),
        ]

    def __str__(self):
        return f"{self.user.username} | {self.classification} | {self.category} | {self.amount}"
