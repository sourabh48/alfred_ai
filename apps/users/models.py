from decimal import Decimal, ROUND_HALF_UP

from django.contrib.auth.models import AbstractUser
from django.db import models
from .money import ProfileMoneyField


class IncomeBasis(models.TextChoices):
    MONTHLY = "monthly", "Per month"
    ANNUAL = "annual", "Per year"
    UNCONFIRMED = "unconfirmed", "Not confirmed"


class User(AbstractUser):
    class Meta:
        app_label = "users"
    # Holds the amount exactly as entered; monthly_income_basis says what period it covers.
    monthly_income = ProfileMoneyField(max_digits=14, decimal_places=2, default=0)
    monthly_income_basis = models.CharField(max_length=12, choices=IncomeBasis.choices, default=IncomeBasis.MONTHLY)
    variable_income = ProfileMoneyField(max_digits=14, decimal_places=2, default=0)
    rent_or_emi = ProfileMoneyField(max_digits=14, decimal_places=2, default=0)

    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    ml_training_consent_granted = models.BooleanField(default=False)
    ml_training_consent_given_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.username

    @property
    def confirmed_monthly_income(self):
        """Entered income per month, or zero while its period is unconfirmed."""
        amount = Decimal(str(self.monthly_income or 0))
        if self.monthly_income_basis == IncomeBasis.ANNUAL:
            return (amount / 12).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return amount if self.monthly_income_basis == IncomeBasis.MONTHLY else Decimal("0.00")

    @property
    def confirmed_annual_income(self):
        """Entered income per year, or zero while its period is unconfirmed."""
        amount = Decimal(str(self.monthly_income or 0))
        if self.monthly_income_basis == IncomeBasis.ANNUAL:
            return amount
        return amount * 12 if self.monthly_income_basis == IncomeBasis.MONTHLY else Decimal("0.00")

    @property
    def income_basis_needs_confirmation(self):
        if self.monthly_income_basis != IncomeBasis.UNCONFIRMED:
            return False
        if self.monthly_income > 0:
            return True
        from apps.career.models import CareerProfile
        return CareerProfile.objects.filter(user=self, last_salary__gt=0).exists()


class UserMoneySnapshot(models.Model):
    original_user_id = models.PositiveBigIntegerField(unique=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="money_snapshot")
    source_values = models.JSONField()
    normalized_values = models.JSONField()
    policy = models.CharField(max_length=30, default="user-money-v1")
    applied_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
