"""Validate profile currency before float storage; schema conversion remains separate."""
from decimal import Decimal, InvalidOperation

from django import forms
from django.core.exceptions import ValidationError
from django.db import models
from rest_framework import serializers

from apps.expenses.money import LIMIT, expense_money

MESSAGE = "Enter a finite non-negative amount with at most two decimal places within the supported range."


def profile_money(value):
    if isinstance(value, bool) or value is None or len(str(value)) > 128:
        raise ValueError(MESSAGE)
    try:
        amount = Decimal(str(value))
        if not amount.is_finite() or amount < 0 or amount > LIMIT or expense_money(amount) != amount:
            raise ValueError(MESSAGE)
        return float(amount)
    except (InvalidOperation, TypeError, OverflowError, ValueError):
        raise ValueError(MESSAGE) from None


class ProfileMoneyField(models.FloatField):
    def to_python(self, value):
        try:
            return profile_money(value)
        except ValueError:
            raise ValidationError(MESSAGE, code="invalid") from None

    def get_prep_value(self, value):
        return self.to_python(value)

    def formfield(self, **kwargs):
        return super().formfield(form_class=forms.DecimalField, max_digits=14,
                                 decimal_places=2, min_value=0, max_value=LIMIT, **kwargs)

    def deconstruct(self):
        name, _, args, kwargs = super().deconstruct()
        # Validation changes no SQL type, historical values or migration state.
        return name, "django.db.models.FloatField", args, kwargs


class ProfileMoneySerializerField(serializers.FloatField):
    def to_internal_value(self, data):
        try:
            return profile_money(data)
        except ValueError:
            raise serializers.ValidationError(MESSAGE) from None
