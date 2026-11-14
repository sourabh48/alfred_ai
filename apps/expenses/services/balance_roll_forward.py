"""WEALTH2-003 slice 1: a bank balance rolled forward from its last statement row, read-only.

The anchor is the newest imported row carrying a closing balance. Only entries dated strictly after it count,
so nothing the statement already included is added twice. Nothing is written.
"""
from decimal import Decimal

from apps.expenses.models import Expense
from apps.expenses.money import expense_money

NOT_ROLLED_TYPES = {"credit", "investment"}  # their statement balances are outstanding dues or holdings, not cash


def _unavailable(reason):
    return {"status": "unavailable", "reason": reason}


def balance_roll_forward(account):
    if account.account_type in NOT_ROLLED_TYPES:
        return _unavailable("Only bank cash accounts are rolled forward.")
    rows = Expense.objects.filter(user_id=account.user_id, bank_account=account)
    anchor = rows.filter(closing_balance__isnull=False).order_by("-transaction_date", "-id").first()
    if anchor is None:
        return _unavailable("No imported statement row with a balance yet.")
    if account.current_balance is None or expense_money(account.current_balance) != expense_money(anchor.closing_balance):
        return _unavailable("The account balance was changed by hand after the last statement, so it is the latest figure.")
    later = list(rows.filter(transaction_date__gt=anchor.transaction_date).values_list("amount", "direction", "currency"))
    if any(currency != anchor.currency for _, _, currency in later):
        return _unavailable("Some later entries are in another or unrecorded currency; amounts are never converted.")
    credits = sum((expense_money(a) for a, d, _ in later if d == "credit"), Decimal("0"))
    debits = sum((expense_money(a) for a, d, _ in later if d != "credit"), Decimal("0"))
    same_day = rows.filter(transaction_date=anchor.transaction_date, closing_balance__isnull=True).count()
    anchor_balance = expense_money(anchor.closing_balance)
    return {
        "status": "estimated" if later else "no_newer_entries",
        "anchor_date": anchor.transaction_date.isoformat(),
        "anchor_balance": anchor_balance,
        "entries": len(later),
        "credits": credits,
        "debits": debits,
        "estimated_balance": anchor_balance + credits - debits,  # virtual figure, never stored
        "same_day_not_counted": same_day,
    }
