from django.contrib.auth.models import AbstractUser
from django.db import models
from .money import ProfileMoneyField


class User(AbstractUser):
    class Meta:
        app_label = "users"
    monthly_income = ProfileMoneyField(max_digits=14, decimal_places=2, default=0)
    variable_income = ProfileMoneyField(max_digits=14, decimal_places=2, default=0)
    rent_or_emi = ProfileMoneyField(max_digits=14, decimal_places=2, default=0)

    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    ml_training_consent_granted = models.BooleanField(default=False)
    ml_training_consent_given_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.username


class UserMoneySnapshot(models.Model):
    original_user_id = models.PositiveBigIntegerField(unique=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="money_snapshot")
    source_values = models.JSONField()
    normalized_values = models.JSONField()
    policy = models.CharField(max_length=30, default="user-money-v1")
    applied_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
