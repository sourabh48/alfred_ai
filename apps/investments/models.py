from django.db import models
from django.conf import settings

class Investment(models.Model):
    ASSET_TYPES = [
        ("equity", "Equity"),
        ("debt", "Debt"),
        ("gold", "Gold"),
        ("reit", "REIT"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    asset_type = models.CharField(max_length=20, choices=ASSET_TYPES)
    monthly_sip = models.FloatField(default=0)
    current_value = models.FloatField(default=0)

    def __str__(self):
        return f"{self.user.username} - {self.asset_type}"
