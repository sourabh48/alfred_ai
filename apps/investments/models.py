from django.db import models
from django.conf import settings


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
    invested_amount = models.FloatField(default=0)
    monthly_sip = models.FloatField(default=0)
    current_value = models.FloatField(default=0)
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
        return round((self.current_value or 0) - (self.invested_amount or 0), 2)


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
