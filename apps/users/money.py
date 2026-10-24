"""Finite, bounded Decimal cents for reported profile money; currency is unknown."""
from decimal import Decimal, InvalidOperation

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
        return expense_money(amount)
    except (InvalidOperation, TypeError, OverflowError, ValueError):
        raise ValueError(MESSAGE) from None


class ProfileMoneyField(models.DecimalField):
    def to_python(self, value):
        try:
            return profile_money(value)
        except ValueError:
            raise ValidationError(MESSAGE, code="invalid") from None

    def formfield(self, **kwargs):
        return super().formfield(**{**kwargs, "min_value": 0, "max_value": LIMIT})


class ProfileMoneySerializerField(serializers.FloatField):
    def to_internal_value(self, data):
        try:
            return profile_money(data)
        except ValueError:
            raise serializers.ValidationError(MESSAGE) from None
