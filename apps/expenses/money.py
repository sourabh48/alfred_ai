"""Expense/account currency and retained legacy transaction identity evidence."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext

from django.core.exceptions import ValidationError
from django.db import models
from rest_framework import serializers

PAISE = Decimal("0.01")
LIMIT = Decimal("999999999999.99")


def expense_money(value):
    if isinstance(value, bool):
        raise ValueError("Currency must be a finite amount within the supported range.")
    try:
        amount = Decimal(str(value if value is not None else 0))
        if not amount.is_finite() or abs(amount) > LIMIT + PAISE:
            raise ValueError("Currency must be a finite amount within the supported range.")
        with localcontext() as context:
            context.prec = 30
            amount = amount.quantize(PAISE, rounding=ROUND_HALF_UP)
        if abs(amount) > LIMIT:
            raise ValueError("Currency must be a finite amount within the supported range.")
        return amount
    except (InvalidOperation, TypeError, OverflowError) as exc:
        raise ValueError("Currency must be a finite amount within the supported range.") from exc


def money_float(value):
    """Numeric API currency; virtual totals are not limited to a stored field."""
    amount = Decimal(str(value or 0))
    if not amount.is_finite():
        raise ValueError("Currency total must be finite.")
    with localcontext() as context:
        context.prec = max(30, amount.adjusted() + 4)
        return float(amount.quantize(PAISE, rounding=ROUND_HALF_UP))


def identity_values(amount, closing_balance):
    # This evidence feeds the unchanged historical float-based identity
    # algorithms. It is deliberately separate from currency calculations.
    expense_money(amount)
    if closing_balance is not None:
        expense_money(closing_balance)
    return {
        "amount": repr(float(amount)),
        "closing_balance": None if closing_balance is None else repr(float(closing_balance)),
    }


def identity_amount(evidence, field, current):
    """Ignore stale evidence after a genuine monetary edit (including null/zero)."""
    if field in (evidence or {}):
        retained = evidence[field]
        try:
            if (retained is None and current is None) or (
                retained is not None and current is not None
                and expense_money(retained) == expense_money(current)
            ):
                return None if retained is None else float(retained)
        except (ValueError, TypeError):
            pass
    return current


class ExpenseMoneyField(models.DecimalField):
    def to_python(self, value):
        if value is None:
            return None
        try:
            return expense_money(value)
        except ValueError as exc:
            raise ValidationError(str(exc), code="invalid") from exc


class NumericMoneySerializerField(serializers.Field):
    def to_internal_value(self, data):
        try:
            return expense_money(data)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc

    def to_representation(self, value):
        return money_float(value)
