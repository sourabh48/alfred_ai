from django.db import models
from django.conf import settings

class RiskSignal(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    layoff_risk = models.FloatField(default=0)
    illness_risk = models.FloatField(default=0)
    relocation_risk = models.FloatField(default=0)
    timestamp = models.DateTimeField(auto_now_add=True)
