"""Read-only loan prepayment what-if: interest saved, months saved, and prepaying versus investing the same money.

Standard reducing-balance EMI maths in Decimal cents: each month's interest is balance x annual rate / 12, rounded
HALF_UP to the paisa. Lenders may accrue daily or charge prepayment fees, so results are estimates. The
prepay-versus-invest comparison follows each path to the original payoff month, so money freed by a smaller or
earlier EMI is invested too (a plain "interest saved versus return" comparison ignores that and favours investing).
Nothing here writes to the loan.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP, ROUND_UP

from apps.loans.money import loan_money

CENT = Decimal("0.01")
MAX_MONTHS = 1200
SAFE_RUNWAY_MONTHS = Decimal("6")  # same emergency-fund target as the budget advice


def _monthly_rate(annual_percent) -> Decimal:
    return Decimal(str(annual_percent)) / Decimal("1200")


def schedule(balance: Decimal, emi: Decimal, rate: Decimal) -> list[tuple[Decimal, Decimal]] | None:
    """(payment, interest) for each month until paid off, or None when the EMI never clears the balance."""
    rows = []
    while balance > 0:
        interest = (balance * rate).quantize(CENT, rounding=ROUND_HALF_UP)
        if emi <= interest or len(rows) >= MAX_MONTHS:
            return None
        payment = min(emi, balance + interest)
        rows.append((payment, interest))
        balance = balance + interest - payment
    return rows


def level_emi(balance: Decimal, months: int, rate: Decimal) -> Decimal:
    """The EMI that clears the balance in the given months, rounded up so it never runs over."""
    if rate == 0:
        return (balance / months).quantize(CENT, rounding=ROUND_UP)
    growth = (1 + rate) ** months
    return (balance * rate * growth / (growth - 1)).quantize(CENT, rounding=ROUND_UP)


def simulate(*, balance, emi, annual_rate, amount, mode="reduce_tenure", expected_return=None) -> dict:
    balance, emi, amount = loan_money(balance), loan_money(emi), loan_money(amount)
    rate = _monthly_rate(annual_rate)
    if balance <= 0 or emi <= 0:
        raise ValueError("The loan needs a recorded outstanding balance and EMI above zero.")
    if amount <= 0:
        raise ValueError("Enter a prepayment amount above zero.")
    if mode not in {"reduce_tenure", "reduce_emi"}:
        raise ValueError("Choose reduce_tenure or reduce_emi.")
    base = schedule(balance, emi, rate)
    if base is None:
        raise ValueError("The EMI does not cover the monthly interest, so the loan never finishes at this rate.")
    remaining = balance - amount
    if remaining <= 0:
        after, new_emi, mode, amount = [], Decimal("0"), "closes_loan", balance
    elif mode == "reduce_tenure":
        after, new_emi = schedule(remaining, emi, rate), emi
    else:
        new_emi = level_emi(remaining, len(base), rate)
        after = schedule(remaining, new_emi, rate)
    base_interest = sum((row[1] for row in base), Decimal("0"))
    after_interest = sum((row[1] for row in after), Decimal("0"))
    result = {
        "mode": mode, "prepayment": amount,
        "baseline": {"months": len(base), "emi": emi, "total_interest": base_interest},
        "after": {"months": len(after), "emi": new_emi if after else Decimal("0"), "total_interest": after_interest},
        "interest_saved": base_interest - after_interest, "months_saved": len(base) - len(after),
    }
    if expected_return is not None:
        result["versus_investing"] = _versus_investing(base, after, amount, Decimal(str(expected_return)))
    return result


def _versus_investing(base, after, amount, annual_return: Decimal) -> dict:
    """Wealth at the original payoff month on each path, investing whatever each path leaves free."""
    months, rate = len(base), annual_return / Decimal("1200")
    invest_path = amount * (1 + rate) ** months
    prepay_path = Decimal("0")
    for month, (payment, _) in enumerate(base, start=1):
        freed = payment - (after[month - 1][0] if month <= len(after) else Decimal("0"))
        prepay_path += max(freed, Decimal("0")) * (1 + rate) ** (months - month)
    invest_path, prepay_path = invest_path.quantize(CENT, rounding=ROUND_HALF_UP), prepay_path.quantize(CENT, rounding=ROUND_HALF_UP)
    better = "prepay" if prepay_path > invest_path else ("invest" if invest_path > prepay_path else "equal")
    return {"expected_annual_return_percent": annual_return, "horizon_months": months, "prepay_path_value": prepay_path,
            "invest_path_value": invest_path, "difference": abs(prepay_path - invest_path), "better": better}


def liquidity_after(baseline: dict, amount: Decimal) -> dict:
    """Months of essential spending left in the bank after paying the amount, from the canonical baseline."""
    cash = loan_money(baseline.get("liquid_cash") or 0)
    outflow = loan_money(baseline.get("essential_monthly_outflow") or 0)
    if outflow <= 0:
        return {"status": "unknown", "detail": "Not enough recorded spending to measure months of runway."}
    left = cash - amount
    runway = (max(left, Decimal("0")) / outflow).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    status = "short" if left < 0 else ("thin" if runway < SAFE_RUNWAY_MONTHS else "kept")
    detail = {"short": "Your recorded bank balances do not cover this amount.",
              "thin": f"This leaves {runway} months of essential spending, under the {SAFE_RUNWAY_MONTHS}-month emergency fund.",
              "kept": f"This leaves {runway} months of essential spending."}[status]
    return {"status": status, "liquid_cash": cash, "cash_after": left, "runway_months_after": runway, "detail": detail}
