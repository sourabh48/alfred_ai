"""Budget register amounts; currency metadata is not recorded by this schema."""
from decimal import Decimal, InvalidOperation, ROUND_DOWN, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from apps.expenses.money import ExpenseMoneyField, NumericMoneySerializerField, expense_money
from rest_framework import serializers

FIELDS = ("base_budget", "inflation_adjusted", "spent")
MESSAGE = "Enter a finite non-negative amount within the supported range."


def allocate_budget(total, weights):
    """Apportion virtual category limits in cents, with stable remainder ties."""
    cent = Decimal("0.01")
    total = max(Decimal("0"), Decimal(str(total))).quantize(cent, rounding=ROUND_HALF_UP)
    weights = {key: Decimal(str(value)) for key, value in weights.items()}
    if any(not value.is_finite() or value < 0 for value in weights.values()):
        raise ValueError("Budget weights must be finite and non-negative.")
    weight_sum = sum(weights.values(), Decimal("0"))
    shares = {key: total * value / weight_sum if weight_sum else Decimal("0") for key, value in weights.items()}
    limits = {key: value.quantize(cent, rounding=ROUND_DOWN) for key, value in shares.items()}
    remainder = int((total - sum(limits.values(), Decimal("0"))) / cent) if weight_sum else 0
    for key in sorted(shares, key=lambda key: (-(shares[key] - limits[key]), key))[:remainder]:
        limits[key] += cent
    return limits


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
