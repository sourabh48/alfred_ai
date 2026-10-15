"""Budget register amounts; currency metadata is not recorded by this schema."""
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from apps.expenses.money import ExpenseMoneyField, NumericMoneySerializerField, expense_money
from rest_framework import serializers

FIELDS = ("base_budget", "inflation_adjusted", "spent")
MESSAGE = "Enter a finite non-negative amount within the supported range."


def budget_money(value):
    try:
        if value is None or isinstance(value, bool) or len(str(value)) > 128:
            raise ValueError(MESSAGE)
        amount = Decimal(str(value))
        if not amount.is_finite() or amount < 0:
            raise ValueError(MESSAGE)
        return expense_money(amount)
    except (ValueError, InvalidOperation, TypeError, OverflowError):
        raise ValueError(MESSAGE) from None


class BudgetMoneyField(ExpenseMoneyField):
    def to_python(self, value):
        try:
            return budget_money(value)
        except ValueError:
            raise ValidationError(MESSAGE, code="invalid") from None

    def formfield(self, **kwargs):
        return super().formfield(**{**kwargs, "min_value": 0})


class BudgetMoneySerializerField(NumericMoneySerializerField):
    def to_internal_value(self, data):
        try:
            return budget_money(data)
        except ValueError:
            raise serializers.ValidationError(MESSAGE) from None
