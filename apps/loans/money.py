"""Loan-domain currency boundary; rates and confidence remain separate."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext

from django.core.exceptions import ValidationError
from django.db import models


LOAN_MONEY_FIELDS = (
    "principal", "emi", "remaining_balance", "home_purchase_price",
    "home_down_payment", "home_other_upfront_payments", "total_paid",
)
LOAN_MONEY_QUANT = Decimal("0.01")
LOAN_MONEY_LIMIT = Decimal("999999999999.99")


def loan_money(value) -> Decimal:
    """Convert decimal text/legacy numbers to bounded cents using HALF_UP.

    None is zero for arithmetic; nullable model/serializer fields preserve it
    before calling this helper. Fourteen digits keep the supported currency
    range below SQLite's fifteen-significant-digit Decimal conversion limit.
    """
    if isinstance(value, bool):
        raise ValueError("Loan money must be a finite currency amount.")
    try:
        amount = value if isinstance(value, Decimal) else Decimal(str(value if value is not None else 0))
        if not amount.is_finite() or abs(amount) > LOAN_MONEY_LIMIT + LOAN_MONEY_QUANT:
            raise ValueError("Loan money is outside the supported currency range.")
        with localcontext() as context:
            context.prec = 30
            amount = amount.quantize(LOAN_MONEY_QUANT, rounding=ROUND_HALF_UP)
        if abs(amount) > LOAN_MONEY_LIMIT:
            raise ValueError("Loan money is outside the supported currency range.")
        return amount
    except (InvalidOperation, TypeError, OverflowError) as exc:
        raise ValueError("Loan money must be a finite currency amount.") from exc


def loan_money_float(value) -> float:
    """Keep the existing numeric JSON/display contract at output boundaries."""
    return float(loan_money(value))


class LoanMoneyField(models.DecimalField):
    """Normalize ordinary ORM writes before the backend stores their value."""

    def to_python(self, value):
        if value is None:
            return None
        try:
            return loan_money(value)
        except ValueError as exc:
            raise ValidationError(str(exc), code="invalid") from exc
