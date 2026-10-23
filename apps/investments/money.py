"""Investment register currency; rates, NAV and extraction evidence are separate."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
from math import isfinite

from django.core.exceptions import ValidationError
from django.db import models

INVESTMENT_MONEY_FIELDS = ("invested_amount", "monthly_sip", "current_value")
PAISE = Decimal("0.01")
LIMIT = Decimal("999999999999.99")


def investment_money(value) -> Decimal:
    """Validate each stored amount and round decimal text to HALF_UP cents."""
    if isinstance(value, bool):
        raise ValueError("Investment money must be a finite currency amount.")
    try:
        amount = Decimal(str(value if value is not None else 0))
        if not amount.is_finite() or abs(amount) > LIMIT + PAISE:
            raise ValueError("Investment money is outside the supported currency range.")
        with localcontext() as context:
            context.prec = 30
            amount = amount.quantize(PAISE, rounding=ROUND_HALF_UP)
        if abs(amount) > LIMIT:
            raise ValueError("Investment money is outside the supported currency range.")
        return amount
    except (InvalidOperation, TypeError, OverflowError) as exc:
        raise ValueError("Investment money must be a finite currency amount.") from exc


def investment_total_float(value) -> float:
    """Numeric output for virtual totals, which may exceed a stored field bound."""
    amount = Decimal(str(value))
    if not amount.is_finite() or not isfinite(float(amount)):
        raise ValueError("Investment total must be finite.")
    with localcontext() as context:
        context.prec = max(30, amount.adjusted() + 4)
        return float(amount.quantize(PAISE, rounding=ROUND_HALF_UP))


class InvestmentMoneyField(models.DecimalField):
    def to_python(self, value):
        if value is None:
            return None
        try:
            return investment_money(value)
        except ValueError as exc:
            raise ValidationError(str(exc), code="invalid") from exc
