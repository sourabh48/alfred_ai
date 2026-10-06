from django.db import models
from django.conf import settings
from .money import InvestmentMoneyField, investment_money, investment_total_float


class Investment(models.Model):
    ASSET_TYPES = [
        ("equity", "Equity"),
        ("debt", "Debt"),
        ("gold", "Gold"),
        ("reit", "REIT"),
        ("mutual_fund", "Mutual Fund"),
        ("crypto", "Crypto"),
        ("cash", "Cash / Liquid"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    asset_type = models.CharField(max_length=20, choices=ASSET_TYPES)
    asset_name = models.CharField(max_length=120)
    institution = models.CharField(max_length=120, blank=True)
    account_number = models.CharField(max_length=64, blank=True)
    invested_amount = InvestmentMoneyField(max_digits=14, decimal_places=2, default=0)
    monthly_sip = InvestmentMoneyField(max_digits=14, decimal_places=2, default=0)
    current_value = InvestmentMoneyField(max_digits=14, decimal_places=2, default=0)
    annual_return_rate = models.FloatField(default=0)
    risk_level = models.CharField(max_length=20, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-current_value", "-id"]

    def __str__(self):
        return f"{self.user.username} - {self.asset_name}"

    @property
    def gain_loss(self) -> float:
        return investment_total_float(investment_money(self.current_value) - investment_money(self.invested_amount))


class InvestmentImportDocument(models.Model):
    PARSER_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("parsed", "Parsed"),
        ("needs_review", "Needs Review"),
        ("failed", "Failed"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="investment_import_documents")
    uploaded_file = models.FileField(upload_to="investment_imports/%Y/%m/")
    file_name = models.CharField(max_length=255)
    broker_name = models.CharField(max_length=120, blank=True)
    parser_status = models.CharField(max_length=20, choices=PARSER_STATUS_CHOICES, default="pending")
    parse_confidence = models.FloatField(default=0)
    extracted_text = models.TextField(blank=True)
    extracted_payload = models.JSONField(default=dict, blank=True)
    summary = models.TextField(blank=True)
    linked_investments = models.ManyToManyField(Investment, blank=True, related_name="source_documents")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-id"]
        indexes = [
            models.Index(fields=["user", "parser_status", "updated_at"]),
            models.Index(fields=["user", "broker_name", "updated_at"]),
        ]

    def __str__(self):
        broker = self.broker_name or "investment"
        return f"{self.user.username} - {broker} - {self.file_name}"


class InvestmentMoneySnapshot(models.Model):
    original_investment_id = models.PositiveBigIntegerField(unique=True)
    investment = models.ForeignKey(Investment, null=True, on_delete=models.SET_NULL, related_name="money_snapshots")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="investment_money_snapshots")
    source_values = models.JSONField()
    normalized_values = models.JSONField()
    policy = models.CharField(max_length=30, default="investment-money-v1")
    applied_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
