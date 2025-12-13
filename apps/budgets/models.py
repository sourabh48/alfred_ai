from django.db import models
from django.conf import settings

class Budget(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    month = models.CharField(max_length=20)
    base_budget = models.FloatField()
    inflation_adjusted = models.FloatField()
    spent = models.FloatField(default=0)

    def __str__(self):
        return f"{self.user.username} - {self.month}"
