from django.db import models
from django.conf import settings

class RelationshipProfile(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    partner_name = models.CharField(max_length=50)
    partner_financial_score = models.FloatField(default=0)
    partner_savings_habits = models.IntegerField(default=3)
    compatibility_score = models.FloatField(default=0)
