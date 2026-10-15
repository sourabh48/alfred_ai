from django.db import models
from django.conf import settings
from .money import BudgetMoneyField

class Budget(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    month = models.CharField(max_length=20)
    base_budget = BudgetMoneyField(max_digits=14, decimal_places=2)
    inflation_adjusted = BudgetMoneyField(max_digits=14, decimal_places=2)
    spent = BudgetMoneyField(max_digits=14, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.user.username} - {self.month}"


class BudgetMoneySnapshot(models.Model):
    original_budget_id = models.PositiveBigIntegerField(unique=True)
    budget = models.ForeignKey(Budget, null=True, on_delete=models.SET_NULL, related_name="money_snapshots")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="budget_money_snapshots")
    source_values = models.JSONField()
    normalized_values = models.JSONField()
    policy = models.CharField(max_length=30, default="budget-money-v1")
    applied_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
