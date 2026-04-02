from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Meta:
        app_label = "users"
    monthly_income = models.FloatField(default=0)
    variable_income = models.FloatField(default=0)
    rent_or_emi = models.FloatField(default=0)

    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    ml_training_consent_granted = models.BooleanField(default=False)
    ml_training_consent_given_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.username
