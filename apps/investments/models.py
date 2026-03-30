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
