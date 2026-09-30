"""Exact monetary inputs; whole-rupee estimates and decimal-string provider quotes."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def decimal_amount(value):
    if isinstance(value, bool):
        raise ValueError("Invalid monetary amount")
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError("Invalid monetary amount") from None
    if not amount.is_finite() or amount < 0 or amount >= Decimal("1000000000"):
        raise ValueError("Monetary amount out of bounds")
    return amount


def rupees(value):
    return int(decimal_amount(value).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def quoted_amount(value):
    # Preserve provider precision/currency scale; do not assume every currency uses cents.
    amount = decimal_amount(value)
    # Reject excessive scale instead of expanding tiny exponent inputs into huge strings.
    if amount.as_tuple().exponent < -28:
        raise ValueError("Excessive monetary precision")
    return format(amount, "f")


def estimated_nightly(total, nights):
    return format((decimal_amount(total)/nights).quantize(Decimal("0.01"),rounding=ROUND_HALF_UP),"f")
