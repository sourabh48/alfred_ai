from django.db import models
from django.conf import settings

class RelationshipProfile(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    partner_name = models.CharField(max_length=50)
    partner_financial_score = models.FloatField(default=0)
    partner_savings_habits = models.IntegerField(default=3)
    compatibility_score = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        ordering = ["-updated_at", "-id"]
